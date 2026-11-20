package com.xusimian.isman100.render

import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import kotlin.math.cos
import kotlin.math.sin

/**
 * 飞船 / 子弹 / 粒子渲染 —— 对应 Python 版 visuals.py 的
 * ShipRenderer / BulletRenderer / ParticleSystem。
 */
class Renderers(private val ctx: com.xusimian.isman100.core.GameContext) {

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }

    // ==================== 飞船 ====================

    /**
     * 绘制玩家飞船（三角箭头 + 护盾环 + 引擎尾焰）。
     *
     * @param engineIntensity 引擎亮度（游戏中 1.0，结算时 0.35）
     * @param shield 是否显示护盾环
     */
    fun drawShip(
        canvas: Canvas,
        cx: Float,
        cy: Float,
        time: Float,
        engineIntensity: Float,
        shield: Boolean
    ) {
        val s = ctx.scale
        val size = ctx.playerSize
        val half = size / 2f

        // 引擎尾焰（向下拖出的锥形光）
        if (engineIntensity > 0.05f) {
            val flameLen = size * (0.5f + 0.25f * sin(time * 18f)) * engineIntensity
            val flamePaint = Paint(Paint.ANTI_ALIAS_FLAG)
            flamePaint.color = Palette.CYAN
            flamePaint.alpha = (110 * engineIntensity).toInt().coerceIn(0, 255)
            val path = Path()
            path.moveTo(cx - half * 0.30f, cy + half * 0.25f)
            path.lineTo(cx + half * 0.30f, cy + half * 0.25f)
            path.lineTo(cx, cy + half * 0.25f + flameLen)
            path.close()
            canvas.drawPath(path, flamePaint)
        }

        // 机体（朝上的三角）
        val body = Path()
        body.moveTo(cx, cy - half * 0.85f)
        body.lineTo(cx + half * 0.62f, cy + half * 0.55f)
        body.lineTo(cx, cy + half * 0.28f)
        body.lineTo(cx - half * 0.62f, cy + half * 0.55f)
        body.close()

        fillPaint.color = Palette.CYAN
        canvas.drawPath(body, fillPaint)

        // 内层高光
        fillPaint.color = Palette.TEXT_HI
        val inner = Path()
        inner.moveTo(cx, cy - half * 0.42f)
        inner.lineTo(cx + half * 0.28f, cy + half * 0.30f)
        inner.lineTo(cx, cy + half * 0.14f)
        inner.lineTo(cx - half * 0.28f, cy + half * 0.30f)
        inner.close()
        canvas.drawPath(inner, fillPaint)

        // 护盾环（脉动）
        if (shield) {
            val pulse = 0.5f + 0.5f * sin(time * 3.4f)
            strokePaint.color = Palette.CYAN
            strokePaint.alpha = (70 + 80 * pulse).toInt().coerceIn(0, 255)
            strokePaint.strokeWidth = 2f * s
            canvas.drawCircle(cx, cy, half * 1.15f, strokePaint)
        }
    }

    // ==================== 子弹 ====================

    /**
     * 绘制一颗子弹（发光能量弹 + 拖尾）。
     *
     * @param danger 是否进入终局（转珊瑚红并闪烁）
     */
    fun drawBullet(
        canvas: Canvas,
        x: Float,
        y: Float,
        vx: Float,
        vy: Float,
        radius: Float,
        danger: Boolean
    ) {
        val s = ctx.scale
        val baseColor = if (danger) Palette.CORAL else Palette.CYAN

        // 拖尾（沿速度反方向）
        val speed = kotlin.math.sqrt(vx * vx + vy * vy)
        if (speed > 1f) {
            val trailLen = radius * 3.2f
            val tx = x - vx / speed * trailLen
            val ty = y - vy / speed * trailLen
            strokePaint.color = baseColor
            strokePaint.alpha = 90
            strokePaint.strokeWidth = radius * 1.1f
            canvas.drawLine(x, y, tx, ty, strokePaint)
        }

        // 外辉光
        Glow.drawRadial(canvas, x, y, (radius * 2.6f).toInt(), baseColor, 120, 2.4f)

        // 弹体
        fillPaint.color = Palette.TEXT_HI
        canvas.drawCircle(x, y, radius, fillPaint)
    }

    // ==================== 粒子系统 ====================

    /** 单个粒子 */
    class Particle(
        var x: Float,
        var y: Float,
        var vx: Float,
        var vy: Float,
        var life: Float,
        val maxLife: Float,
        val color: Int,
        val size: Float,
        val drag: Float = 0.92f
    ) {
        val alive: Boolean get() = life > 0f

        fun update(dt: Float) {
            life -= dt
            x += vx * dt
            y += vy * dt
            val d = drag.toDouble().pow(dt * 60.0)
            vx = (vx * d).toFloat()
            vy = (vy * d).toFloat()
        }
    }

    /**
     * 粒子池 —— 对应 Python 版 ParticleSystem。
     * 上限保护，避免性能抖动。
     */
    class ParticleSystem(val maxParticles: Int = 600) {
        val particles = mutableListOf<Particle>()

        fun spawn(p: Particle) {
            if (particles.size >= maxParticles) {
                particles.removeAt(0)
            }
            particles.add(p)
        }

        fun clear() = particles.clear()

        fun update(dt: Float) {
            for (p in particles) p.update(dt)
            particles.removeAll { !it.alive }
        }

        fun draw(canvas: Canvas) {
            val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
            for (p in particles) {
                val t = if (p.maxLife > 0f) p.life / p.maxLife else 0f
                if (t <= 0.05f) continue
                val rad = maxOf(1, (p.size * (0.35f + 0.65f * t)).toInt())
                // 亮度档位烘焙进 RGB（ADD 混合忽略 alpha）
                val level = (t * 5f).toInt().coerceIn(0, 4)
                val brightness = floatArrayOf(1.0f, 0.7f, 0.45f, 0.25f, 0.12f)[level]
                val glow = Glow.radial(rad, p.color, (255 * brightness).toInt(), 1.6f)
                canvas.drawBitmap(
                    glow,
                    (p.x - rad).toFloat(),
                    (p.y - rad).toFloat(),
                    paint
                )
            }
        }
    }

    // ==================== 五角星 ====================

    /** 生成五角星顶点（对应 Python 版 _make_star_points） */
    fun makeStarPoints(cx: Float, cy: Float, outerR: Float, innerR: Float, points: Int): FloatArray {
        val pts = FloatArray(points * 4)
        for (i in 0 until points * 2) {
            val angle = Math.PI / points * i - Math.PI / 2
            val r = if (i % 2 == 0) outerR else innerR
            pts[i * 4] = cx + (cos(angle) * r).toFloat()
            pts[i * 4 + 1] = cy + (sin(angle) * r).toFloat()
        }
        return pts
    }
}

private fun Double.pow(exp: Double): Double = Math.pow(this, exp)
