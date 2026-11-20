package com.xusimian.isman100.core

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * 子弹 —— 对应 Python 版 core/bullet.py。
 *
 * 坐标使用「设计基准坐标 + scale」的思路：内部按屏幕实际像素存储，
 * 生成时用 ctx 做缩放。
 */
class Bullet(
    var x: Float,
    var y: Float,
    var vx: Float,
    var vy: Float,
    val radius: Float
) {
    val speed: Float
        get() = sqrt(vx * vx + vy * vy)

    /** 按时间步长移动 */
    fun update(dt: Float) {
        x += vx * dt
        y += vy * dt
    }

    /** 检查是否飞出屏幕（带余量） */
    fun isOffScreen(ctx: GameContext): Boolean =
        x < -ctx.offScreenMargin ||
            x > ctx.screenWidth + ctx.offScreenMargin ||
            y < -ctx.offScreenMargin ||
            y > ctx.screenHeight + ctx.offScreenMargin

    /** 检查是否与中心点 (cx, cy)、半径 radius 的圆形碰撞 */
    fun collidesWith(cx: Float, cy: Float, radius: Float): Boolean {
        val dx = x - cx
        val dy = y - cy
        val sumR = this.radius + radius
        return dx * dx + dy * dy <= sumR * sumR
    }

    companion object {
        /**
         * 从屏幕四条边之一随机生成，飞向目标点附近。
         *
         * 飞行方向 = 目标方向 + 随机角度偏移（±jitter 度）。
         *
         * 与 Python 版一致：默认目标是屏幕中心。
         */
        fun spawnFromEdge(
            ctx: GameContext,
            targetX: Float = ctx.screenWidth / 2f,
            targetY: Float = ctx.screenHeight / 2f,
            speed: Float
        ): Bullet {
            val r = ctx.bulletRadius
            val edge = EDGES.random()
            val x: Float
            val y: Float
            when (edge) {
                0 -> { x = (0..ctx.screenWidth.toInt()).random().toFloat(); y = -r }
                1 -> { x = (0..ctx.screenWidth.toInt()).random().toFloat(); y = ctx.screenHeight + r }
                2 -> { x = -r; y = (0..ctx.screenHeight.toInt()).random().toFloat() }
                else -> { x = ctx.screenWidth + r; y = (0..ctx.screenHeight.toInt()).random().toFloat() }
            }

            // 基础方向：从生成点指向目标
            val baseAngle = atan2((targetY - y).toDouble(), (targetX - x).toDouble())

            // 随机角度偏移
            val jitterRad = Math.toRadians(
                -ctx.bulletJitter + Math.random() * (2 * ctx.bulletJitter)
            )
            val finalAngle = baseAngle + jitterRad

            val vx = (cos(finalAngle) * speed).toFloat()
            val vy = (sin(finalAngle) * speed).toFloat()

            return Bullet(x, y, vx, vy, r)
        }

        private val EDGES = intArrayOf(0, 1, 2, 3)
    }
}
