package com.xusimian.isman100.core

/**
 * 游戏主控制器（逻辑层）—— 对应 Python 版 core/game.py。
 *
 * 平台无关，不含任何渲染代码。
 */
class Game(val ctx: GameContext) {

    var state: GameState = GameState.MENU
        private set

    var elapsedTime: Double = 0.0
        private set

    var player: Player = Player.atScreenCenter(ctx)
        private set

    var bullets: MutableList<Bullet> = mutableListOf()
        private set

    private var spawnTimer: Float = 0f

    /** 开始新游戏（从菜单或失败界面） */
    fun start() {
        state = GameState.PLAYING
        elapsedTime = 0.0
        player = Player.atScreenCenter(ctx)
        bullets = mutableListOf()
        spawnTimer = 0f
    }

    /** 玩家拖动飞机（仅在游戏中生效） */
    fun movePlayerTo(x: Float, y: Float) {
        if (state == GameState.PLAYING) {
            player.moveTo(x, y)
        }
    }

    /**
     * 每帧调用一次，更新游戏状态。
     *
     * @param dt 时间步长（秒）
     */
    fun update(dt: Float) {
        if (state != GameState.PLAYING) return

        // ⚠️ dt 下限保护：
        //   负值会让计时器倒退（progress 变负、remainingTime 超过 100）。
        //   上限钳制在渲染层（GameView.onDraw）做，逻辑层不干预。
        val safeDt = maxOf(dt, 0f)

        elapsedTime += safeDt.toDouble()

        // 1. 子弹生成
        spawnTimer += safeDt
        val spawnInterval = Difficulty.spawnIntervalAt(elapsedTime)
        while (spawnTimer >= spawnInterval) {
            spawnTimer -= spawnInterval
            val speed = Difficulty.bulletSpeedAt(elapsedTime)
            bullets.add(Bullet.spawnFromEdge(ctx, speed = speed))
        }

        // 2. 子弹移动
        for (b in bullets) {
            b.update(safeDt)
        }

        // 3. 清除出界子弹
        bullets.removeAll { it.isOffScreen(ctx) }

        // 4. 子弹数量上限保护
        if (bullets.size > Constants.BULLET_MAX_ON_SCREEN) {
            bullets = bullets.takeLast(Constants.BULLET_MAX_ON_SCREEN).toMutableList()
        }

        // 5. 碰撞检测
        for (b in bullets) {
            if (b.collidesWith(player.x, player.y, player.hitboxRadius)) {
                gameOver()
                return
            }
        }

        // 6. 胜利判定
        if (elapsedTime >= Constants.TARGET_SURVIVAL_TIME) {
            victory()
        }
    }

    private fun gameOver() {
        state = GameState.GAME_OVER
    }

    // ==================== 测试辅助 ====================

    /**
     * 仅供单元测试使用：直接设置已流逝时间。
     *
     * 不暴露为公开 API —— 正常玩法中时间只能由 update() 推进。
     */
    internal fun setElapsedTimeForTest(value: Double) {
        elapsedTime = value
    }

    /**
     * 仅供单元测试使用：直接设置状态。
     */
    internal fun setStateForTest(value: GameState) {
        state = value
    }

    private fun victory() {
        state = GameState.VICTORY
        elapsedTime = Constants.TARGET_SURVIVAL_TIME
    }

    /** 存活时间（秒） */
    val survivalTime: Double
        get() = minOf(elapsedTime, Constants.TARGET_SURVIVAL_TIME)

    /** 剩余时间（秒） */
    val remainingTime: Double
        get() = maxOf(0.0, Constants.TARGET_SURVIVAL_TIME - elapsedTime)

    /** 游戏进度（0.0 到 1.0） */
    val progress: Float
        get() = (survivalTime / Constants.TARGET_SURVIVAL_TIME).toFloat().coerceIn(0f, 1f)
}
