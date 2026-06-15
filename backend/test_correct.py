import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("LLM_BASE_URL", "")
key = os.getenv("LLM_API_KEY", "")
model = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """你是一位小学作业辅导专家。请根据用户提供的年级、科目和作业内容，逐题批改。

## 规则
1. 如果作业内容含有孩子作答的答案，执行【批改模式】：逐题判断对错，给出简要评语。
2. 如果作业内容只有题目没有答案，执行【直接解答模式】：给出完整解答，不判断对错。
3. 严格遵循年级规范，不得使用超纲方法。

## 输出格式（JSON）
{
  "mode": "correct",
  "page_status": "ok",
  "problems": [
    {
      "number": 1,
      "status": "ok",
      "question": "题目文本",
      "student_answer": "孩子答案",
      "correct_answer": "正确答案",
      "is_correct": true | false,
      "comment": "评语"
    }
  ]
}
"""

USER_PROMPT = """年级：4
科目：math
年级规范：四年级数学禁用：方程、代数式、比例式、负数、二元方程组。只能用算术方法。

请识别并批改以下作业内容。

题目：
1. 25 + 38 = ？  孩子答案：63
2. 72 - 45 = ？  孩子答案：27
3. 12 × 3 = ？   孩子答案：36
4. 48 ÷ 6 = ？   孩子答案：7
"""

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ],
    "temperature": 0.3,
    "response_format": {"type": "json_object"},
}

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}

print("=" * 50)
print("批改场景测试（四年级数学，4道题）")
print("=" * 50)

try:
    r = httpx.post(f"{url}/chat/completions", headers=headers, json=payload, timeout=120)
    print(f"HTTP Status: {r.status_code}")

    if r.status_code != 200:
        print(f"Error: {r.text[:500]}")
        exit(1)

    data = r.json()
    content = data["choices"][0]["message"]["content"]

    # 尝试解析 JSON
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # 可能包含 markdown 代码块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        result = json.loads(content)

    print(f"\n解析成功！mode={result.get('mode')}, page_status={result.get('page_status')}")
    print(f"共识别 {len(result.get('problems', []))} 道题：\n")

    for p in result.get("problems", []):
        correct = "✅" if p.get("is_correct") else "❌"
        print(f"  第{p.get('number')}题 {correct} {p.get('question')}")
        print(f"    孩子答案: {p.get('student_answer')}")
        print(f"    正确答案: {p.get('correct_answer')}")
        print(f"    评语: {p.get('comment')}")
        print()

    print("✅ 批改测试通过！模型返回格式正确。")

except Exception as e:
    print(f"\n❌ 测试异常: {type(e).__name__}: {e}")
    if 'r' in dir():
        print(f"原始响应: {r.text[:1000]}")
