package com.xusimian.isman100.core

/**
 * 玩家飞机 —— 对应 Python 版 core/player.py。
 */
class Player(
    var x: Float,
    var y: Float,
    val ctx: GameContext
) {
    val size: Float get() = ctx.playerSize
    val hitboxRadius: Float get() = ctx.playerHitboxRadius

    /** 移动飞机到指定位置，并限制在屏幕内 */
    fun moveTo(x: Float, y: Float) {
        this.x = clamp(x, size / 2f, ctx.screenWidth - size / 2f)
        this.y = clamp(y, size / 2f, ctx.screenHeight - size / 2f)
    }

    companion object {
        private fun clamp(value: Float, minVal: Float, maxVal: Float): Float =
            maxOf(minVal, minOf(value, maxVal))

        /** 创建位于屏幕中心的飞机 */
        fun atScreenCenter(ctx: GameContext): Player =
            Player(ctx.screenWidth / 2f, ctx.screenHeight / 2f, ctx)
    }
}
