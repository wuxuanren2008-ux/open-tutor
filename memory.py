"""间隔复习记忆（SM-2 简化版）。对应 Sia 的 tutor_memory。

quality: 0-5，>=3 视为答对。答对按 1→3→7→16→35→60 天推进，答错回到起点。
"""
from datetime import datetime, timedelta

INTERVALS = [1, 3, 7, 16, 35, 60]


def next_schedule(reps, quality):
    """返回 (新reps, 间隔天数)。"""
    if quality < 3:
        return 0, 0
    new_reps = reps + 1
    idx = min(new_reps - 1, len(INTERVALS) - 1)
    return new_reps, INTERVALS[idx]


def due_date(interval_days, now=None):
    now = now or datetime.now()
    return (now + timedelta(days=interval_days)).strftime("%Y-%m-%d %H:%M:%S")


def is_due(due_at, now=None):
    if not due_at:
        return True
    now = now or datetime.now()
    try:
        return datetime.strptime(due_at, "%Y-%m-%d %H:%M:%S") <= now
    except ValueError:
        return True
