package com.xusimian.isman100.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import com.xusimian.isman100.core.Constants
import com.xusimian.isman100.core.Game
import com.xusimian.isman100.core.GameContext
import com.xusimian.isman100.core.GameState
import com.xusimian.isman100.core.Leaderboard
import com.xusimian.isman100.render.Glow
import com.xusimian.isman100.render.Hud
import com.xusimian.isman100.render.Palette
import com.xusimian.isman100.render.Renderers
import com.xusimian.isman100.render.StarField
import com.xusimian.isman100.render.TextRenderer
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * 主游戏视图 —— 对应 Python 版 mac/ui.py。
 *
 * 职责：
 * - 状态机（menu / playing / gameover / victory / name_input）
 * - 触屏交互（拖拽移动飞机、点击按钮）
 * - 渲染编排
 */
class GameView(context: Context) : View(context) {

    /**
     * 名字输入相关回调 —— 由 Activity 实现。
     *
     * GameView 不直接持有 Activity 引用（避免内存泄漏），
     * 只通过回调请求弹/收软键盘。
     */
    interface NameInputCallback {
        /** 请求显示软键盘 */
        fun onRequestKeyboard()

        /** 请求隐藏软键盘 */
        fun onHideKeyboard()
    }

    /** 名字输入回调（可选） */
    var nameInputCallback: NameInputCallback? = null

    // ==================== 状态 ====================

    private enum class UiState { MENU, PLAYING, GAME_OVER, VICTORY, NAME_INPUT }

    // ==================== 核心对象 ====================

    private lateinit var ctx: GameContext
    private lateinit var game: Game
    private lateinit var leaderboard: Leaderboard
    private lateinit var starfield: StarField
    private lateinit var renderers: Renderers
    private lateinit var hud: Hud
    private lateinit var text: TextRenderer

    private var uiState = UiState.MENU
    private var nameInput = ""
    private var submittedRank: Int? = null
    private var settleState: UiState? = null

    private var dragging = false
    private var time = 0f
    private var shake = 0f
    private var flash = 0f
    private var lastFrameNanos = 0L

    private val particles = Renderers.ParticleSystem()

    // ==================== 字号（按 scale 缩放） ====================

    private var fontDisplay = 0f
    private var fontTitle = 0f
    private var fontBody = 0f
    private var fontCallout = 0f
    private var fontCaption = 0f
    private var fontCountdown = 0f

