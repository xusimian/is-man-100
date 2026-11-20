package com.xusimian.isman100.render

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PorterDuff
import android.graphics.PorterDuffXfermode
import kotlin.random.Random

/**
 * 缓存式深空背景 —— 对应 Python 版 visuals.py 的 StarField。
 *
 * 一次性生成渐变 + 星点 + 星云光晕，之后每帧只 blit 一次。
 * 星点分三层（远/中/近），带不同亮度，制造视差感。
 */
class StarField(
    private val width: Int,
    private val height: Int,
    private val seed: Int = 20261119
) {
    private var surface: Bitmap? = null

    /** 构建背景（首次调用或尺寸变化时重建） */
    fun build(): Bitmap {
        surface?.let { if (it.width == width && it.height == height) return it }

        val rng = Random(seed)
        val bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)

        // 1. 垂直渐变
        canvas.drawBitmap(
            Glow.verticalGradient(width, height, Palette.BG_TOP, Palette.BG_MID, Palette.BG_BOTTOM),
            0f, 0f, null
        )

        // 2. 星云光晕（大块柔和色斑，制造纵深）
        //    ⚠️ 必须用不带 alpha 的 RGB 衰减贴图 + ADD 混合
        val nebulaPaint = Paint(Paint.FILTER_BITMAP_FLAG)
        nebulaPaint.xfermode = PorterDuffXfermode(PorterDuff.Mode.ADD)
        repeat(5) {
            val cx = rng.nextInt(-40, width + 40)
            val cy = rng.nextInt(0, height)
            val rad = rng.nextInt(160, 300)
            val tint = if (rng.nextBoolean()) Palette.NEBULA_A else Palette.NEBULA_B
            val glow = Glow.radial(rad, tint, 46, 2.6f)
            canvas.drawBitmap(glow, (cx - rad).toFloat(), (cy - rad).toFloat(), nebulaPaint)
        }

        // 3. 星点三层
        val starPaint = Paint(Paint.ANTI_ALIAS_FLAG)
        val layers = arrayOf(
            Triple(420, 0..1, 60..115),
            Triple(150, 1..2, 110..180),
            Triple(46, 1..3, 190..255)
        )
        for ((count, radii, brightnesses) in layers) {
            repeat(count) {
                val x = rng.nextInt(0, width)
                val y = rng.nextInt(0, height)
                val rad = rng.nextInt(radii.first, radii.last + 1)
                val brightness = rng.nextInt(brightnesses.first, brightnesses.last + 1)
                val tint = when (rng.nextInt(3)) {
                    0 -> COLOR_WHITE
                    1 -> COLOR_BLUE_WHITE
                    else -> COLOR_PINK_WHITE
                }
                starPaint.color = Color.argb(brightness, Color.red(tint), Color.green(tint), Color.blue(tint))
                canvas.drawCircle(x.toFloat(), y.toFloat(), rad.toFloat(), starPaint)
            }
        }

        surface = bmp
        return bmp
    }

    /** 绘制背景到画布 */
    fun draw(canvas: Canvas) {
        val bmp = build()
        canvas.drawBitmap(bmp, 0f, 0f, null)
    }

    companion object {
        private const val COLOR_WHITE = 0xFFFFFF
        private const val COLOR_BLUE_WHITE = 0xBEDCFF
        private const val COLOR_PINK_WHITE = 0xFFD2F0
    }
}
