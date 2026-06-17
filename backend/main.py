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
from sqlalchemy import func, select

# ---- LLM config ----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
ENABLE_OCR = os.getenv("ENABLE_OCR", "true").lower() == "true"

llm_client: Optional[AsyncOpenAI] = None
if LLM_BASE_URL and LLM_API_KEY:
    llm_client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

# ---- Grade rules ----
GRADE_RULES = {
    4: {
        "math": "四年级数学允许：线段图、示意画图、分步计算、凑整法、列举法、倒推法、运算定律简化。严禁：方程（含用字母表示数）、代数推导、比例式、负数、分数乘除法。",
        "chinese": "四年级语文：错别字/拼音/笔顺、基础标点、把字句/被字句、事件四要素、直接引语改间接引语（基础）。严禁：文言文语法、作者心理深度分析、文学流派术语。",
        "english": "四年级英语（北京版一年级起点）：一般现在时（含三单）、现在进行时（be+doing）、基本句型转换、方位介词、there be基础、祈使句。严禁：一般过去时、比较级/最高级、一般将来时、音标系统教学、任何从句。",
        "science": "四年级科学：声音由振动产生、简单电路与导体绝缘体分类、岩石外部特征、动植物生命周期、天气观测。严禁：频率公式、欧姆定律、食物链能量计算、化学成分分析、光合作用方程式。",
    },
    5: {
        "math": "五年级数学允许：四年级全部+简易方程（一步/两步求解）、分数与小数互化、统计图表读取、因数分解（短除法）、长方体/正方体表面积和体积。严禁：负数、二元一次方程组、代数恒等变形、复杂多步比例、分数乘除法。",
        "chinese": "五年级语文：四年级全部+修辞（比喻/拟人/排比/夸张/设问/反问，只讲实例不上术语定义）、说明方法（举例子/列数字/打比方/作比较）、中心句提取、段意概括、简单文言文只翻译字词、人物性格特点。严禁：文言文语法、过度推断、高中文学鉴赏术语、文化批评视角。",
        "english": "五年级英语：四年级全部+一般过去时（规则/不规则常见20-30个）、形容词比较级/最高级（-er/-est）、一般将来时be going to（只讲'打算做某事'）、情态动词can/may/must口语区别。严禁：现在完成时、被动语态、任何从句、虚拟语气、动词不定式作成分。",
        "science": "五年级科学：四年级全部+光的直线传播/反射/折射现象、食物链关系（只讲'谁吃谁'，不计算能量）、沉浮只定性、热传导/对流/辐射现象、简单机械定性（省力/费力）。严禁：浮力公式、杠杆平衡条件定量计算、能量守恒定律系统讲解、折射定律。",
    },
    6: {
        "math": "六年级数学允许：五年级全部+一元一次方程（含分数系数）、比例式、百分数应用题（折扣/利率/成数）、圆/圆柱/圆锥表面积和体积、负数概念（仅认识，不进行四则运算）。严禁：负数四则运算、二元一次方程组、函数概念、一元二次方程、无理数。",
        "chinese": "六年级语文：五年级全部+表达手法（借物喻人/对比/托物言志，只讲示例不上术语定义）、简单读后感（联系自身）、非连续性文本读取、小说人物简单分析（性格特点+情节作用）。严禁：初中及以上文言语法、社会历史宏大叙事分析、文学批评理论。",
        "english": "六年级英语：五年级全部+will与be going to口语区别（'早有打算/临时决定'，只给例句）、there be时态扩展、可数/不可数+some/any/much/many、规则动词过去式拼写。严禁：现在完成时、被动语态、任何从句（包括宾语从句）、条件句术语（只讲'如果...就...'）、动词不定式作成分、动名词作主语。",
        "science": "六年级科学：五年级全部+细胞基本结构（膜/质/核，知道植物有壁和叶绿体）、物质变化看现象（变色/冒泡/发热/沉淀=化学变化，不写方程式）、能量形式转换定性、地球自转/公转定性、生物分类到纲/目层级。严禁：化学方程式配平、物理公式定量计算（密度/压强/浮力/欧姆定律）、细胞器精细结构、光合作用/呼吸作用方程式、开普勒定律、基因详细结构。",
    }
}

SUBJECT_NAMES = {"math":"数学","chinese":"语文","english":"英语","science":"科学"}

