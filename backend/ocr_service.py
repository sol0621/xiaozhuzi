import os
import io
import asyncio
from typing import List, Optional, Tuple
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


# ---- Image Preprocessing Pipeline (双版本输出) ----
def _preprocess_image(image_bytes: bytes) -> Tuple[bytes, bytes]:
    """
    图像预处理：返回两个版本的图片
      - 版本A（二值化版）：Otsu自适应二值化，手写文字最清晰
      - 版本B（灰度增强版）：不做二值化，保留√×等小符号的灰度细节
    """
    img = Image.open(io.BytesIO(image_bytes))

    # 1. 小图自动放大
    w, h = img.size
    scale = 2
    if max(w, h) < 800:
        scale = 4  # 极小的图放大4倍
    elif max(w, h) < 1600:
        scale = 3  # 中等图放大3倍（提高√×等小符号分辨率）
    if scale > 1:
        img = img.resize((w * scale, h * scale), Image.LANCZOS)
        w, h = img.size

    # 2. 转灰度
    if img.mode != "L":
        gray = img.convert("L")
    else:
        gray = img

    # 3. 强对比度增强（2.5x，比之前更强）
    enhancer = ImageEnhance.Contrast(gray)
    enhanced = enhancer.enhance(2.5)

    # 4. 锐化
    enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))

    # 5. 自动对比度拉伸
    enhanced = ImageOps.autocontrast(enhanced, cutoff=1)

    # ---- 版本B：灰度增强版（不做二值化，保留√×等小符号） ----
    out_b = io.BytesIO()
    enhanced.save(out_b, format="PNG")
    version_b = out_b.getvalue()

    # ---- 版本A：Otsu二值化版（手写文字最清晰） ----
    arr = np.array(enhanced, dtype=np.uint8)
    hist, _ = np.histogram(arr.ravel(), 256, [0, 256])
    total = arr.size
    sum_all = np.dot(np.arange(256), hist)
    weight_bg = 0
    sum_bg = 0
    max_var = 0
    threshold = 128

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
    binary_img = Image.fromarray(binary_arr, mode="L")

    out_a = io.BytesIO()
    binary_img.save(out_a, format="PNG")
    version_a = out_a.getvalue()

    return version_a, version_b


# ---- Multi-Engine OCR ----
async def _ocr_single(client, image_bytes: bytes, mode: str) -> List[str]:
    """单次 OCR 调用，返回词条列表（非合并文本），便于后续去重。"""
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
        elif mode == "general":
            resp = await loop.run_in_executor(
                None, client.basicGeneral, image_bytes, {"detect_direction": "true"}
            )
        else:
            return []
        return [w.get("words", "") for w in resp.get("words_result", [])]
    except Exception as e:
        print(f"OCR [{mode}] error:", e)
        return []


def _merge_results(all_lines: List[List[str]]) -> str:
    """
    合并多引擎结果，去重保留完整内容。
    策略：
      1. 收集所有非空行
      2. 按相似度去重（同一行如果 80% 相同，保留更长的）
      3. 按原顺序返回合并文本
    """
    # 展平+去空白
    seen = []
    for lines in all_lines:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 检查是否与已有行高度相似
            is_dup = False
            for i, existing in enumerate(seen):
                if _is_similar(line, existing, threshold=0.75):
                    is_dup = True
                    # 保留更长的版本
                    if len(line) > len(existing):
                        seen[i] = line
                    break
            if not is_dup:
                seen.append(line)

    # 尝试按原始顺序排列（简单启发式：短行在前更可能是标题/题号）
    seen.sort(key=lambda x: (len(x) < 4, x))
    
    return "\n".join(seen)


def _is_similar(a: str, b: str, threshold: float = 0.75) -> bool:
    """判断两个字符串是否高度相似（用于去重）。"""
    if not a or not b:
        return False
    # 短字符串精确匹配
    if len(a) <= 3 or len(b) <= 3:
        return a == b
    
    # 长字符串：检查是否一个包含另一个，或重叠字符比例高
    shorter = a if len(a) < len(b) else b
    longer = b if len(a) < len(b) else a
    
    # 包含关系
    if shorter in longer:
        return True
    
    # 字符重叠率
    overlap = sum(1 for c in shorter if c in longer)
    return overlap / len(shorter) > threshold


async def ocr_image(image_bytes: bytes) -> str:
    """
    多版本 + 多引擎 OCR，合并去重。
    
    流程：
      1. 生成 2 个预处理版本（二值化版 + 灰度增强版）
      2. 2 个版本 × 2 个引擎（handwriting/general）= 4 路并发 OCR
      3. 合并去重所有结果
      4. 如果总字数 < 20，用原始图再跑 handwrite + general 兜底
    """
    client = _get_client()
    if not client:
        return ""

    # Step 1: 图像预处理（双版本）
    try:
        bin_img, gray_img = _preprocess_image(image_bytes)
    except Exception as e:
        print("Preprocess error:", e)
        bin_img = gray_img = image_bytes

    # Step 2: 多版本多引擎并行 OCR（4 路并发）
    #   - handwriting + 二值化版：手写文字识别主力
    #   - handwriting + 灰度版：保留√×等小符号灰度细节
    #   - general + 二值化版：补充印刷体识别
    #   - general + 灰度版：general 对简单符号(√×)识别更好
    tasks = [
        _ocr_single(client, bin_img, "handwriting"),
        _ocr_single(client, gray_img, "handwriting"),
        _ocr_single(client, bin_img, "general"),
        _ocr_single(client, gray_img, "general"),
    ]

    all_results = await asyncio.gather(*tasks)

    # Step 3: 合并去重
    result = _merge_results(all_results)

    # Step 4: 如果结果太少（< 20 字符），用原始图再跑一遍
    if len(result.strip()) < 20:
        raw_tasks = [
            _ocr_single(client, image_bytes, "handwriting"),
            _ocr_single(client, image_bytes, "general"),
        ]
        raw_results = await asyncio.gather(*raw_tasks)
        fallback = _merge_results(raw_results)
        if len(fallback) > len(result):
            result = fallback

    return result


async def ocr_images(images: List[bytes]) -> str:
    """并发处理多张图片。"""
    results = await asyncio.gather(*(ocr_image(img) for img in images))
    return "\n".join(r for r in results if r)
