# /// script
# dependencies = [
#   "fastapi>=0.110.0", "uvicorn>=0.29.0", "sqlalchemy>=2.0.0", "aiosqlite>=0.20.0",
#   "python-dotenv>=1.0.0", "openai>=1.20.0", "pydantic>=2.0.0", "python-multipart>=0.0.9"
# ]
# ///
import os
import json
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

from database import init_db, async_session
from models import HomeworkRecord, ProblemRecord
from ocr_service import ocr_images
from prompts import GRADE_RULES, SUBJECT_NAMES, get_subject_prompt, get_universal_prompt
from question_parser import parse as parse_questions, format_for_llm
from sqlalchemy import func, select

# ---- LLM config ----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
ENABLE_OCR = os.getenv("ENABLE_OCR", "true").lower() == "true"

llm_client: Optional[AsyncOpenAI] = None
if LLM_BASE_URL and LLM_API_KEY:
    llm_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

# ---- Prompt builders (now in prompts.py) ----
def get_explain_prompt(grade: int, subject: str, question: str, student_answer: str, correct_answer: str, wrong_reason: str) -> str:
    rule = GRADE_RULES.get(grade, {}).get(subject, "")
    return f"""你是一位{grade}年级{SUBJECT_NAMES.get(subject, subject)}辅导老师，正给一位做错题的孩子讲解。
{rule}

跨科目红线：禁止JSON/贬低/俚语。步骤清晰，用"你"而非"我们"。数学必须给出至少两种方法（线段图+分步）。

题目：{question}
孩子的错误答案：{student_answer}
正确答案：{correct_answer}
判题发现的错因：{wrong_reason}

请输出如下JSON（不要markdown代码块）：
{{"explanation":"详细步骤...","methods":[{{"name":"方法1","content":"步骤..."}}],"tip":"易错点一句话","finalAnswer":"正确答案"}}
若不需要多方法，methods可为空列表。"""

# ---- LLM call helpers ----
async def call_llm(system: str, user: str, temperature: float = 0.3) -> str:
    """调用LLM，使用流式模式拼接完整响应（该API仅支持stream=True）。"""
    if not llm_client:
        raise RuntimeError("LLM未配置，请检查环境变量LLM_BASE_URL和LLM_API_KEY")
    stream = await llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=temperature,
        max_tokens=4096,
        timeout=120.0,
        stream=True,
    )
    chunks = []
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)
    return "".join(chunks)

def safe_json_parse(text: str):
    t = text.strip()
    if t.startswith("```json"): t = t[7:]
    elif t.startswith("```"): t = t[3:]
    if t.endswith("```"): t = t[:-3]
    t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        try:
            return json.loads(text)
        except Exception:
            return None

# ---- lifespan ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="小学作业辅导助手 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Endpoints ----
@app.post("/api/correct")
async def correct(
    grade: int = Form(...),
    subject: str = Form(...),
    inputMode: str = Form(...),
    textContent: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
):
    texts = []
    if textContent:
        texts.append(textContent)

    if inputMode == "photo" and images:
        image_bytes = []
        for img in images:
            content = await img.read()
            if content: image_bytes.append(content)
        if ENABLE_OCR and image_bytes:
            ocr_text = await ocr_images(image_bytes)
            if ocr_text:
                texts.append(ocr_text)

    if not texts:
        return {"success": False, "message": "没有识别到任何内容，请检查输入或图片"}

    full_text = "\n".join(texts)

    # Step 1: 拆题引擎预分割
    parsed_questions, is_reliable = parse_questions(full_text)

    # Step 2: 学科专用提示词
    system = get_subject_prompt(grade, subject)

    # Step 3: 构建用户消息
    subject_name = SUBJECT_NAMES.get(subject, subject)
    if parsed_questions and is_reliable:
        # 规则引擎拆分可靠 → LLM 接收已拆好的题目，只需批改
        formatted = format_for_llm(parsed_questions)
        user = f"以下是已拆分好的{grade}年级{subject_name}作业题目（共{len(parsed_questions)}题），请逐题批改：\n\n{formatted}\n\n请输出所有题目的批改结果JSON。"
    else:
        # 规则引擎不可靠 → 回退到原始文本，LLM 自行拆题+批改
        user = f"以下是学生提交的{grade}年级{subject_name}作业内容，请自行拆分题目并逐题批改：\n\n{full_text}"

    try:
        raw = await call_llm(system, user, temperature=0.2)
    except Exception as e:
        return {"success": True, "data": {"mode": "ai_error", "errorType": "LLM调用失败", "rawText": str(e)}}

    data = safe_json_parse(raw)
    if not data or not isinstance(data, dict):
        return {"success": True, "data": {"mode": "ai_error", "errorType": "JSON解析异常", "rawText": raw}}

    mode = data.get("mode", "correction")
    questions = data.get("questions", [])

    if mode == "error" or not questions:
        return {"success": True, "data": {"mode": "error", "totalCount": 0, "questions": []}}

    total = len(questions)
    not_attempted = sum(1 for q in questions if q.get("status") == "not_attempted")
    if mode == "correction" or (mode not in ("direct-answer", "error")):
        correct = sum(1 for q in questions if q.get("isCorrect") and q.get("status") == "normal")
        wrong = sum(1 for q in questions if not q.get("isCorrect") and q.get("status") == "normal")
        # 全对判断：所有normal题都正确，且没有答案模糊/异常状态题，not_attempted不影响
        if correct == (total - not_attempted) and wrong == 0 and total > 0 and \
           all(q.get("status") in ("normal", "not_attempted") for q in questions) and \
           correct > 0:
            result_data = {"mode": "all_correct", "totalCount": total, "correctCount": correct, "wrongCount": 0, "notAttemptedCount": not_attempted, "questions": questions}
        else:
            result_data = {"mode": "correction", "totalCount": total, "correctCount": correct, "wrongCount": wrong, "notAttemptedCount": not_attempted, "questions": questions}
    elif mode == "direct-answer":
        result_data = {"mode": "direct-answer", "totalCount": total, "questions": questions}
    else:
        correct = sum(1 for q in questions if q.get("isCorrect"))
        if correct == total and all(q.get("status") == "normal" for q in questions):
            result_data = {"mode": "all_correct", "totalCount": total, "correctCount": correct, "wrongCount": 0, "questions": questions}
        else:
            wrong = total - correct
            result_data = {"mode": "correction", "totalCount": total, "correctCount": correct, "wrongCount": wrong, "questions": questions}

    # persist to DB
    try:
        async with async_session() as session:
            record = HomeworkRecord(
                grade=grade, subject=subject, mode=result_data["mode"],
                total_count=result_data.get("totalCount", 0),
                correct_count=result_data.get("correctCount", 0),
                wrong_count=result_data.get("wrongCount", 0),
                not_attempted_count=result_data.get("notAttemptedCount", 0),
            )
            session.add(record)
            await session.flush()
            if result_data["mode"] in ("correction", "all_correct"):
                for q in questions:
                    if q.get("status") != "normal":
                        continue  # 跳过 not_attempted/answer_unclear/partial_recognition/unrecognizable
                    session.add(ProblemRecord(
                        homework_id=record.id,
                        question_content=str(q.get("content", ""))[:500],
                        is_correct=1 if q.get("isCorrect") else 0,
                        wrong_reason=str(q.get("wrongReason", ""))[:500],
                        error_type=str(q.get("errorType", ""))[:100],
                    ))
            await session.commit()
    except Exception as e:
        print("DB error:", e)
        traceback.print_exc()

    return {"success": True, "data": result_data}

