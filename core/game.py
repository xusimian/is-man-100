"""
游戏主循环（平台无关）

包含游戏的所有逻辑：子弹生成、移动、碰撞检测、状态转换。
不包含任何渲染代码，因此可以被 Pygame / iOS / 其他前端复用。
"""
from __future__ import annotations

from typing import List
from .constants import (
    TARGET_SURVIVAL_TIME,
    BULLET_MAX_ON_SCREEN,
)
from .difficulty import bullet_speed_at, spawn_interval_at
from .bullet import Bullet
from .player import Player
from .game_state import GameState


class Game:
    """游戏主控制器（逻辑层）"""

    def __init__(self):
        self.state = GameState.MENU
        self.elapsed_time: float = 0.0
        self.player: Player = Player.at_screen_center()
        self.bullets: List[Bullet] = []
        self._spawn_timer: float = 0.0

    # ==================== 状态转换 ====================

    def start(self) -> None:
        """开始新游戏（从菜单或失败界面）"""
        self.state = GameState.PLAYING
        self.elapsed_time = 0.0
        self.player = Player.at_screen_center()
        self.bullets = []
        self._spawn_timer = 0.0

    def move_player_to(self, x: float, y: float) -> None:
        """玩家拖动飞机（仅在游戏中生效）"""
        if self.state == GameState.PLAYING:
            self.player.move_to(x, y)

    # ==================== 主更新循环 ====================

    def update(self, dt: float) -> None:
        """每帧调用一次，更新游戏状态

        Args:
            dt: 时间步长（秒）
        """
        if self.state != GameState.PLAYING:
            return

        self.elapsed_time += dt

        # 1. 子弹生成
        self._spawn_timer += dt
        spawn_interval = spawn_interval_at(self.elapsed_time)
        while self._spawn_timer >= spawn_interval:
            self._spawn_timer -= spawn_interval
            speed = bullet_speed_at(self.elapsed_time)
            bullet = Bullet.spawn_from_edge(speed=speed)
            self.bullets.append(bullet)

        # 2. 子弹移动
        for bullet in self.bullets:
            bullet.update(dt)

        # 3. 清除出界子弹
        self.bullets = [b for b in self.bullets if not b.is_off_screen(margin=50)]

        # 4. 子弹数量上限保护
        if len(self.bullets) > BULLET_MAX_ON_SCREEN:
            self.bullets = self.bullets[-BULLET_MAX_ON_SCREEN:]

        # 5. 碰撞检测
        for bullet in self.bullets:
            if bullet.collides_with(self.player.x, self.player.y, self.player.hitbox_radius):
                self._game_over()
                return

        # 6. 胜利判定
        if self.elapsed_time >= TARGET_SURVIVAL_TIME:
            self._victory()

    # ==================== 内部方法 ====================

    def _game_over(self) -> None:
        self.state = GameState.GAME_OVER

    def _victory(self) -> None:
        self.state = GameState.VICTORY
        self.elapsed_time = TARGET_SURVIVAL_TIME

    # ==================== 便捷属性 ====================

    @property
    def survival_time(self) -> float:
        """存活时间（秒）"""
        return min(self.elapsed_time, TARGET_SURVIVAL_TIME)

    @property
    def remaining_time(self) -> float:
        """剩余时间（秒）"""
        return max(0.0, TARGET_SURVIVAL_TIME - self.elapsed_time)

    @property
    def progress(self) -> float:
        """游戏进度（0.0 到 1.0）"""
        return min(self.elapsed_time / TARGET_SURVIVAL_TIME, 1.0)