import os
import httpx
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("LLM_BASE_URL", "")
key = os.getenv("LLM_API_KEY", "")
model = os.getenv("LLM_MODEL", "")

print(f"Base URL: {url}")
print(f"Model: {model}")
print(f"Key length: {len(key)}")

if not url or not key:
    print("ERROR: 配置缺失，请检查 .env")
    exit(1)

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}
payload = {
    "model": model,
    "messages": [{"role": "user", "content": "请只回复一个字：通"}],
    "max_tokens": 10,
}

try:
    r = httpx.post(f"{url}/chat/completions", headers=headers, json=payload, timeout=20)
    print(f"HTTP Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
    if r.status_code == 200:
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        print(f"\n✅ 连通成功！模型回复: {content.strip()}")
    else:
        print(f"\n⚠️ 连通但返回非200，请检查模型名称或API Key")
except httpx.ConnectError as e:
    print(f"\n❌ 连接失败：无法访问 {url}")
    print(f"Detail: {e}")
except Exception as e:
    print(f"\n❌ 请求异常: {type(e).__name__}: {e}")
