package com.xusimian.isman100.render

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.graphics.Bitmap
import kotlin.math.max
import kotlin.random.Random

/**
 * 辉光贴图工具 —— 对应 Python 版 visuals.py 的 make_radial_glow。
 *
 * ⚠️ 关键点（与 Python 版一致）：
 *   Canvas 的 PorterDuff ADD / Screen 混合会忽略 alpha 通道，
 *   所以辉光贴图必须是「不带 alpha 的 RGB 衰减图」，
 *   亮度直接烘焙进 RGB 值里 —— 不能用带 alpha 的 SRCALPHA 贴图，
 *   否则整张方形区域（含透明像素）都会以满强度叠加上去，
 *   表现为满屏彩色方块。
 */
object Glow {

    /** 预渲染缓存：key = (radius, color, alpha) */
    private val cache = HashMap<String, Bitmap>()

    /**
     * 生成一个径向渐变辉光贴图（无 alpha 通道，亮度衰减烘焙进 RGB）。
     *
     * @param radius 半径（px）
     * @param color 中心颜色
     * @param innerAlpha 中心亮度（0-255）
     * @param falloff 衰减指数，越大越集中
     */
    fun radial(radius: Int, color: Int, innerAlpha: Int, falloff: Float = 2.6f): Bitmap {
        val r = max(1, radius)
        val key = "${r}_${color}_${innerAlpha}_${falloff}"
        cache[key]?.let { return it }

        val bmp = Bitmap.createBitmap(r * 2, r * 2, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)

        val r8 = color and 0x00FFFFFF
        val center = (r8 shl 24) or (innerAlpha.coerceIn(0, 255))
        val transparent = (r8 shl 24)

        val shader = RadialGradient(
            r.toFloat(), r.toFloat(), r.toFloat(),
            intArrayOf(center, center, transparent),
            floatArrayOf(0f, 0.25f, 1f),
            Shader.TileMode.CLAMP
        )
        paint.shader = shader
        canvas.drawCircle(r.toFloat(), r.toFloat(), r.toFloat(), paint)

        cache[key] = bmp
        return bmp
    }

    /** 以加法混合方式绘制辉光（居中于 cx, cy） */
    fun drawRadial(
        canvas: Canvas,
        cx: Float,
        cy: Float,
        radius: Int,
        color: Int,
        innerAlpha: Int,
        falloff: Float = 2.6f
    ) {
        val bmp = radial(radius, color, innerAlpha, falloff)
        val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
        paint.xfermode = android.graphics.PorterDuffXfermode(android.graphics.PorterDuff.Mode.ADD)
        canvas.drawBitmap(
            bmp,
            cx - radius,
            cy - radius,
            paint
        )
        paint.xfermode = null
    }

    /** 垂直渐变背景（对应 Python 版的 lerp_color 三段渐变） */
    fun verticalGradient(
        width: Int,
        height: Int,
        top: Int,
        mid: Int,
        bottom: Int
    ): Bitmap {
        val key = "grad_${width}_${height}_${top}_${mid}_${bottom}"
        cache[key]?.let { return it }

        val bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        val paint = Paint()
        paint.shader = LinearGradient(
            0f, 0f, 0f, height.toFloat(),
            intArrayOf(top, mid, bottom),
            floatArrayOf(0f, 0.5f, 1f),
            Shader.TileMode.CLAMP
        )
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), paint)

        cache[key] = bmp
        return bmp
    }

    /** 清空缓存（横竖屏切换时调用，避免持有旧尺寸的 Bitmap） */
    fun clearCache() {
        cache.clear()
    }
}
