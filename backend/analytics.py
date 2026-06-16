"""
错误模式分析 + 薄弱点诊断 + 学习趋势
纯后端分析模块，基于 HomeworkRecord 和 ProblemRecord 的累积数据。
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import func, select, and_, desc, text
from database import async_session
from models import HomeworkRecord, ProblemRecord

# ============================================================
# 知识点体系（人教版 4-6 年级）
# ============================================================
KNOWLEDGE_POINTS = {
    "数学": {
        "4": [
            "大数的认识与读写", "三位数乘两位数", "除数是两位数的除法",
            "四则混合运算", "运算定律(交换律/结合律/分配律)",
            "分数的初步认识", "小数的意义与性质",
            "角的度量", "平行四边形和梯形",
            "条形统计图", "应用题(归一/归总)",
        ],
        "5": [
            "小数乘法", "小数除法", "简易方程",
            "多边形的面积", "分数的意义和性质",
            "分数的加减法", "因数与倍数",
            "长方体和正方体", "折线统计图",
            "应用题(行程/工程/盈亏)",
        ],
        "6": [
            "分数乘法", "分数除法", "百分数",
            "比和比例", "圆与扇形", "圆柱与圆锥",
            "负数", "统计与概率",
            "数学广角(鸽巢原理等)", "总复习综合",
        ],
    },
    "语文": {
        "4": [
            "看拼音写词语", "多音字/形近字辨析", "成语积累与运用",
            "关联词填空", "修改病句", "阅读理解(记叙文)",
            "古诗词背诵与默写", "口语交际", "作文(记事/写人)",
        ],
        "5": [
            "生字词辨析", "词语搭配与感情色彩", "句式变换",
            "标点符号", "阅读理解(说明文/散文)", "古诗词理解",
            "课文内容填空", "口语交际与综合性学习", "作文(想象/读后感)",
        ],
        "6": [
            "文言文实词虚词", "近义词/反义词辨析", "修辞手法",
            "段落概括与中心思想", "阅读理解(议论文/小说)", "古诗词鉴赏",
            "文学常识", "口语交际与辩论", "作文(议论文/演讲稿)",
        ],
    },
    "英语": {
        "4": [
            "字母大小写与书写", "基本词汇(颜色/数字/动物等)",
            "简单句型(There be/This is)", "人称代词与物主代词",
            "现在进行时", "一般疑问句", "听读能力",
        ],
        "5": [
            "词汇拼写(月份/季节/职业等)", "一般现在时(三单)",
            "一般过去时", "There be句型变体", "情态动词(can/must/should)",
            "形容词比较级", "短文阅读理解",
        ],
        "6": [
            "词汇拓展(抽象名词)", "现在完成时初步",
            "将来时(be going to/will)", "被动语态初步",
            "比较级与最高级", "状语从句(时间/条件)",
            "完形填空与阅读理解", "书面表达(50词短文)",
        ],
    },
    "科学": {
        "4": [
            "天气与气候", "溶解与溶液", "声音的产生与传播",
            "电路基础知识", "植物的生长与繁殖", "动物的分类",
            "岩石与矿物", "物质的状态变化",
        ],
        "5": [
            "生物与环境", "光与影", "地球的运动",
            "简单机械(杠杆/滑轮/斜面)", "力与运动", "热传递",
            "人体的消化与呼吸", "遗传与变异",
        ],
        "6": [
            "细胞与微生物", "物质的变化(物理/化学)", "能量转换",
            "太阳系与宇宙", "环境与生态", "技术与工程",
            "科学探究方法", "总复习综合",
        ],
    },
}

SUBJECT_NAMES = {"math": "数学", "chinese": "语文", "english": "英语", "science": "科学"}

# ============================================================
# 错误模式 → 知识点映射（关键词匹配）
# ============================================================
ERROR_TO_KNOWLEDGE = {
    # 数学常见错误关键词 → 知识点
    "计算错误": ["四则混合运算", "小数乘法", "小数除法", "分数乘法", "分数除法", "百分数"],
    "进位错误": ["三位数乘两位数", "小数乘法"],
    "公式错误": ["多边形的面积", "长方体和正方体", "圆与扇形", "圆柱与圆锥"],
    "概念混淆": ["小数的意义与性质", "分数的意义和性质", "比和比例"],
    "单位换算": ["小数的意义与性质", "分数的意义和性质"],
    "方程错误": ["简易方程"],
    "应用题审题": ["应用题(归一/归总)", "应用题(行程/工程/盈亏)"],
    "运算顺序": ["四则混合运算"],
    "几何图形": ["角的度量", "平行四边形和梯形", "圆与扇形"],
    # 语文
    "拼写错误": ["看拼音写词语", "生字词辨析"],
    "词语搭配": ["词语搭配与感情色彩"],
    "阅读理解偏差": ["阅读理解(记叙文)", "阅读理解(说明文/散文)", "阅读理解(议论文/小说)"],
    "古诗词默写": ["古诗词背诵与默写", "古诗词理解", "古诗词鉴赏"],
    "病句未改出": ["修改病句"],
    "文言文理解": ["文言文实词虚词"],
    "作文跑题": ["作文(记事/写人)", "作文(想象/读后感)", "作文(议论文/演讲稿)"],
    # 英语
    "拼写": ["词汇拼写(月份/季节/职业等)", "基本词汇(颜色/数字/动物等)"],
    "语法": ["一般现在时(三单)", "一般过去时", "现在进行时"],
    "时态": ["一般现在时(三单)", "一般过去时", "现在完成时初步", "将来时(be going to/will)"],
    "单词遗忘": ["基本词汇(颜色/数字/动物等)", "词汇拓展(抽象名词)"],
    "语序错误": ["简单句型(There be/This is)", "状语从句(时间/条件)"],
    # 科学
    "概念模糊": ["天气与气候", "物质的状态变化", "能量转换"],
    "术语不准确": ["细胞与微生物", "溶解与溶液", "力与运动"],
    "实验步骤": ["科学探究方法", "电路基础知识"],
    "知识点混淆": ["生物与环境", "光与影", "物质的变化(物理/化学)"],
}


async def _run_analysis_queries() -> dict:
    """执行所有分析查询，返回结构化数据。"""
    async with async_session() as session:
        # ---- 1. 总量统计 ----
        total_homeworks = await session.scalar(select(func.count(HomeworkRecord.id))) or 0
        total_problems = await session.scalar(select(func.count(ProblemRecord.id))) or 0
        total_wrong = await session.scalar(
            select(func.count(ProblemRecord.id)).where(ProblemRecord.is_correct == 0)
        ) or 0
        total_correct = total_problems - total_wrong
        accuracy = round(total_correct / total_problems * 100, 1) if total_problems else 0.0

        # ---- 2. 错误模式分析 ----
        stmt = (
            select(ProblemRecord.error_type, func.count(ProblemRecord.id).label("cnt"))
            .where(ProblemRecord.is_correct == 0)
            .group_by(ProblemRecord.error_type)
            .order_by(desc("cnt"))
        )
        rows = await session.execute(stmt)
        error_patterns = []
        for r in rows.all():
            label = r.error_type or "未分类"
            error_patterns.append({
                "type": label,
                "count": r.cnt,
                "percent": round(r.cnt / total_wrong * 100, 1) if total_wrong else 0,
            })

        # ---- 3. 薄弱知识点诊断 ----
        # 合并所有错题的错误信息，映射到知识点
        stmt = (
            select(ProblemRecord.subject, ProblemRecord.error_type, ProblemRecord.wrong_reason,
                   func.count(ProblemRecord.id).label("cnt"))
            .where(ProblemRecord.is_correct == 0)
            .group_by(ProblemRecord.subject, ProblemRecord.error_type, ProblemRecord.wrong_reason)
            .order_by(desc("cnt"))
        )
        rows = await session.execute(stmt)
        knowledge_scores = {}  # {knowledge_point: score}
        for r in rows.all():
            subject = SUBJECT_NAMES.get(r.subject, r.subject)
            error_type = r.error_type or ""
            wrong_reason = r.wrong_reason or ""
            combined = f"{error_type} {wrong_reason}"

            # 关键词匹配
            matched = set()
            for keyword, kps in ERROR_TO_KNOWLEDGE.items():
                if keyword in combined:
                    for kp in kps:
                        matched.add(f"[{subject}] {kp}")

            # 如果没匹配到任何知识点，标记为待分类
            if not matched:
                matched.add(f"[{subject}] 综合能力（{error_type or '未分类'}）")

            for kp in matched:
                knowledge_scores[kp] = knowledge_scores.get(kp, 0) + r.cnt

        # 排序取 Top 15
        weak_points = sorted(
            [{"point": k, "error_count": v, "severity": _severity_label(v)} for k, v in knowledge_scores.items()],
            key=lambda x: x["error_count"], reverse=True
        )[:15]

        # ---- 4. 学习趋势 ----
        # 按周汇总
        trends = await _get_weekly_trends(session)

        # ---- 5. 学科对比 ----
        subject_stats = []
        all_subjects = list(set(
            (await session.execute(select(ProblemRecord.subject).distinct())).scalars().all()
        ))
        for subj in all_subjects:
            name = SUBJECT_NAMES.get(subj, subj)
            cnt = await session.scalar(
                select(func.count(ProblemRecord.id)).where(ProblemRecord.subject == subj)
            ) or 0
            wrong = await session.scalar(
                select(func.count(ProblemRecord.id)).where(
                    ProblemRecord.subject == subj, ProblemRecord.is_correct == 0
                )
            ) or 0
            acc = round((cnt - wrong) / cnt * 100, 1) if cnt else 0
            subject_stats.append({"subject": name, "total": cnt, "wrong": wrong, "accuracy": acc})

        return {
            "overview": {
                "totalHomeworks": total_homeworks,
                "totalProblems": total_problems,
                "averageAccuracy": accuracy,
                "totalCorrect": total_correct,
                "totalWrong": total_wrong,
            },
            "errorPatterns": error_patterns,
            "weakPoints": weak_points,
            "trends": trends,
            "subjects": subject_stats,
            "generatedAt": datetime.now().isoformat(),
        }


async def _get_weekly_trends(session) -> list:
    """按周汇总正确率和题量趋势。"""
    # 取最近 8 周的数据（最多）
    cutoff = datetime.now() - timedelta(weeks=8)

    # 获取每周的数据
    stmt = (
        select(HomeworkRecord)
        .where(HomeworkRecord.created_at >= cutoff)
        .order_by(HomeworkRecord.created_at)
    )
    rows = await session.execute(stmt)
    records = rows.scalars().all()

    # 手动按周汇聚
    weekly = {}  # {week_label: {correct, wrong, total}}
    for r in records:
        week_start = r.created_at - timedelta(days=r.created_at.weekday())
        week_label = week_start.strftime("%m/%d")
        if week_label not in weekly:
            weekly[week_label] = {"correct": 0, "wrong": 0, "not_attempted": 0, "total": 0, "homeworks": 0}
        weekly[week_label]["correct"] += r.correct_count
        weekly[week_label]["wrong"] += r.wrong_count
        weekly[week_label]["not_attempted"] += r.not_attempted_count
        weekly[week_label]["total"] += r.total_count
        weekly[week_label]["homeworks"] += 1

    trends = []
    for label, data in sorted(weekly.items()):
        answered = data["correct"] + data["wrong"]
        acc = round(data["correct"] / answered * 100, 1) if answered else 0
        trends.append({
            "week": label,
            "accuracy": acc,
            "total": data["total"],
            "correct": data["correct"],
            "wrong": data["wrong"],
            "notAttempted": data["not_attempted"],
            "homeworkCount": data["homeworks"],
        })

    return trends


async def _get_subject_trends(session, subject: str) -> list:
    """获取指定学科的周趋势。"""
    cutoff = datetime.now() - timedelta(weeks=8)
    stmt = (
        select(HomeworkRecord)
        .where(HomeworkRecord.created_at >= cutoff, HomeworkRecord.subject == subject)
        .order_by(HomeworkRecord.created_at)
    )
    rows = await session.execute(stmt)
    records = rows.scalars().all()

    weekly = {}
    for r in records:
        week_start = r.created_at - timedelta(days=r.created_at.weekday())
        week_label = week_start.strftime("%m/%d")
        if week_label not in weekly:
            weekly[week_label] = {"correct": 0, "wrong": 0, "total": 0}
        weekly[week_label]["correct"] += r.correct_count
        weekly[week_label]["wrong"] += r.wrong_count
        weekly[week_label]["total"] += r.total_count

    trends = []
    for label, data in sorted(weekly.items()):
        answered = data["correct"] + data["wrong"]
        acc = round(data["correct"] / answered * 100, 1) if answered else 0
        trends.append({"week": label, "accuracy": acc, "total": data["total"], "correct": data["correct"], "wrong": data["wrong"]})

    return trends


def _severity_label(count: int) -> str:
    """根据错误次数判断严重程度。"""
    if count >= 10:
        return "高危"
    elif count >= 5:
        return "中危"
    elif count >= 2:
        return "关注"
    return "轻微"


# ============================================================
# 对外暴露的分析函数
# ============================================================

async def get_full_analysis() -> dict:
    """获取全量分析报告。"""
    return await _run_analysis_queries()


async def get_error_patterns(subject: Optional[str] = None) -> list:
    """获取错误模式分布。"""
    async with async_session() as session:
        conditions = [ProblemRecord.is_correct == 0]
        if subject:
            conditions.append(ProblemRecord.subject == subject)
        stmt = (
            select(ProblemRecord.error_type, func.count(ProblemRecord.id).label("cnt"))
            .where(and_(*conditions))
            .group_by(ProblemRecord.error_type)
            .order_by(desc("cnt"))
        )
        rows = await session.execute(stmt)
        total = sum(r.cnt for r in rows.all()) or 1
        results = []
        for r in rows:
            results.append({
                "type": r.error_type or "未分类",
                "count": r.cnt,
                "percent": round(r.cnt / total * 100, 1),
            })
        return results


async def get_weak_points(subject: Optional[str] = None) -> list:
    """获取薄弱知识点诊断。"""
    data = await _run_analysis_queries()
    weak_points = data["weakPoints"]
    if subject:
        name = SUBJECT_NAMES.get(subject, subject)
        weak_points = [w for w in weak_points if w["point"].startswith(f"[{name}]")]
    return weak_points


async def get_trends(subject: Optional[str] = None) -> list:
    """获取学习趋势。"""
    if subject:
        async with async_session() as session:
            return await _get_subject_trends(session, subject)
    async with async_session() as session:
        return await _get_weekly_trends(session)
