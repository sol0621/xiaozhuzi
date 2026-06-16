"""
拆题引擎：将 OCR 文本切分为独立题目 + 题型分类。

策略：正则规则引擎（处理 80% 场景） + 碎片合并 + 异常检测。
"""
import re
from typing import List, Dict, Tuple

# ---- 题号识别正则 ----
QUESTION_NO_PATTERNS = [
    # 1. 1、 1） ① [1] 第1题
    (r'^\s*(\d+)\s*[.、．)〕］]', lambda m: int(m.group(1))),
    # (1) (2)
    (r'^\s*\(\s*(\d+)\s*\)', lambda m: int(m.group(1))),
    # 一、 二. 三）
    (r'^\s*([一二三四五六七八九十]+)\s*[、.．)]', lambda m: _chinese_to_int(m.group(1))),
    # 第X题
    (r'^\s*第\s*(\d+|[一二三四五六七八九十]+)\s*题', lambda m: _parse_num(m.group(1))),
]


def _chinese_to_int(s: str) -> int:
    """中文数字 → 整数。支持一~九十九。"""
    mapping = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
               '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    if s in mapping:
        return mapping[s]
    if len(s) == 1:
        return mapping.get(s, 0)
    if s.startswith('十'):
        return 10 + mapping.get(s[1], 0)
    if s.endswith('十'):
        return mapping.get(s[0], 0) * 10
    parts = s.split('十')
    if len(parts) == 2:
        return mapping.get(parts[0], 0) * 10 + mapping.get(parts[1], 0)
    return 0


def _parse_num(s: str) -> int:
    """通用数字解析。"""
    try:
        return int(s)
    except ValueError:
        return _chinese_to_int(s)


# ---- 题型分类信号 ----
TYPE_SIGNALS: List[Tuple[str, List[str]]] = [
    ('choice', [
        r'[A-Da-d]\s*[.、．)]',           # A. B. C.
        r'选一选|选择题|单选|多选',
        r'选出|选择正确|选出正确的',
        r'把正确答案|正确答案是',
    ]),
    ('true_false', [
        r'判断|判断对错|对的打|错的打',
        r'[√✓]|×|打[√✓×]|画[√✓×]',
        r'正确.*错误|对的.*错的',
    ]),
    ('fill_blank', [
        r'_{2,}',                        # ________
        r'（\s*）|\(\s*\)',              # （） ()
        r'填空|填入|填上|横线',
        r'看拼音.*写|根据拼音',
    ]),
    ('calculation', [
        r'[+\-×÷=]',
        r'计算|口算|竖式|脱式|递等式|解方程|列式|简便|估算|求值|约分|通分',
        r'得数|结果',
    ]),
    ('equation', [
        r'解方程|求\s*\w+\s*的值|未知数|设\s*\w',
    ]),
    ('application', [
        r'应用|解决|问题|应用题',
        r'已知.*求|条件.*问题',
        r'一共|还剩|多少|几倍|平均',
    ]),
    ('geometry', [
        r'面积|周长|体积|表面积|角度|对称|平移|旋转',
        r'画.*角|画.*线|画.*图|画出',
    ]),
    ('reading', [
        r'阅读|短文|文章|根据.*内容|读一读',
        r'这段话|这段文字|这篇',
    ]),
    ('composition', [
        r'作文|写话|写一写|习作|日记|周记',
        r'写.*字|写.*篇',
    ]),
    ('matching', [
        r'连线|连一连|搭配|配对|对应',
    ]),
    ('translation', [
        r'翻译|译|英译汉|汉译英|译成',
    ]),
    ('pinyin', [
        r'看拼音|拼音|注音|读音',
    ]),
    ('experiment', [
        r'实验|观察|记录|探究|调查',
    ]),
]


def classify_question_type(text: str) -> str:
    """根据文本信号分类题型。"""
    text_lower = text.lower()
    # 按优先级从具体到笼统
    priority = ['composition', 'reading', 'experiment', 'matching',
                'translation', 'pinyin', 'equation', 'application',
                'geometry', 'calculation', 'true_false', 'choice',
                'fill_blank']
    for type_name in priority:
        patterns = dict(TYPE_SIGNALS).get(type_name, [])
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return type_name
    return 'short_answer'