class ExplainRequest(BaseModel):
    grade: int
    subject: str
    question: str
    studentAnswer: Optional[str] = None
    correctAnswer: Optional[str] = None
    wrongReason: Optional[str] = None

@app.post("/api/explain")
async def explain(req: ExplainRequest):
    try:
        system = get_explain_prompt(req.grade, req.subject, req.question, req.studentAnswer or "", req.correctAnswer or "", req.wrongReason or "")
        raw = await call_llm(system, "请按格式输出讲解。", temperature=0.4)
        data = safe_json_parse(raw)
        if not data or not isinstance(data, dict):
            data = {"explanation": raw, "methods": [], "tip": "", "finalAnswer": req.correctAnswer or ""}
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/stats")
async def stats():
    try:
        async with async_session() as session:
            total_problems = await session.scalar(select(func.count(ProblemRecord.id)))
            total_errors = await session.scalar(select(func.count(ProblemRecord.id)).where(ProblemRecord.is_correct == 0))
            accuracy = f"{round((total_problems - total_errors) / total_problems * 100)}%" if total_problems else "N/A"

            stmt = select(ProblemRecord.error_type, func.count(ProblemRecord.id).label("cnt")).where(ProblemRecord.is_correct == 0).group_by(ProblemRecord.error_type).order_by(func.count(ProblemRecord.id).desc()).limit(5)
            rows = await session.execute(stmt)
            top_errors = []
            max_cnt = 1
            all_rows = rows.all()
            if all_rows: max_cnt = max(r.cnt for r in all_rows)
            for row in all_rows:
                top_errors.append({"type": row.error_type or "未分类", "count": row.cnt, "percent": round(row.cnt / max_cnt * 100)})

            stmt2 = select(HomeworkRecord.subject, func.count(HomeworkRecord.id).label("cnt")).group_by(HomeworkRecord.subject)
            rows2 = await session.execute(stmt2)
            subject_dist = [{"name": SUBJECT_NAMES.get(r.subject, r.subject), "count": r.cnt} for r in rows2.all()]

            return {"success": True, "data": {"totalProblems": total_problems, "totalErrors": total_errors, "accuracyRate": accuracy, "topErrors": top_errors, "subjectDist": subject_dist}}
    except Exception as e:
        print("Stats error:", e)
        traceback.print_exc()
        return {"success": True, "data": {"totalProblems":0,"totalErrors":0,"accuracyRate":"N/A","topErrors":[],"subjectDist":[]}}

@app.post("/api/record-error")
async def record_error(payload: dict):
    return {"success": True}

@app.get("/api/health")
async def health():
    return {"status": "ok", "llm_configured": llm_client is not None}

# ---- Serve frontend static files (production) ----
import os as _os
_FRONTEND_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "static")
if _os.path.isdir(_FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=_os.path.join(_FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend static files, fallback to index.html for SPA routing."""
        file_path = _os.path.join(_FRONTEND_DIR, full_path)
        if full_path and _os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(_os.path.join(_FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
