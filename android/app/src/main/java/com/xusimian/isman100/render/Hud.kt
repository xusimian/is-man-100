package com.xusimian.isman100.render

import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import kotlin.math.sin

/**
 * 游戏内 HUD：倒计时面板 + 进度条 —— 对应 Python 版 visuals.py 的 HUD。
 */
class Hud(private val ctx: com.xusimian.isman100.core.GameContext) {

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
    }

    /**
     * 绘制顶部 HUD 面板。
     *
     * @param finished 已通关 —— 隐藏倒计时，改为显示达成状态
     * @param dim 结算中 —— 整体降低透明度
     */
    fun draw(
        canvas: Canvas,
        remaining: Double,
        progress: Float,
        time: Float,
        finished: Boolean,
        dim: Boolean,
        text: TextRenderer
    ) {
        val s = ctx.scale
        val panelW = 190f * s
        val panelH = 74f * s
        val left = (ctx.screenWidth - panelW) / 2f
        val top = 14f * s
        val rect = RectF(left, top, left + panelW, top + panelH)

        // 面板背景（半透明）
        fillPaint.color = Palette.PANEL_BG
        if (dim) fillPaint.alpha = 110 else fillPaint.alpha = 205
        canvas.drawRoundRect(rect, 14f * s, 14f * s, fillPaint)
        fillPaint.alpha = 255

        // 描边：临近结束转珊瑚红并脉动；通关后转绿
        when {
            finished -> {
                strokePaint.color = Palette.LIME
                strokePaint.alpha = 180
            }
            remaining <= 10.0 -> {
                val pulse = 0.55f + 0.45f * sin(time * 7.0).toFloat()
                strokePaint.color = Palette.CORAL
                strokePaint.alpha = (90 + 150 * pulse).toInt().coerceIn(0, 255)
                val glowR = (panelW * 0.75f).toInt()
                Glow.drawRadial(
                    canvas, rect.centerX(), rect.centerY(), glowR,
                    Palette.CORAL, (40 * pulse).toInt(), 2.6f
                )
            }
            else -> {
                strokePaint.color = Palette.PANEL_EDGE
                strokePaint.alpha = 255
            }
        }
        strokePaint.strokeWidth = 1f * s
        canvas.drawRoundRect(rect, 14f * s, 14f * s, strokePaint)

        // 主数字（通关后显示「达成」，否则显示倒计时）
        val numText: String
        val numColor: Int
        if (finished) {
            numText = "达成 100s"
            numColor = Palette.LIME
        } else {
            numText = String.format("%.1f", remaining)
            numColor = if (remaining <= 10.0) Palette.CORAL else Palette.CYAN
        }
        val numSize = if (finished) 22f * s else 44f * s
        val numPaint = text.paint(numSize, numColor, bold = true)
        val numW = text.measure(numText, numPaint)
        val numX = rect.centerX() - numW / 2f
        val numY = top + 8f * s
        canvas.drawText(numText, numX, numY + numSize, numPaint)

        if (!finished) {
            // 单位「秒」
            val unitPaint = text.paint(14f * s, Palette.TEXT_DIM)
            canvas.drawText("秒", numX + numW + 5f * s, numY + numSize, unitPaint)
        }

        // 进度条
        val barW = panelW - 36f * s
        val barH = 6f * s
        val barLeft = rect.centerX() - barW / 2f
        val barTop = rect.bottom - 18f * s
        val barRect = RectF(barLeft, barTop, barLeft + barW, barTop + barH)

        fillPaint.color = Palette.BG_MID
        canvas.drawRoundRect(barRect, 3f * s, 3f * s, fillPaint)

        val fillW = (barW * progress.coerceIn(0f, 1f))
        if (fillW > 0) {
            val fillRect = RectF(barLeft, barTop, barLeft + fillW, barTop + barH)
            fillPaint.color = when {
                finished -> Palette.LIME
                remaining <= 10.0 -> Palette.CORAL
                else -> Palette.CYAN
            }
            canvas.drawRoundRect(fillRect, 3f * s, 3f * s, fillPaint)

            // 进度条头部辉光
            Glow.drawRadial(
                canvas, fillRect.right, fillRect.centerY(), (9 * s).toInt(),
                fillPaint.color, 140, 2.4f
            )
        }
    }
}
