"""
子弹类

平台无关的子弹逻辑：位置、方向、移动、出界检测。
"""
import math
import random
from .constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BULLET_RADIUS,
    BULLET_DIRECTION_JITTER,
)


class Bullet:
    """子弹"""

    def __init__(self, x: float, y: float, vx: float, vy: float):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = BULLET_RADIUS
        self.alive = True

    @property
    def position(self) -> tuple:
        return (self.x, self.y)

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    def update(self, dt: float) -> None:
        """按时间步长移动"""
        self.x += self.vx * dt
        self.y += self.vy * dt

    def is_off_screen(self, margin: float = 0) -> bool:
        """检查子弹是否飞出屏幕（带余量）"""
        return (
            self.x < -margin
            or self.x > SCREEN_WIDTH + margin
            or self.y < -margin
            or self.y > SCREEN_HEIGHT + margin
        )

    def collides_with(self, cx: float, cy: float, radius: float) -> bool:
        """检查子弹是否与中心点 (cx, cy)、半径 radius 的圆形碰撞"""
        dx = self.x - cx
        dy = self.y - cy
        sum_r = self.radius + radius
        return (dx * dx + dy * dy) <= (sum_r * sum_r)

    @classmethod
    def spawn_from_edge(
        cls,
        target_x: float = SCREEN_WIDTH / 2,
        target_y: float = SCREEN_HEIGHT / 2,
        speed: float = 100.0,
    ) -> "Bullet":
        """从屏幕四条边之一随机生成，飞向目标点附近

        飞行方向 = 目标方向 + 随机角度偏移（±BULLET_DIRECTION_JITTER 度）
        """
        edge = random.choice(["top", "bottom", "left", "right"])
        if edge == "top":
            x = random.uniform(0, SCREEN_WIDTH)
            y = -BULLET_RADIUS
        elif edge == "bottom":
            x = random.uniform(0, SCREEN_WIDTH)
            y = SCREEN_HEIGHT + BULLET_RADIUS
        elif edge == "left":
            x = -BULLET_RADIUS
            y = random.uniform(0, SCREEN_HEIGHT)
        else:  # right
            x = SCREEN_WIDTH + BULLET_RADIUS
            y = random.uniform(0, SCREEN_HEIGHT)

        # 基础方向：从生成点指向目标
        dx = target_x - x
        dy = target_y - y
        base_angle = math.atan2(dy, dx)

        # 随机角度偏移
        jitter = math.radians(random.uniform(-BULLET_DIRECTION_JITTER, BULLET_DIRECTION_JITTER))
        final_angle = base_angle + jitter

        vx = math.cos(final_angle) * speed
        vy = math.sin(final_angle) * speed

        return cls(x, y, vx, vy)