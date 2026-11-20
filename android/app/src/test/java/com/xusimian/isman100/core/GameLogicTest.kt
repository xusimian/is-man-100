package com.xusimian.isman100.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/**
 * 逻辑层单元测试 —— 与 Python 版 tests/ 对齐。
 *
 * 目的：确保 Kotlin 移植后的游戏逻辑与 Python 原版行为一致，
 * 避免两端玩法出现偏差。
 */
class GameLogicTest {

    private fun ctx(w: Float = 393f, h: Float = 852f) = GameContext(w, h)

    // ==================== 难度曲线 ====================

    @Test
    fun `bullet speed at zero is base speed`() {
        assertEquals(90.0f, Difficulty.bulletSpeedAt(0.0), 0.001f)
    }

    @Test
    fun `bullet speed at target is max speed`() {
        assertEquals(380.0f, Difficulty.bulletSpeedAt(100.0), 0.001f)
    }

    @Test
    fun `bullet speed at 50 follows quadratic curve`() {
        // 90 + (380-90) * 0.25 = 162.5
        assertEquals(162.5f, Difficulty.bulletSpeedAt(50.0), 0.001f)
    }

    @Test
    fun `bullet speed is clamped above target`() {
        assertEquals(380.0f, Difficulty.bulletSpeedAt(150.0), 0.001f)
    }

    @Test
    fun `bullet speed is clamped below zero`() {
        assertEquals(90.0f, Difficulty.bulletSpeedAt(-10.0), 0.001f)
    }

    @Test
    fun `spawn rate at zero is base count`() {
        assertEquals(4.0f, Difficulty.bulletSpawnRateAt(0.0), 0.001f)
    }

    @Test
    fun `spawn rate at target is max count`() {
        assertEquals(10.0f, Difficulty.bulletSpawnRateAt(100.0), 0.001f)
    }

    @Test
    fun `spawn rate at 50 is linear midpoint`() {
        assertEquals(7.0f, Difficulty.bulletSpawnRateAt(50.0), 0.001f)
    }

    @Test
    fun `spawn interval is inverse of rate`() {
        val rate = Difficulty.bulletSpawnRateAt(50.0)
        assertEquals(1.0f / rate, Difficulty.spawnIntervalAt(50.0), 0.0001f)
    }

    @Test
    fun `late game threshold is 80 seconds`() {
        assertFalse(Difficulty.isLateGame(79.9))
        assertTrue(Difficulty.isLateGame(80.0))
    }

    // ==================== 游戏状态 ====================

    @Test
    fun `initial state is menu`() {
        val game = Game(ctx())
        assertEquals(GameState.MENU, game.state)
        assertEquals(0.0, game.elapsedTime, 0.0)
    }

    @Test
    fun `start transitions to playing and centers player`() {
        val c = ctx()
        val game = Game(c)
        game.start()
        assertEquals(GameState.PLAYING, game.state)
        assertEquals(c.screenWidth / 2f, game.player.x, 0.001f)
        assertEquals(c.screenHeight / 2f, game.player.y, 0.001f)
    }

    @Test
    fun `update in menu state does nothing`() {
        val game = Game(ctx())
        game.update(1.0f)
        assertEquals(GameState.MENU, game.state)
        assertEquals(0.0, game.elapsedTime, 0.0)
    }

    @Test
    fun `update increments elapsed time`() {
        val game = Game(ctx())
        game.start()
        game.update(0.5f)
        assertEquals(0.5, game.elapsedTime, 0.0001)
        game.update(0.3f)
        assertEquals(0.8, game.elapsedTime, 0.0001)
    }

    @Test
    fun `bullets spawn over time`() {
        val game = Game(ctx())
        game.start()
        repeat(50) { game.update(0.1f) }
        assertTrue(game.bullets.isNotEmpty())
    }

    @Test
    fun `victory at 100 seconds`() {
        val game = Game(ctx())
        game.start()
        game.setElapsedTimeForTest(99.95)
        game.update(0.1f)
        assertEquals(GameState.VICTORY, game.state)
    }

    @Test
    fun `victory locks elapsed time at target`() {
        val game = Game(ctx())
        game.start()
        game.setElapsedTimeForTest(99.95)
        game.update(0.1f)
        game.update(1.0f)
        assertEquals(100.0, game.elapsedTime, 0.0001)
        assertEquals(0.0, game.remainingTime, 0.0001)
        assertEquals(1.0f, game.progress, 0.0001f)
    }

