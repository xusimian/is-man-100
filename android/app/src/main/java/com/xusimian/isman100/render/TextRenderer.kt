package com.xusimian.isman100.render

import android.graphics.Paint
import android.graphics.Typeface

/**
 * 文本渲染辅助 —— 统一管理字号 / 颜色 / 中文字体。
 *
 * Android 系统自带中文字体，直接用 default 即可，
 * 不需要像 Python 版那样满系统扫描字体文件。
 */
class TextRenderer(baseSize: Float) {

    private val base = baseSize
    private val typeface: Typeface = Typeface.create(
        Typeface.SANS_SERIF,
        Typeface.NORMAL
    )
    private val boldTypeface: Typeface = Typeface.create(
        Typeface.SANS_SERIF,
        Typeface.BOLD
    )

    /** 按基准字号创建 Paint */
    fun paint(size: Float, color: Int, bold: Boolean = false): Paint {
        return Paint(Paint.ANTI_ALIAS_FLAG).apply {
            this.textSize = size
            this.color = color
            this.typeface = if (bold) boldTypeface else typeface
        }
    }

    /** 测量文本宽度 */
    fun measure(text: String, paint: Paint): Float = paint.measureText(text)

    /** 创建居中绘制的 Paint（textAlign = CENTER） */
    fun centeredPaint(size: Float, color: Int, bold: Boolean = false): Paint =
        paint(size, color, bold).apply { textAlign = Paint.Align.CENTER }
}