# ---- Prompt builders ----
def get_system_prompt(grade: int, subject: str) -> str:
    rule = GRADE_RULES.get(grade, {}).get(subject, "")
    return f"""你是一位{grade}年级{SUBJECT_NAMES.get(subject, subject)}作业批改老师。
{rule}

跨科目统一红线：
1. 禁止输出原始JSON/PLHD/任何机器数据结构。
2. 禁止输出"我不知道""这题我不会"——必须给出基于年级边界的最佳尝试。
3. 禁止贬低学生，不得出现"这么简单的题都错"等负面评价。
4. 禁止使用成人社交俚语/网络黑话。
5. 数学禁止计算器思维，必须展示手算步骤。

批改规则：
- 如果每道题都有明确的"答案/结果/=数字"，则进入【批改模式】，判断每题对错。
- 如果只有算式/题干没有答案（裸算式），则进入【直接解答模式】。

学科专项处理：
- 科学连线/配对题：OCR文本中所有连线对象均已列出时，必须用科学知识推理正确配对，输出为finalAnswer。
  从文本排列中推断学生连线（如有编号/字母）。能确定→判断对错；无法确定→status="answer_unclear"并给出正确配对。
- 科学填图/标注图（需要看图定位的）：status="partial_recognition"。
- 数学连线题同样处理：用数学知识推理正确配对。
- 语文连线/配对：用语文知识（拼音对应、词语搭配、近反义词等）推理正确配对。
- 英语连线/配对：用英语知识推理正确配对（如单词-翻译、图片描述等）。

输出格式要求（必须是合法JSON，不要markdown代码块）：
批改模式：{{"mode":"correction","questions":[{{"id":1,"content":"题目原文","studentAnswer":"学生答案","isCorrect":true/false,"wrongReason":"错误原因，仅错题","errorType":"错误类型标签如'计算错误'/'概念混淆'","status":"normal"}}]}}
直接解答模式：{{"mode":"direct-answer","questions":[{{"id":1,"content":"题目原文","explanation":"分步解答过程","finalAnswer":"最终答案","status":"normal"}}]}}

注意：
- 每道题status只能是"normal""answer_unclear""partial_recognition""unrecognizable"。
- 优先status为normal；答案模糊时标记answer_unclear并务必填充correctAnswer或studentAnswer（基于学科知识的最佳推断）。
- 连线/配对题的correctAnswer格式："A→X, B→Y, C→Z" 或 "1-c, 2-a, 3-b"，清晰列出配对关系。
- 整页无有效题目返回mode="error"，questions为空。
- 直接解答模式的explanation请用中文分步讲解，符合年级铁律。"""