    /**
     * 回归测试：负 dt 不应让计时器倒退
     * （对应 Python 版 core/game.py 的修复）
     */
    @Test
    fun `negative dt does not rewind timer`() {
        val game = Game(ctx())
        game.start()
        game.update(-5.0f)
        assertEquals(0.0, game.elapsedTime, 0.0)
        assertEquals(0.0f, game.progress, 0.0f)
        assertEquals(100.0, game.remainingTime, 0.0001)
    }

    /**
     * 逻辑层应忠实执行传入的时间步（不钳制上限）——
     * 单帧卡顿的钳制在渲染层（GameView.onDraw）做。
     */
    @Test
    fun `logic layer executes large dt verbatim`() {
        val game = Game(ctx())
        game.start()
        game.update(0.5f)
        assertEquals(0.5, game.elapsedTime, 0.0001)
    }

    @Test
    fun `bullet count respects max on screen`() {
        val game = Game(ctx())
        game.start()
        repeat(2000) { game.update(1f / 30f) }
        assertTrue(game.bullets.size <= Constants.BULLET_MAX_ON_SCREEN)
    }

    // ==================== 玩家 ====================

    @Test
    fun `player is initialized at position`() {
        val c = ctx()
        val p = Player(100f, 200f, c)
        assertEquals(100f, p.x, 0.001f)
        assertEquals(200f, p.y, 0.001f)
    }

    @Test
    fun `player clamps to screen bounds`() {
        val c = ctx()
        val p = Player.atScreenCenter(c)
        p.moveTo(-9999f, -9999f)
        assertEquals(c.playerSize / 2f, p.x, 0.001f)
        assertEquals(c.playerSize / 2f, p.y, 0.001f)

        p.moveTo(99999f, 99999f)
        assertEquals(c.screenWidth - c.playerSize / 2f, p.x, 0.001f)
        assertEquals(c.screenHeight - c.playerSize / 2f, p.y, 0.001f)
    }

    @Test
    fun `player moves only while playing`() {
        val game = Game(ctx())
        game.start()
        val before = game.player.x
        game.movePlayerTo(50f, 50f)
        assertTrue(abs(game.player.x - before) > 0.001f)

        // 非 PLAYING 状态不应移动
        game.setStateForTest(GameState.MENU)
        val x = game.player.x
        game.movePlayerTo(10f, 10f)
        assertEquals(x, game.player.x, 0.001f)
    }

    // ==================== 子弹 ====================

    @Test
    fun `bullet moves`() {
        val b = Bullet(100f, 100f, 50f, 0f, 8f)
        b.update(1.0f)
        assertEquals(150f, b.x, 0.001f)
        assertEquals(100f, b.y, 0.001f)
    }

    @Test
    fun `bullet off screen detection`() {
        val c = ctx()
        val b = Bullet(-100f, 100f, 0f, 0f, c.bulletRadius)
        assertTrue(b.isOffScreen(c))

        val b2 = Bullet(c.screenWidth / 2f, c.screenHeight / 2f, 0f, 0f, c.bulletRadius)
        assertFalse(b2.isOffScreen(c))
    }

    @Test
    fun `bullet spawns from an edge`() {
        val c = ctx()
        repeat(50) {
            val b = Bullet.spawnFromEdge(c, speed = 100f)
            val onEdge =
                b.x < 50f * c.scale ||
                    b.x > c.screenWidth - 50f * c.scale ||
                    b.y < 50f * c.scale ||
                    b.y > c.screenHeight - 50f * c.scale
            assertTrue("子弹应在屏幕边缘生成", onEdge)
        }
    }

    @Test
    fun `bullet collision detection`() {
        val b = Bullet(100f, 100f, 0f, 0f, 8f)
        assertTrue(b.collidesWith(100f, 100f, 18f))
        assertFalse(b.collidesWith(200f, 200f, 18f))
    }

    @Test
    fun `bullet speed property`() {
        val b = Bullet(0f, 0f, 3f, 4f, 8f)
        assertEquals(5.0f, b.speed, 0.001f)
    }

    // ==================== 缩放 ====================

    @Test
    fun `context scales relative to base resolution`() {
        val c = GameContext(786f, 1704f) // 2x
        assertEquals(2.0f, c.scale, 0.001f)
        assertEquals(80f, c.playerSize, 0.001f)
        assertEquals(36f, c.playerHitboxRadius, 0.001f)
        assertEquals(16f, c.bulletRadius, 0.001f)
    }

    @Test
    fun `context on base resolution has scale 1`() {
        val c = GameContext(393f, 852f)
        assertEquals(1.0f, c.scale, 0.001f)
    }
}