    private val padS = 8f
    private val padM = 16f
    private val padL = 24f
    private val padXL = 32f
    private val radius = 18f
    private val buttonRadius = 26f

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }

    init {
        isFocusable = true
        isFocusableInTouchMode = true
    }

    // ==================== 尺寸变化 ====================

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (w <= 0 || h <= 0) return

        Glow.clearCache()

        ctx = GameContext(w.toFloat(), h.toFloat())
        game = Game(ctx)
        leaderboard = Leaderboard(context)
        starfield = StarField(w, h)
        renderers = Renderers(ctx)
        hud = Hud(ctx)
        text = TextRenderer(ctx.scale)

        fontDisplay = ctx.s(36f)
        fontTitle = ctx.s(28f)
        fontBody = ctx.s(17f)
        fontCallout = ctx.s(14f)
        fontCaption = ctx.s(11f)
        fontCountdown = ctx.s(46f)

        lastFrameNanos = 0L
    }

    // ==================== 主循环 ====================

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val now = System.nanoTime()
        var dt = if (lastFrameNanos == 0L) 1f / 60f else (now - lastFrameNanos) / 1_000_000_000f
        lastFrameNanos = now

        // ⚠️ dt 上限钳制：
        //   Activity 切后台再回来，delta 可能非常大，
        //   一帧推进好几秒 → 子弹瞬间铺屏、直接判死。
        //   钳制在渲染层做，逻辑层（Game.update）不干预。
        dt = min(dt, Constants.MAX_FRAME_DT)

        time += dt

        // 游戏逻辑
        if (uiState == UiState.PLAYING) {
            game.update(dt)
            when (game.state) {
                GameState.GAME_OVER -> onGameOver()
                GameState.VICTORY -> onVictory()
                else -> {}
            }
        }

        // 粒子与反馈
        particles.update(dt)
        shake = maxOf(0f, shake - dt * 3.0f)
        flash = maxOf(0f, flash - dt * 2.5f)

        // 引擎尾焰粒子
        if (uiState == UiState.PLAYING || uiState == UiState.GAME_OVER || uiState == UiState.VICTORY) {
            spawnEngineTrail(dt)
        }

        render(canvas)

        // 持续重绘（游戏主循环）
        postInvalidateOnAnimation()
    }

    // ==================== 渲染 ====================

    private fun render(canvas: Canvas) {
        starfield.draw(canvas)

        // 屏幕震动
        var shakeX = 0f
        var shakeY = 0f
        if (shake > 0.01f) {
            val mag = shake * 7f * ctx.scale
            shakeX = sin(time * 47.0).toFloat() * mag
            shakeY = cos(time * 53.0).toFloat() * mag
        }

        if (uiState == UiState.MENU) {
            drawMenu(canvas)
        } else {
            drawGame(canvas, shakeX, shakeY)
        }

        // 粒子画在游戏层之上
        particles.draw(canvas)

        when (uiState) {
            UiState.GAME_OVER -> drawGameOverModal(canvas)
            UiState.VICTORY -> drawVictoryModal(canvas)
            UiState.NAME_INPUT -> drawNameInputModal(canvas)
            else -> {}
        }

        // 受击红闪
        if (flash > 0.01f) {
            fillPaint.color = 0xFFFF2828.toInt()
            fillPaint.alpha = (flash * 90).toInt().coerceIn(0, 255)
            canvas.drawRect(0f, 0f, ctx.screenWidth, ctx.screenHeight, fillPaint)
            fillPaint.alpha = 255
        }
    }

    private fun drawGame(canvas: Canvas, shakeX: Float, shakeY: Float) {
        val danger = game.elapsedTime > Constants.LATE_GAME_THRESHOLD
        val frozen = uiState == UiState.GAME_OVER ||
            uiState == UiState.VICTORY ||
            uiState == UiState.NAME_INPUT

        // 子弹
        for (b in game.bullets) {
            renderers.drawBullet(
                canvas,
                b.x + shakeX,
                b.y + shakeY,
                b.vx, b.vy,
                b.radius,
                danger
            )
        }

        // 飞船
        renderers.drawShip(
            canvas,
            game.player.x + shakeX,
            game.player.y + shakeY,
            time,
            if (uiState == UiState.PLAYING) 1.0f else 0.35f,
            uiState == UiState.PLAYING
        )

        // HUD
        hud.draw(
            canvas,
            remaining = game.remainingTime,
            progress = game.progress,
            time = time,
            finished = game.state == GameState.VICTORY,
            dim = frozen,
            text = text
        )
    }

    // ==================== 菜单 ====================

    private fun drawMenu(canvas: Canvas) {
        val cx = ctx.screenWidth / 2f

        // 标题（带柔和辉光）
        val titlePaint = text.paint(fontDisplay, Palette.TEXT_HI, bold = true)
        val title = "是男人就100"
        val tw = text.measure(title, titlePaint)
        Glow.drawRadial(canvas, cx, 150f * ctx.scale, (150f * ctx.scale).toInt(), Palette.CYAN, 42, 3.0f)
        canvas.drawText(title, cx - tw / 2f, (150f + fontDisplay * 0.35f) * ctx.scale, titlePaint)

        // 副标题
        val subPaint = text.paint(fontCallout, Palette.TEXT_MID)
        val sub = "撑过 100 秒 证明自己"
        val sw = text.measure(sub, subPaint)
        canvas.drawText(sub, cx - sw / 2f, (205f * ctx.scale) + fontCallout * 0.4f, subPaint)

        // 悬浮飞船
        val hover = sin(time * 1.6).toFloat() * 6f * ctx.scale
        renderers.drawShip(
            canvas, cx, 330f * ctx.scale + hover,
            time, 1.0f, true
        )

        // 排行榜卡片
        drawLeaderboardCard(canvas, 400f * ctx.scale, 340f * ctx.scale)

        // 开始按钮
        drawButton(
            canvas, "开始挑战",
            cx, ctx.screenHeight - 62f * ctx.scale,
            240f * ctx.scale, 58f * ctx.scale,
            Palette.CYAN, 0xFF040E1C.toInt()
        )
    }

    private fun drawLeaderboardCard(canvas: Canvas, y: Float, height: Float) {
        val s = ctx.scale
        val left = padL * s
        val right = ctx.screenWidth - padL * s
        val rect = RectF(left, y, right, y + height)

        // 面板背景
        fillPaint.color = Palette.PANEL_BG
        canvas.drawRoundRect(rect, radius * s, radius * s, fillPaint)

        // 描边
        strokePaint.color = Palette.PANEL_EDGE
        strokePaint.strokeWidth = 1f * s
        canvas.drawRoundRect(rect, radius * s, radius * s, strokePaint)

        // 标题
        val titlePaint = text.paint(fontBody, Palette.CYAN)
        canvas.drawText("排行榜 · TOP 5", rect.left + padM * s, rect.top + padM * s + fontBody * 0.8f, titlePaint)

        if (leaderboard.size == 0) {
            val emptyPaint = text.paint(fontCallout, Palette.TEXT_DIM)
            val empty = "暂无记录 · 成为第一个挑战者"
            val ew = text.measure(empty, emptyPaint)
            canvas.drawText(empty, rect.centerX() - ew / 2f, rect.centerY(), emptyPaint)
        } else {
            drawLeaderboardEntries(canvas, rect)
        }
    }

    private fun drawLeaderboardEntries(canvas: Canvas, cardRect: RectF) {
        val s = ctx.scale
        val startY = cardRect.top + 60f * s
        val lineHeight = (cardRect.height() - 70f * s) / 5f

        for (idx in 0 until leaderboard.size) {
            val entry = leaderboard[idx]
            val y = startY + idx * lineHeight

            val medalCx = cardRect.left + padM * s + 14f * s
            val medalCy = y + 12f * s
            val medalRadius = 14f * s

            var nameX: Float
            if (idx < 3) {
                val medalColor = when (idx) {
                    0 -> Palette.AMBER
                    1 -> 0xFFC8CDDC.toInt()
                    else -> 0xCD7F32.toInt()
                }
                fillPaint.color = medalColor
                canvas.drawCircle(medalCx, medalCy, medalRadius, fillPaint)
                strokePaint.color = 0xFF505050.toInt()
                strokePaint.strokeWidth = 1f * s
                canvas.drawCircle(medalCx, medalCy, medalRadius, strokePaint)

                val numPaint = text.paint(fontCaption, 0xFF1E1E28.toInt(), bold = true)
                val num = "${idx + 1}"
                val nw = text.measure(num, numPaint)
                canvas.drawText(num, medalCx - nw / 2f, medalCy + fontCaption * 0.35f, numPaint)
                nameX = cardRect.left + 70f * s
            } else {
                val rankPaint = text.paint(fontBody, Palette.TEXT_DIM)
                canvas.drawText("${idx + 1}.", cardRect.left + padM * s, y + 12f * s + fontBody * 0.3f, rankPaint)
                nameX = cardRect.left + 52f * s
            }

            // 名字（最多 10 字符）
            val name = entry.name.take(10)
            val nameColor = if (idx == 0) Palette.AMBER else Palette.TEXT_HI
            val namePaint = text.paint(fontBody, nameColor)
            canvas.drawText(name, nameX, y + 12f * s + fontBody * 0.3f, namePaint)

            // 时间（右对齐）
            val timePaint = text.paint(fontBody, nameColor)
            val timeText = String.format(java.util.Locale.US, "%.1fs", entry.time)
            val tw = text.measure(timeText, timePaint)
            canvas.drawText(timeText, cardRect.right - padM * s - tw, y + 12f * s + fontBody * 0.3f, timePaint)

            // 分隔线
            if (idx < leaderboard.size - 1) {
                strokePaint.color = 0xFF283052.toInt()
                strokePaint.strokeWidth = 1f
                val lineY = y + lineHeight - 4f * s
                canvas.drawLine(
                    cardRect.left + padM * s, lineY,
                    cardRect.right - padM * s, lineY, strokePaint
                )
            }
        }
    }

    // ==================== 弹窗 ====================

    private fun drawModalSheet(canvas: Canvas) {
        fillPaint.color = 0x9B02020C.toInt()
        canvas.drawRect(0f, 0f, ctx.screenWidth, ctx.screenHeight, fillPaint)
    }

    private fun drawGameOverModal(canvas: Canvas) {
        drawModalSheet(canvas)
        val s = ctx.scale
        val cx = ctx.screenWidth / 2f

        // 图标外辉光 + X
        Glow.drawRadial(canvas, cx, 240f * s, (52f * s).toInt(), Palette.CORAL, 55, 2.6f)
        fillPaint.color = Palette.CORAL
        canvas.drawCircle(cx, 240f * s, 36f * s, fillPaint)
        strokePaint.color = Palette.TEXT_HI
        strokePaint.strokeWidth = 4f * s
        canvas.drawLine(cx - 14f * s, 240f * s - 14f * s, cx + 14f * s, 240f * s + 14f * s, strokePaint)
        canvas.drawLine(cx + 14f * s, 240f * s - 14f * s, cx - 14f * s, 240f * s + 14f * s, strokePaint)

        // 标题
        val titlePaint = text.paint(fontTitle, Palette.TEXT_HI, bold = true)
        val title = "挑战失败"
        val tw = text.measure(title, titlePaint)
        canvas.drawText(title, cx - tw / 2f, 320f * s + fontTitle * 0.35f, titlePaint)

        // 生存时间
        val timeText = String.format(java.util.Locale.US, "%.1f 秒", game.survivalTime)
        val timePaint = text.paint(fontCountdown, Palette.CORAL, bold = true)
        val tww = text.measure(timeText, timePaint)
        canvas.drawText(timeText, cx - tww / 2f, 380f * s + fontCountdown * 0.35f, timePaint)

        if (qualifiesForNameInput()) {
            val hintPaint = text.paint(fontBody, Palette.AMBER)
            val hint = "新纪录！输入名字上榜"
            val hw = text.measure(hint, hintPaint)
            canvas.drawText(hint, cx - hw / 2f, 440f * s + fontBody * 0.35f, hintPaint)
            drawInputField(canvas, 470f * s)
        } else if (submittedRank != null) {
            val rankText = "已上榜 · 第 $submittedRank 名"
            val rankPaint = text.paint(fontBody, Palette.AMBER)
            val rw = text.measure(rankText, rankPaint)
            canvas.drawText(rankText, cx - rw / 2f, 440f * s + fontBody * 0.35f, rankPaint)
            drawLeaderboardCard(canvas, 470f * s, 280f * s)
        } else {
            drawLeaderboardCard(canvas, 440f * s, 280f * s)
        }

        drawRetryButton(canvas)
    }

    private fun drawVictoryModal(canvas: Canvas) {
        drawModalSheet(canvas)
        val s = ctx.scale
        val cx = ctx.screenWidth / 2f

        // 五角星
        Glow.drawRadial(canvas, cx, 250f * s, (75f * s).toInt(), Palette.LIME, 55, 2.8f)
        val star = renderers.makeStarPoints(cx, 250f * s, 38f * s, 16f * s, 5)
        val path = Path()
        path.moveTo(star[0], star[1])
        for (i in 1 until star.size / 4) {
            path.lineTo(star[i * 4], star[i * 4 + 1])
        }
        path.close()
        fillPaint.color = Palette.LIME
        canvas.drawPath(path, fillPaint)

        // 标题
        val titlePaint = text.paint(fontTitle, Palette.LIME, bold = true)
        val title = "是男人！"
        val tw = text.measure(title, titlePaint)
        canvas.drawText(title, cx - tw / 2f, 330f * s + fontTitle * 0.35f, titlePaint)

        // 100.0
        val numPaint = text.paint(fontCountdown, Palette.LIME, bold = true)
        val num = "100.0"
        val nw = text.measure(num, numPaint)
        canvas.drawText(num, cx - nw / 2f, 390f * s + fontCountdown * 0.35f, numPaint)

        // 副标题
        val subPaint = text.paint(fontCallout, Palette.TEXT_MID)
        val sub = "完美通关"
        val sw = text.measure(sub, subPaint)
        canvas.drawText(sub, cx - sw / 2f, 428f * s + fontCallout * 0.4f, subPaint)

        if (submittedRank == null) {
            val hintPaint = text.paint(fontBody, Palette.TEXT_HI)
            val hint = "输入名字上榜"
            val hw = text.measure(hint, hintPaint)
            canvas.drawText(hint, cx - hw / 2f, 466f * s + fontBody * 0.35f, hintPaint)
            drawInputField(canvas, 496f * s)
        } else {
            val rankText = "已上榜 · 第 $submittedRank 名"
            val rankPaint = text.paint(fontBody, Palette.AMBER)
            val rw = text.measure(rankText, rankPaint)
            canvas.drawText(rankText, cx - rw / 2f, 466f * s + fontBody * 0.35f, rankPaint)
            drawLeaderboardCard(canvas, 496f * s, 254f * s)
        }

        drawRetryButton(canvas)
    }

    private fun drawInputField(canvas: Canvas, y: Float) {
        val s = ctx.scale
        val boxW = ctx.screenWidth - 2 * padXL * s
        val boxH = 56f * s
        val left = (ctx.screenWidth - boxW) / 2f
        val rect = RectF(left, y, left + boxW, y + boxH)

        fillPaint.color = 0xFF1C2042.toInt()
        canvas.drawRoundRect(rect, 12f * s, 12f * s, fillPaint)
        strokePaint.color = Palette.CYAN
        strokePaint.strokeWidth = 2f * s
        canvas.drawRoundRect(rect, 12f * s, 12f * s, strokePaint)

        val display: String
        val color: Int
        if (nameInput.isNotEmpty()) {
            display = nameInput
            color = Palette.TEXT_HI
        } else {
            display = "点击输入名字..."
            color = Palette.TEXT_DIM
        }
        val tp = text.paint(fontBody, color)
        val tw = text.measure(display, tp)
        canvas.drawText(display, rect.centerX() - tw / 2f, rect.centerY() + fontBody * 0.35f, tp)

        val hintPaint = text.paint(fontCaption, Palette.TEXT_DIM)
        val hint = "点击输入 · 空白处确认"
        val hw = text.measure(hint, hintPaint)
        canvas.drawText(hint, rect.centerX() - hw / 2f, rect.bottom + 18f * s + fontCaption * 0.5f, hintPaint)
    }

    private fun drawNameInputModal(canvas: Canvas) {
        if (game.state == GameState.GAME_OVER) {
            drawGameOverModal(canvas)
        } else {
            drawVictoryModal(canvas)
        }
    }

    private fun drawRetryButton(canvas: Canvas) {
        drawButton(
            canvas, "再来一次",
            ctx.screenWidth / 2f, ctx.screenHeight - 82f * ctx.scale,
            200f * ctx.scale, 52f * ctx.scale,
            Palette.CYAN, 0xFF040E1C.toInt()
        )
    }

    // ==================== 通用组件 ====================

    private fun drawButton(
        canvas: Canvas,
        label: String,
        centerX: Float,
        centerY: Float,
        width: Float,
        height: Float,
        fillColor: Int,
        textColor: Int
    ) {
        val rect = RectF(
            centerX - width / 2f, centerY - height / 2f,
            centerX + width / 2f, centerY + height / 2f
        )

        // 按钮外柔光
        val glowR = (width * 0.42f).toInt()
        Glow.drawRadial(canvas, rect.centerX(), rect.centerY(), glowR, fillColor, 38, 3.0f)

        fillPaint.color = fillColor
        canvas.drawRoundRect(rect, buttonRadius * ctx.scale, buttonRadius * ctx.scale, fillPaint)

        val tp = text.paint(fontBody, textColor)
        val tw = text.measure(label, tp)
        canvas.drawText(label, rect.centerX() - tw / 2f, rect.centerY() + fontBody * 0.35f, tp)
    }

    // ==================== 交互 ====================

    override fun onTouchEvent(event: MotionEvent): Boolean {
        val x = event.x
        val y = event.y

        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                when (uiState) {
                    UiState.NAME_INPUT -> {
                        // 点击输入框聚焦 / 点击别处确认
                        if (hitInputBox(x, y)) {
                            // 保持在输入模式
                        } else {
                            submitName(anonymous = false)
                        }
                    }
                    UiState.PLAYING -> {
                        dragging = true
                        game.movePlayerTo(x, y)
                    }
                    UiState.MENU -> {
                        if (hitStartButton(x, y)) startGame()
                    }
                    UiState.GAME_OVER, UiState.VICTORY -> {
                        if (hitRetryButton(x, y)) {
                            startGame()
                            return true
                        }
                        if (uiState == UiState.GAME_OVER && qualifiesForNameInput() && hitInputBox(x, y)) {
                            enterNameInput()
                            return true
                        }
                    }
                }
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                if (dragging && uiState == UiState.PLAYING) {
                    game.movePlayerTo(x, y)
                }
                return true
            }

            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                dragging = false
                if (event.actionMasked == MotionEvent.ACTION_UP) {
                    performClick()
                }
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    /**
     * 无障碍：供辅助功能服务触发点击。
     */
    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    private fun hitStartButton(x: Float, y: Float): Boolean {
        val s = ctx.scale
        val rect = RectF(
            ctx.screenWidth / 2f - 120f * s, ctx.screenHeight - 62f * s - 29f * s,
            ctx.screenWidth / 2f + 120f * s, ctx.screenHeight - 62f * s + 29f * s
        )
        return rect.contains(x, y)
    }

    private fun hitRetryButton(x: Float, y: Float): Boolean {
        val s = ctx.scale
        val rect = RectF(
            ctx.screenWidth / 2f - 100f * s, ctx.screenHeight - 82f * s - 26f * s,
            ctx.screenWidth / 2f + 100f * s, ctx.screenHeight - 82f * s + 26f * s
        )
        return rect.contains(x, y)
    }

    private fun hitInputBox(x: Float, y: Float): Boolean {
        val s = ctx.scale
        val boxW = ctx.screenWidth - 2 * padXL * s
        val rect = RectF(
            (ctx.screenWidth - boxW) / 2f, 470f * s,
            (ctx.screenWidth + boxW) / 2f, 470f * s + 56f * s
        )
        return rect.contains(x, y)
    }

    // ==================== 状态转换 ====================

    private fun startGame() {
        game.start()
        uiState = UiState.PLAYING
        submittedRank = null
        settleState = null
        particles.clear()
        shake = 0f
        flash = 0f
    }

    private fun enterNameInput() {
        settleState = if (uiState == UiState.GAME_OVER || uiState == UiState.VICTORY) uiState else null
        uiState = UiState.NAME_INPUT
        nameInput = ""
        // 请求 Activity 弹出软键盘
        nameInputCallback?.onRequestKeyboard()
    }

    private fun submitName(anonymous: Boolean) {
        val name = if (anonymous) "匿名" else nameInput.trim().ifEmpty { "匿名" }
        val rank = leaderboard.addEntry(name, game.survivalTime)
        submittedRank = rank

        // ⚠️ 不能用 game.state 判断回到哪个界面：
        //    逻辑层可能仍是 PLAYING，会被错判成 victory。
        //    用「进入名字输入之前所在的结算界面」，兜底绝不把 PLAYING 映射成胜利。
        uiState = when {
            settleState == UiState.GAME_OVER -> UiState.GAME_OVER
            settleState == UiState.VICTORY -> UiState.VICTORY
            game.state == GameState.GAME_OVER -> UiState.GAME_OVER
            game.state == GameState.VICTORY -> UiState.VICTORY
            else -> UiState.PLAYING
        }
        settleState = null
        nameInput = ""
        nameInputCallback?.onHideKeyboard()
    }

    private fun qualifiesForNameInput(): Boolean {
        if (submittedRank != null) return false
        if (game.survivalTime <= 0.0) return false
        return leaderboard.isHighScore(game.survivalTime)
    }

    private fun onGameOver() {
        uiState = UiState.GAME_OVER
        shake = 1f
        flash = 1f
        burstAtPlayer()
    }

    private fun onVictory() {
        uiState = UiState.VICTORY
        burstAtPlayer(
            colors = intArrayOf(Palette.LIME, Palette.AMBER, Palette.CYAN),
            count = 80,
            speed = 420f
        )
    }

    private fun burstAtPlayer(
        colors: IntArray = intArrayOf(Palette.CYAN, Palette.MAGENTA, Palette.VIOLET),
        count: Int = 55,
        speed: Float = 340f
    ) {
        val px = game.player.x
        val py = game.player.y
        repeat(count) {
            val ang = Math.random() * Math.PI * 2
            val spd = (speed * (0.25f + 0.75f * Math.random().toFloat()))
            particles.spawn(
                Renderers.Particle(
                    px, py,
                    (cos(ang) * spd).toFloat(), (sin(ang) * spd).toFloat(),
                    0.4f + 0.7f * Math.random().toFloat(),
                    0.4f + 0.7f * Math.random().toFloat(),
                    colors.random(),
                    2f + 3f * Math.random().toFloat()
                )
            )
        }
    }

    private fun spawnEngineTrail(dt: Float) {
        if (Math.random() > dt * 40.0) return
        val px = game.player.x
        val py = game.player.y
        particles.spawn(
            Renderers.Particle(
                px + (-3f + 6f * Math.random().toFloat()),
                py + 16f * ctx.scale,
                (-12f + 24f * Math.random().toFloat()),
                (40f + 50f * Math.random().toFloat()),
                0.25f + 0.25f * Math.random().toFloat(),
                0.25f + 0.25f * Math.random().toFloat(),
                if (Math.random() > 0.5) Palette.CYAN else Palette.VIOLET,
                1.5f + 1.5f * Math.random().toFloat(),
                drag = 0.9f
            )
        )
    }

    /**
     * 设置名字输入内容（供 Activity 的 IME 回调）。
     *
     * 最多 12 个字符，与 Python 版一致。
     */
    fun setNameInput(text: String) {
        nameInput = text.take(12)
        invalidate()
    }

    /**
     * 提交当前输入的名字（IME 回车）。
     */
    fun submitCurrentName() {
        if (uiState == UiState.NAME_INPUT) {
            submitName(anonymous = false)
        }
    }

    /**
     * 当前是否处于名字输入状态（供 Activity 判断要不要弹键盘）。
     */
    fun isNameInputActive(): Boolean = uiState == UiState.NAME_INPUT
}