def get_explain_prompt(grade: int, subject: str, question: str, student_answer: str, correct_answer: str, wrong_reason: str) -> str:
    rule = GRADE_RULES.get(grade, {}).get(subject, "")
    return f"""你是一位{grade}年级{SUBJECT_NAMES.get(subject, subject)}辅导老师，正给一位做错题的孩子讲解。
{rule}

跨科目红线：禁止JSON/贬低/俚语。步骤清晰，用"你"而非"我们"。数学必须给出至少两种方法（线段图+分步）。

题目：{question}
孩子的错误答案：{student_answer}
正确答案：{correct_answer}
判题发现的错因：{wrong_reason}

【关键要求】
1. 数学题必须用分步算式验证：一步一步推导，每一步都写出具体的算式和结果，最后验证是否与正确答案[{correct_answer}]一致。
2. 如果计算结果与[{correct_answer}]不符，必须重新检查每一步，找到错误并修正。
3. 不要盲目相信正确答案——如果经过验证发现它也可能是错的，在tip中提醒。

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
    system = get_system_prompt(grade, subject)
    user = f"以下是学生提交的{grade}年级{SUBJECT_NAMES.get(subject, subject)}作业内容，请按规则批改或解答：\n\n{full_text}"

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
    if mode == "correction":
        correct = sum(1 for q in questions if q.get("isCorrect"))
        wrong = total - correct
        result_data = {"mode": "correction", "totalCount": total, "correctCount": correct, "wrongCount": wrong, "questions": questions}
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
            )
            session.add(record)
            await session.flush()
            if result_data["mode"] == "correction":
                for q in questions:
                    if q.get("status") != "normal":
                        continue
                    session.add(ProblemRecord(
                        homework_id=record.id,
                        question_content=str(q.get("content", ""))[:500],
                        student_answer=str(q.get("studentAnswer", ""))[:500],
                        correct_answer="",  # LLM不直接返回正确答案，由后续讲解提供
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

@app.get("/api/analytics")
async def analytics(subject: Optional[str] = None):
    """学习分析报告：错误模式/薄弱知识点/趋势/学科对比。"""
    from analytics import get_full_analysis, get_error_patterns, get_weak_points, get_trends
    try:
        full = await get_full_analysis()
        if not full or full.get("overview", {}).get("totalProblems", 0) == 0:
            return {"success": False, "message": "暂无批改数据，请先提交作业"}
        # 若指定学科，覆盖筛选后的错误模式和薄弱点
        if subject:
            full["errorPatterns"] = await get_error_patterns(subject)
            full["weakPoints"] = await get_weak_points(subject)
        return {"success": True, "data": full}
    except Exception as e:
        print("Analytics error:", e)
        traceback.print_exc()
        return {"success": False, "message": f"分析失败：{str(e)}"}

@app.get("/api/mistake-book")
async def mistake_book(
    page: int = 1, page_size: int = 20,
    subject: Optional[str] = None, error_type: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None,
):
    """错题本：分页查询错题，支持按学科/错误类型/时间筛选。"""
    from sqlalchemy import desc as desc_
    from datetime import date as date_type
    try:
        async with async_session() as session:
            # 基础条件：只查错题
            conditions = [ProblemRecord.is_correct == 0]

            if error_type:
                conditions.append(ProblemRecord.error_type == error_type)

            # Join HomeworkRecord 获取 subject 和 grade
            join_conditions = [ProblemRecord.homework_id == HomeworkRecord.id]
            if subject:
                join_conditions.append(HomeworkRecord.subject == subject)

            # 日期筛选
            if start_date:
                conditions.append(func.date(ProblemRecord.created_at) >= start_date)
            if end_date:
                conditions.append(func.date(ProblemRecord.created_at) <= end_date)

            # 总数
            from sqlalchemy import join as sql_join
            count_stmt = (
                select(func.count(ProblemRecord.id))
                .select_from(ProblemRecord)
                .join(HomeworkRecord, *join_conditions)
                .where(and_(*conditions))
            )
            total = await session.scalar(count_stmt) or 0

            # 分页数据
            stmt = (
                select(ProblemRecord, HomeworkRecord.subject, HomeworkRecord.grade)
                .select_from(ProblemRecord)
                .join(HomeworkRecord, *join_conditions)
                .where(and_(*conditions))
                .order_by(desc_(ProblemRecord.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            rows = await session.execute(stmt)
            problems = []
            for pr, subj, grd in rows.all():
                problems.append({
                    "id": pr.id,
                    "subject": SUBJECT_NAMES.get(subj, subj),
                    "grade": grd,
                    "question_content": pr.question_content or "",
                    "student_answer": pr.student_answer or "",
                    "correct_answer": pr.correct_answer or "",
                    "wrong_reason": pr.wrong_reason or "",
                    "error_type": pr.error_type or "",
                    "parent_correction": pr.parent_correction or "",
                    "created_at": pr.created_at.isoformat() if pr.created_at else "",
                })

            # 错误类型汇总（用于筛选下拉）
            type_stmt = (
                select(ProblemRecord.error_type, func.count(ProblemRecord.id).label("cnt"))
                .select_from(ProblemRecord)
                .join(HomeworkRecord, ProblemRecord.homework_id == HomeworkRecord.id)
                .where(ProblemRecord.is_correct == 0)
                .group_by(ProblemRecord.error_type)
                .order_by(desc_("cnt"))
            )
            if subject:
                type_stmt = type_stmt.where(HomeworkRecord.subject == subject)
            type_rows = await session.execute(type_stmt)
            error_types = [{"type": r.error_type or "未分类", "count": r.cnt} for r in type_rows.all()]

            return {
                "success": True,
                "data": {
                    "problems": problems,
                    "errorTypes": error_types,
                    "total": total,
                    "page": page,
                    "pageSize": page_size,
                }
            }
    except Exception as e:
        print("MistakeBook error:", e)
        traceback.print_exc()
        return {"success": False, "message": f"查询失败：{str(e)}"}

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
