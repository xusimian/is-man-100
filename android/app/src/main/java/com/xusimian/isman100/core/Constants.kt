package com.xusimian.isman100.core

/**
 * 游戏常量 —— 与 Python 版 core/constants.py 保持一致。
 *
 * 注意：屏幕尺寸在 Android 上是动态的（见 GameContext），
 * 这里保留 393x852 作为「设计基准分辨率」，所有坐标按比例缩放。
 */
object Constants {
    /** 胜利条件：撑过 100 秒 */
    const val TARGET_SURVIVAL_TIME = 100.0

    /** 设计基准分辨率（iPhone 风格竖屏） */
    const val BASE_SCREEN_WIDTH = 393f
    const val BASE_SCREEN_HEIGHT = 852f

    /** 玩家飞机 */
    const val PLAYER_SIZE = 40f
    const val PLAYER_HITBOX_RADIUS = 18f

    /** 子弹 */
    const val BULLET_RADIUS = 8f
    const val BULLET_MAX_ON_SCREEN = 100

    /** 难度参数（对应 core/constants.py，v0.2.0 调整后的值） */
    const val DIFFICULTY_BASE_SPEED = 90.0f
    const val DIFFICULTY_MAX_SPEED = 380.0f
    const val DIFFICULTY_BASE_COUNT = 4f
    const val DIFFICULTY_MAX_COUNT = 10f

    /** 子弹生成角度偏移（±30 度） */
    const val BULLET_DIRECTION_JITTER = 30.0

    /** 终局闪烁阈值（秒） */
    const val LATE_GAME_THRESHOLD = 80.0

    /**
     * 单帧最大时间步长（秒）。
     *
     * Android 上 Activity 切后台再回来，onDraw 的 delta 可能非常大，
     * 一帧推进好几秒会导致子弹瞬间铺屏、直接判死。钳制上限避免误杀。
     *
     * 对应 Python 版修复：MAX_FRAME_DT。
     */
    const val MAX_FRAME_DT = 1.0f / 30.0f
}