# ---- 拆题主逻辑 ----
def _split_into_segments(lines: List[str]) -> List[Tuple[int, int, int]]:
    """
    扫描行列表，按题号模式切分为 (start_idx, end_idx, q_number)。
    end_idx 暂为 None，后续补填。
    """
    segments = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern, extractor in QUESTION_NO_PATTERNS:
            m = re.match(pattern, stripped)
            if m:
                num = extractor(m)
                segments.append((i, None, num))
                break

    # 无任何题号 → 整段为一题
    if not segments:
        text = '\n'.join(l for l in lines if l.strip())
        if text.strip():
            return [(0, len(lines), 1)]
        return []

    # 补填 end_idx
    result = []
    for idx, (start, _, num) in enumerate(segments):
        if idx + 1 < len(segments):
            end = segments[idx + 1][0]
        else:
            end = len(lines)
        result.append((start, end, num))
    return result


def _build_questions(lines: List[str], segments: List[Tuple[int, int, int]]) -> List[Dict]:
    """从切分段构建题目列表。"""
    questions = []
    for start, end, q_num in segments:
        q_lines = []
        for j in range(start, end):
            line = lines[j].strip()
            if line:
                q_lines.append(line)
        content = '\n'.join(q_lines)
        if content.strip():
            questions.append({
                'id': q_num,
                'content': content,
                'type': classify_question_type(content),
            })
    # 重排 ID 为连续整数
    for i, q in enumerate(questions):
        q['id'] = i + 1
    return questions


def _merge_fragments(questions: List[Dict]) -> List[Dict]:
    """
    合并 OCR 碎片：极短且无题型信号的片段可能是上一题的残片。
    """
    if len(questions) <= 1:
        return questions

    merged = []
    for q in questions:
        content = q['content']
        # 内容太短 + 无题型信号 → 可能是碎片
        is_likely_fragment = (
            len(content) < 30
            and q['type'] == 'short_answer'
            and not re.search(r'\d+[.、．)]', content)
        )
        if merged and is_likely_fragment:
            merged[-1]['content'] += '\n' + content
            # 重新判定题型
            merged[-1]['type'] = classify_question_type(merged[-1]['content'])
        else:
            merged.append(q)

    for i, q in enumerate(merged):
        q['id'] = i + 1
    return merged


def _validate_split(questions: List[Dict]) -> bool:
    """
    验证拆题质量。返回 False 表示拆分质量差，建议 LLM 兜底。
    判定标准：
    - 题目数合理（1-30）
    - 平均长度合理（>20 字符）
    - 碎片率低（<30% 的题目 <15 字符）
    """
    if not questions:
        return False
    if len(questions) > 30:
        return False
    avg_len = sum(len(q['content']) for q in questions) / len(questions)
    if avg_len < 15:
        return False
    short_count = sum(1 for q in questions if len(q['content']) < 15)
    if short_count / len(questions) > 0.3:
        return False
    return True


def parse(text: str) -> Tuple[List[Dict], bool]:
    """
    主入口：解析 OCR 文本为结构化题目列表。

    Args:
        text: OCR 识别的完整文本

    Returns:
        (questions, is_reliable)
        - questions: [{id, content, type}, ...]
        - is_reliable: 拆分质量是否可靠（False 时建议 LLM 兜底）
    """
    if not text or not text.strip():
        return [], False

    lines = text.strip().split('\n')
    segments = _split_into_segments(lines)
    questions = _build_questions(lines, segments)
    questions = _merge_fragments(questions)
    is_reliable = _validate_split(questions)

    return questions, is_reliable


def format_for_llm(questions: List[Dict]) -> str:
    """
    将拆好的题目格式化为 LLM 友好的文本块。
    """
    type_names = {
        'choice': '选择题', 'true_false': '判断题', 'fill_blank': '填空题',
        'calculation': '计算题', 'equation': '解方程', 'application': '应用题',
        'geometry': '图形题', 'reading': '阅读理解', 'composition': '作文',
        'matching': '连线题', 'translation': '翻译题', 'pinyin': '拼音题',
        'experiment': '实验题', 'short_answer': '简答题',
    }
    lines = []
    for q in questions:
        tname = type_names.get(q['type'], '简答题')
        lines.append(f"第{q['id']}题 [{tname}] {q['content']}")
    return '\n\n'.join(lines)
