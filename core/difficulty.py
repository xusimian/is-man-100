"""
难度曲线计算

根据当前游戏时间 t（秒），返回子弹速度和生成频率。
参考 DESIGN.md §3 二次曲线公式。
"""
from .constants import (
    DIFFICULTY_BASE_SPEED,
    DIFFICULTY_MAX_SPEED,
    DIFFICULTY_BASE_COUNT,
    DIFFICULTY_MAX_COUNT,
    TARGET_SURVIVAL_TIME,
)


def bullet_speed_at(elapsed_time: float) -> float:
    """返回 t 时刻的子弹速度（pt/s）

    二次曲线：v(t) = base + (max - base) * (t/100)^2
    """
    t = max(0.0, min(elapsed_time, TARGET_SURVIVAL_TIME))
    progress = t / TARGET_SURVIVAL_TIME
    return DIFFICULTY_BASE_SPEED + (DIFFICULTY_MAX_SPEED - DIFFICULTY_BASE_SPEED) * (progress ** 2)


def bullet_spawn_rate_at(elapsed_time: float) -> float:
    """返回 t 时刻的每秒子弹生成数

    线性：N(t) = base + (max - base) * (t/100)
    """
    t = max(0.0, min(elapsed_time, TARGET_SURVIVAL_TIME))
    progress = t / TARGET_SURVIVAL_TIME
    return DIFFICULTY_BASE_COUNT + (DIFFICULTY_MAX_COUNT - DIFFICULTY_BASE_COUNT) * progress


def spawn_interval_at(elapsed_time: float) -> float:
    """返回两次生成之间的间隔（秒）

    spawn_interval = 1 / spawn_rate
    """
    rate = bullet_spawn_rate_at(elapsed_time)
    return 1.0 / rate if rate > 0 else 1.0


def is_late_game(elapsed_time: float) -> bool:
    """是否进入终局阶段（用于触发闪烁等效果）"""
    from .constants import LATE_GAME_THRESHOLD
    return elapsed_time >= LATE_GAME_THRESHOLD