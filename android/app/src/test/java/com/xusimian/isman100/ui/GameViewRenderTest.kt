package com.xusimian.isman100.ui

import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.MotionEvent
import android.view.View
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.annotation.LooperMode

/**
 * 渲染层无头验证 —— 用 Robolectric 的 NATIVE 图形模式真实执行 Canvas 绘制。
 *
 * ⚠️ 必须用 @GraphicsMode(NATIVE)：
 *    默认的 LEGACY 模式不栅格化 Canvas 操作（连 drawColor 出来的都是黑图），
 *    像素级断言会全部误判为「没画出来」。
 *
 * 目的：在没有模拟器/KVM 的机器上验证：
 * - GameView 能正常创建、测量、布局
 * - 各状态渲染不抛异常
 * - 渲染结果确实画出了东西（不是空白画布）
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@LooperMode(LooperMode.Mode.PAUSED)
class GameViewRenderTest {

    private val width = 1080
    private val height = 2340

    private fun makeView(): GameView {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val view = GameView(ctx)
        view.measure(
            View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY)
        )
        view.layout(0, 0, width, height)
        return view
    }

    /** 渲染一帧，返回非背景像素占比 */
    private fun renderFrame(view: View): Double {
        val bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        view.draw(canvas)

        var nonBlack = 0
        var total = 0
        var y = 0
        while (y < height) {
            var x = 0
            while (x < width) {
                val px = bmp.getPixel(x, y)
                val r = (px shr 16) and 0xFF
                val g = (px shr 8) and 0xFF
                val b = px and 0xFF
                if (r + g + b > 30) nonBlack++
                total++
                x += 10
            }
            y += 10
        }
        return if (total == 0) 0.0 else nonBlack.toDouble() / total
    }

    /** 点击屏幕坐标 */
    private fun tap(view: View, x: Float, y: Float) {
        val down = MotionEvent.obtain(0L, 0L, MotionEvent.ACTION_DOWN, x, y, 0)
        val up = MotionEvent.obtain(0L, 10L, MotionEvent.ACTION_UP, x, y, 0)
        view.dispatchTouchEvent(down)
        view.dispatchTouchEvent(up)
        down.recycle()
        up.recycle()
        shadowOf(android.os.Looper.getMainLooper()).idle()
    }

    @Test
    fun `view is created and laid out`() {
        val view = makeView()
        assertTrue("宽度应为正数", view.width > 0)
        assertTrue("高度应为正数", view.height > 0)
    }

    @Test
    fun `menu state renders visible content`() {
        val view = makeView()
        val ratio = renderFrame(view)
        assertTrue("菜单应渲染出内容，非背景像素 > 5%，实际 ${ratio * 100}%", ratio > 0.05)
    }

    @Test
    fun `playing state renders visible content`() {
        val view = makeView()
        // 点击「开始挑战」按钮（底部居中）
        tap(view, width / 2f, height - 62f * (width / 393f))

        val ratio = renderFrame(view)
        assertTrue("游戏画面应渲染出内容，实际 ${ratio * 100}%", ratio > 0.05)
    }

    @Test
    fun `repeated frames do not crash`() {
        val view = makeView()
        repeat(30) {
            renderFrame(view)
            shadowOf(android.os.Looper.getMainLooper()).idle()
        }
    }

    @Test
    fun `touch events across states do not crash`() {
        val view = makeView()
        val actions = listOf(
            MotionEvent.ACTION_DOWN,
            MotionEvent.ACTION_MOVE,
            MotionEvent.ACTION_UP
        )
        for (action in actions) {
            val e = MotionEvent.obtain(0L, 0L, action, width / 2f, height / 2f, 0)
            view.dispatchTouchEvent(e)
            e.recycle()
            renderFrame(view)
        }
    }

    @Test
    fun `dragging in game state does not crash`() {
        val view = makeView()
        tap(view, width / 2f, height - 62f * (width / 393f))

        // 模拟拖拽
        val down = MotionEvent.obtain(0L, 0L, MotionEvent.ACTION_DOWN, 500f, 1200f, 0)
        view.dispatchTouchEvent(down)
        for (i in 0..20) {
            val move = MotionEvent.obtain(0L, 0L, MotionEvent.ACTION_MOVE, 500f + i * 10f, 1200f + i * 5f, 0)
            view.dispatchTouchEvent(move)
            move.recycle()
        }
        val up = MotionEvent.obtain(0L, 0L, MotionEvent.ACTION_UP, 700f, 1300f, 0)
        view.dispatchTouchEvent(up)

        renderFrame(view)
        up.recycle()
        down.recycle()
    }
}
