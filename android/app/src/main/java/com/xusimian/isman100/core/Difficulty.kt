package com.xusimian.isman100.core

import kotlin.math.pow
import kotlin.math.min
import kotlin.math.max

/**
 * 难度曲线计算 —— 对应 Python 版 core/difficulty.py。
 *
 * 速度：二次曲线 v(t) = base + (max - base) * (t/100)^2
 * 生成率：线性     N(t) = base + (max - base) * (t/100)
 */
object Difficulty {

    /** t 时刻的子弹速度（pt/s） */
    fun bulletSpeedAt(elapsedTime: Double): Float {
        val t = max(0.0, min(elapsedTime, Constants.TARGET_SURVIVAL_TIME))
        val progress = (t / Constants.TARGET_SURVIVAL_TIME).toFloat()
        return Constants.DIFFICULTY_BASE_SPEED +
            (Constants.DIFFICULTY_MAX_SPEED - Constants.DIFFICULTY_BASE_SPEED) * progress.pow(2)
    }

    /** t 时刻的每秒子弹生成数 */
    fun bulletSpawnRateAt(elapsedTime: Double): Float {
        val t = max(0.0, min(elapsedTime, Constants.TARGET_SURVIVAL_TIME))
        val progress = (t / Constants.TARGET_SURVIVAL_TIME).toFloat()
        return Constants.DIFFICULTY_BASE_COUNT +
            (Constants.DIFFICULTY_MAX_COUNT - Constants.DIFFICULTY_BASE_COUNT) * progress
    }

    /** 两次生成之间的间隔（秒） */
    fun spawnIntervalAt(elapsedTime: Double): Float {
        val rate = bulletSpawnRateAt(elapsedTime)
        return if (rate > 0f) 1.0f / rate else 1.0f
    }

    /** 是否进入终局阶段（用于触发闪烁等效果） */
    fun isLateGame(elapsedTime: Double): Boolean = elapsedTime >= Constants.LATE_GAME_THRESHOLD
}
