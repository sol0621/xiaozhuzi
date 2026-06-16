import os
import io
import asyncio
from typing import List
from aip import AipOcr

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

_APP_ID = os.getenv("BAIDU_OCR_APP_ID", "")
_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")

_client = None

def _get_client():
    global _client
    if _client is None and _APP_ID and _API_KEY and _SECRET_KEY:
        _client = AipOcr(_APP_ID, _API_KEY, _SECRET_KEY)
    return _client

def _preprocess_image(image_bytes: bytes) -> bytes:
    """预处理图片：增强对比度、转灰度，让手写（尤其是红笔）更清晰。"""
    if not HAS_PIL:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # 1. 转灰度
        if img.mode != "L":
            img = img.convert("L")

        # 2. 增强对比度（让淡色笔迹更明显）
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # 3. 锐化——让笔迹边缘更清晰
        img = img.filter(ImageFilter.SHARPEN)

        # 4. 自动对比度拉伸
        img = ImageOps.autocontrast(img, cutoff=3)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except Exception as e:
        print(f"Image preprocess error: {e}")
        return image_bytes

async def ocr_image(image_bytes: bytes, mode: str = "handwriting") -> str:
    client = _get_client()
    if not client:
        return ""
    try:
        # 预处理图片（增强对比度让红笔更清楚）
        processed = _preprocess_image(image_bytes)

        loop = asyncio.get_event_loop()
        options = {"detect_direction": "true", "probability": "true"}
        if mode == "accurate":
            resp = await loop.run_in_executor(None, client.basicAccurate, processed, options)
        elif mode == "handwriting":
            resp = await loop.run_in_executor(None, client.handwriting, processed, options)
        else:
            resp = await loop.run_in_executor(None, client.basicGeneral, processed, options)
        words = [w.get("words", "") for w in resp.get("words_result", [])]
        return "\n".join(words)
    except Exception as e:
        print("OCR error:", e)
        return ""

async def ocr_images(images: List[bytes]) -> str:
    results = await asyncio.gather(*(ocr_image(img) for img in images))
    return "\n".join(r for r in results if r)
