import os
import asyncio
from typing import List
from aip import AipOcr

_APP_ID = os.getenv("BAIDU_OCR_APP_ID", "")
_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")

_client = None

def _get_client():
    global _client
    if _client is None and _APP_ID and _API_KEY and _SECRET_KEY:
        _client = AipOcr(_APP_ID, _API_KEY, _SECRET_KEY)
    return _client

async def ocr_image(image_bytes: bytes, mode: str = "accurate") -> str:
    client = _get_client()
    if not client:
        return ""
    try:
        loop = asyncio.get_event_loop()
        if mode == "accurate":
            resp = await loop.run_in_executor(None, client.basicAccurate, image_bytes, {"detect_direction": "true"})
        elif mode == "handwriting":
            resp = await loop.run_in_executor(None, client.handwriting, image_bytes, {"detect_direction": "true"})
        else:
            resp = await loop.run_in_executor(None, client.basicGeneral, image_bytes, {"detect_direction": "true"})
        words = [w.get("words", "") for w in resp.get("words_result", [])]
        return "\n".join(words)
    except Exception as e:
        print("OCR error:", e)
        return ""

async def ocr_images(images: List[bytes]) -> str:
    results = await asyncio.gather(*(ocr_image(img) for img in images))
    return "\n".join(r for r in results if r)
