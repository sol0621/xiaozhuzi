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

def _resize_if_small(image_bytes: bytes, min_size: int = 1600) -> bytes:
    """小图放大——手写识别对分辨率有要求，长边<1600px 放大2倍。"""
    if not HAS_PIL:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        long_side = max(w, h)
        if long_side < min_size:
            scale = min_size / long_side
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            buf = io.BytesIO()
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=95)
            return buf.getvalue()
        return image_bytes
    except Exception as e:
        print(f"Resize error: {e}")
        return image_bytes

def _preprocess_handwriting(image_bytes: bytes) -> bytes:
    """手写优化版：灰度 + 强对比度 + 锐化 + 自适应阈值"""
    if not HAS_PIL:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 1. 转灰度
        gray = img.convert("L")

        # 2. 强烈增强对比度（红笔和淡色笔迹都更明显）
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(2.2)

        # 3. 双锐化（让字迹边缘锐利）
        gray = gray.filter(ImageFilter.SHARPEN)
        gray = gray.filter(ImageFilter.SHARPEN)

        # 4. 自动对比度拉伸（cutoff稍微大一点，去除背景阴影）
        gray = ImageOps.autocontrast(gray, cutoff=5)

        # 5. 二值化：手写体在白底上识别最准
        # 使用Otsu算法自动找阈值
        threshold = sum(gray.getdata()) / (gray.size[0] * gray.size[1])
        # 加点偏移，让红笔（转灰度后偏深）更容易被识别为文字
        threshold = max(100, min(180, threshold + 10))
        bw = gray.point(lambda p: 255 if p > threshold else 0)

        buf = io.BytesIO()
        bw.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception as e:
        print(f"Handwriting preprocess error: {e}")
        return image_bytes

def _preprocess_image(image_bytes: bytes) -> bytes:
    """兼容旧接口"""
    return _preprocess_handwriting(image_bytes)

async def _call_ocr(client, func, image_bytes: bytes, options: dict) -> str:
    """单次OCR调用包装"""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, func, image_bytes, options)
        words = [w.get("words", "") for w in resp.get("words_result", [])]
        return "\n".join(w for w in words if w)
    except Exception as e:
        print(f"OCR call error: {e}")
        return ""

async def ocr_image(image_bytes: bytes, mode: str = "handwriting") -> str:
    client = _get_client()
    if not client:
        return ""
    try:
        # 第1步：放大（如果是小图）
        upscaled = _resize_if_small(image_bytes, min_size=1600)

        # 第2步：手写优化预处理
        processed = _preprocess_handwriting(upscaled)

        options = {"detect_direction": "true", "probability": "false"}

        # 第3步：双引擎识别，取更长结果（解决红笔/淡笔容易漏识别的问题）
        if mode == "accurate":
            r1 = await _call_ocr(client, client.basicAccurate, processed, options)
            # 第二次用原图再试一次（有时预处理反而丢失信息）
            r2 = await _call_ocr(client, client.basicAccurate, upscaled, options)
        else:
            # 默认handwriting：用手写引擎+高精度引擎各跑一次
            r1 = await _call_ocr(client, client.handwriting, processed, options)
            r2 = await _call_ocr(client, client.basicAccurate, upscaled, options)

        # 取更长的结果
        return r1 if len(r1) >= len(r2) else r2
    except Exception as e:
        print("OCR error:", e)
        return ""

async def ocr_images(images: List[bytes]) -> str:
    results = await asyncio.gather(*(ocr_image(img) for img in images))
    return "\n".join(r for r in results if r)
