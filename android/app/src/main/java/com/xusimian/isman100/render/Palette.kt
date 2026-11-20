package com.xusimian.isman100.render

import android.graphics.Color

/**
 * 深空赛博色板 —— 对应 Python 版 mac/visuals.py 的色板常量。
 */
object Palette {
    // 背景
    val BG_TOP = Color.rgb(12, 10, 32)
    val BG_MID = Color.rgb(18, 16, 52)
    val BG_BOTTOM = Color.rgb(4, 4, 14)
    val NEBULA_A = Color.rgb(58, 32, 120)
    val NEBULA_B = Color.rgb(16, 62, 122)

    // 霓虹主色
    val CYAN = Color.rgb(0, 229, 255)
    val MAGENTA = Color.rgb(255, 45, 170)
    val VIOLET = Color.rgb(150, 90, 255)
    val LIME = Color.rgb(120, 255, 170)
    val AMBER = Color.rgb(255, 180, 40)
    val CORAL = Color.rgb(255, 85, 85)

    // 文字
    val TEXT_HI = Color.rgb(235, 245, 255)
    val TEXT_MID = Color.rgb(150, 165, 200)
    val TEXT_DIM = Color.rgb(95, 108, 140)

    // 面板
    val PANEL_BG = Color.argb(205, 16, 18, 42)
    val PANEL_EDGE = Color.argb(120, 90, 130, 190)
}
