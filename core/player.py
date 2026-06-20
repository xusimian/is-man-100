"""
飞机类（玩家）

平台无关的飞机逻辑：位置、边界限制、碰撞 hitbox。
"""
import math
from .constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYER_HITBOX_RADIUS,
    PLAYER_SIZE,
)


class Player:
    """玩家飞机"""

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        self.size = PLAYER_SIZE
        self.hitbox_radius = PLAYER_HITBOX_RADIUS

    @property
    def position(self) -> tuple:
        return (self.x, self.y)

    def move_to(self, x: float, y: float) -> None:
        """移动飞机到指定位置，并限制在屏幕内"""
        self.x = self._clamp(x, self.size / 2, SCREEN_WIDTH - self.size / 2)
        self.y = self._clamp(y, self.size / 2, SCREEN_HEIGHT - self.size / 2)

    def collides_with_point(self, px: float, py: float) -> bool:
        """检查飞机的圆形 hitbox 是否包含点 (px, py)"""
        dx = px - self.x
        dy = py - self.y
        return (dx * dx + dy * dy) <= (self.hitbox_radius * self.hitbox_radius)

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(value, max_val))

    @classmethod
    def at_screen_center(cls) -> "Player":
        """创建位于屏幕中心的飞机"""
        return cls(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)