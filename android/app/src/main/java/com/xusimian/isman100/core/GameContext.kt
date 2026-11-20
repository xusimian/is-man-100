package com.xusimian.isman100.core

/**
 * 游戏上下文：承载屏幕尺寸与缩放系数。
 *
 * Python 版屏幕尺寸是常量（393x852），Android 上设备尺寸千差万别，
 * 统一用「设计基准 + scale」的方式映射所有坐标。
 */
class GameContext(
    val screenWidth: Float,
    val screenHeight: Float
) {
    /** 统一缩放系数（取宽高比例的较小值，保证不变形） */
    val scale: Float = minOf(
        screenWidth / Constants.BASE_SCREEN_WIDTH,
        screenHeight / Constants.BASE_SCREEN_HEIGHT
    )

    /** 缩放后的玩家视觉尺寸 */
    val playerSize: Float = Constants.PLAYER_SIZE * scale

    /** 缩放后的碰撞半径 */
    val playerHitboxRadius: Float = Constants.PLAYER_HITBOX_RADIUS * scale

    /** 缩放后的子弹半径 */
    val bulletRadius: Float = Constants.BULLET_RADIUS * scale

    /** 缩放后的子弹生成角度偏移（度） */
    val bulletJitter: Double = Constants.BULLET_DIRECTION_JITTER.toDouble()

    /** 缩放后的边界留白（子弹出界判定余量） */
    val offScreenMargin: Float = 50f * scale

    fun s(v: Float): Float = v * scale
    fun s(v: Double): Float = (v * scale).toFloat()
}
