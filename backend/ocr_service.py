import os
import io
import asyncio
from typing import List, Optional
from aip import AipOcr
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

_APP_ID = os.getenv("BAIDU_OCR_APP_ID", "")
_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")

_client = None

def _get_client():
    global _client
    if _client is None and _APP_ID and _API_KEY and _SECRET_KEY:
        _client = AipOcr(_APP_ID, _API_KEY, _SECRET_KEY)
    return _client


# ---- Image Preprocessing Pipeline ----
def _preprocess_image(image_bytes: bytes) -> bytes:
    """
    图像预处理管线：放大 → 灰度 → 对比度增强 → 锐化 → Otsu二值化
    解决手写红笔/淡笔/低分辨率照片识别不稳定问题。
    返回处理后的 bytes（PNG格式，保证质量）。
    """
    img = Image.open(io.BytesIO(image_bytes))

    # 1. 小图自动放大：长边 < 1600px → 放大 2 倍（手写识别对分辨率敏感）
    w, h = img.size
    if max(w, h) < 1600:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)

    # 2. 转灰度
    if img.mode != "L":
        img = img.convert("L")

    # 3. 强对比度增强（2.2x）
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.2)

    # 4. 锐化（UnsharpMask 比普通 SHARPEN 更可控）
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))

    # 5. 自动对比度拉伸（将像素范围拉伸到 0-255，消除灰雾）
    img = ImageOps.autocontrast(img, cutoff=2)

    # 6. Otsu 自适应二值化：手写体在白底上识别最准
    arr = np.array(img, dtype=np.uint8)
    # 计算 Otsu 阈值
    hist, _ = np.histogram(arr.ravel(), 256, [0, 256])
    total = arr.size
    sum_all = np.dot(np.arange(256), hist)
    weight_bg = 0
    sum_bg = 0
    max_var = 0
    threshold = 128  # fallback

    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var_between > max_var:
            max_var = var_between
            threshold = t

    binary_arr = np.where(arr > threshold, 255, 0).astype(np.uint8)
    img = Image.fromarray(binary_arr, mode="L")

    # 输出为 PNG bytes
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


# ---- Dual-Engine OCR ----
async def _ocr_single(client, image_bytes: bytes, mode: str) -> str:
    """单次 OCR 调用（在线程池执行，避免阻塞异步事件循环）。"""
    loop = asyncio.get_event_loop()
    try:
        if mode == "handwriting":
            resp = await loop.run_in_executor(
                None, client.handwriting, image_bytes, {"detect_direction": "true"}
            )
        elif mode == "accurate":
            resp = await loop.run_in_executor(
                None, client.basicAccurate, image_bytes, {"detect_direction": "true"}
            )
        else:
            resp = await loop.run_in_executor(
                None, client.basicGeneral, image_bytes, {"detect_direction": "true"}
            )
        words = [w.get("words", "") for w in resp.get("words_result", [])]
        return "\n".join(words)
    except Exception as e:
        print(f"OCR [{mode}] error:", e)
        return ""


async def ocr_image(image_bytes: bytes) -> str:
    """
    双引擎 OCR：handwriting + basicAccurate 各跑一次，
    取结果更长的那个（解决红笔/淡笔单引擎漏识别问题）。
    
    预处理后的图片分别送两个引擎，提高手写识别覆盖率。
    """
    client = _get_client()
    if not client:
        return ""

    # 图像预处理
    try:
        processed = _preprocess_image(image_bytes)
    except Exception as e:
        print("Preprocess error, falling back to raw:", e)
        processed = image_bytes

    # 双引擎并行识别
    hw_task = _ocr_single(client, processed, "handwriting")
    acc_task = _ocr_single(client, processed, "accurate")

    hw_text, acc_text = await asyncio.gather(hw_task, acc_task)

    # 取更长的结果（更长的通常意味着识别到了更多内容）
    result = hw_text if len(hw_text) >= len(acc_text) else acc_text

    # 如果双引擎都几乎没识别到，尝试原始图片再跑一次 handwrite
    if len(result.strip()) < 3:
        raw_text = await _ocr_single(client, image_bytes, "handwriting")
        if len(raw_text) > len(result):
            result = raw_text

    return result


async def ocr_images(images: List[bytes]) -> str:
    """并发处理多张图片。"""
    results = await asyncio.gather(*(ocr_image(img) for img in images))
    return "\n".join(r for r in results if r)
