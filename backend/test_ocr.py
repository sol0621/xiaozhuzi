import os
import base64
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
from aip import AipOcr

APP_ID = os.getenv("BAIDU_OCR_APP_ID")
API_KEY = os.getenv("BAIDU_OCR_API_KEY")
SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY")

print("APP_ID:", APP_ID)
print("API_KEY:", API_KEY[:6] + "..." if API_KEY else None)
print("SECRET_KEY:", SECRET_KEY[:6] + "..." if SECRET_KEY else None)

client = AipOcr(APP_ID, API_KEY, SECRET_KEY)
# 用1x1透明png测试连通性
transparent_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
image_bytes = base64.b64decode(transparent_png_b64)
result = client.basicAccurate(image_bytes)
print("Response:", result)

code = result.get("error_code")
if code == 110 or code == 111:
    print("❌ 认证失败，请检查 AppID/API Key/Secret Key")
elif code == 216201:
    print("✅ 认证成功（216201=图片格式/大小错误，是透明小图导致的预期错误）")
elif code == 216630:
    print("✅ 认证成功（216630=未识别到文字，透明小图无文字是预期的）")
elif "words_result" in result:
    print("✅ 认证成功，正常返回结果")
else:
    print("ℹ️ 返回:", result)
