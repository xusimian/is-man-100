"""
测试难度曲线计算

参考 DESIGN.md §3.2 关键时刻速度表
"""
import unittest
from core.difficulty import (
    bullet_speed_at,
    bullet_spawn_rate_at,
    spawn_interval_at,
    is_late_game,
)


class TestDifficultyCurve(unittest.TestCase):

    def test_speed_at_zero(self):
        """t=0 时应该返回 baseSpeed (90) - v0.2.0 调整"""
        self.assertAlmostEqual(bullet_speed_at(0), 90.0, places=5)

    def test_speed_at_target(self):
        """t=100 时应该返回 maxSpeed (380) - v0.2.0 调整"""
        self.assertAlmostEqual(bullet_speed_at(100), 380.0, places=5)

    def test_speed_at_50(self):
        """t=50 时应该返回 90 + 290*0.25 = 162.5（v0.2.0）"""
        # v(50) = 90 + 290 * (0.5)^2 = 90 + 72.5 = 162.5
        self.assertAlmostEqual(bullet_speed_at(50), 162.5, places=5)

    def test_speed_at_30(self):
        """t=30 时应该返回 90 + 290*0.09 = 116.1（v0.2.0）"""
        self.assertAlmostEqual(bullet_speed_at(30), 116.1, places=5)

    def test_speed_clamped_below_zero(self):
        """负数时间应视为 t=0"""
        self.assertAlmostEqual(bullet_speed_at(-5), 90.0, places=5)

    def test_speed_clamped_above_target(self):
        """超过 100 秒应视为 t=100"""
        self.assertAlmostEqual(bullet_speed_at(150), 380.0, places=5)

    def test_spawn_rate_at_zero(self):
        """t=0 时每秒 4 发 - v0.2.0 调整"""
        self.assertAlmostEqual(bullet_spawn_rate_at(0), 4.0, places=5)

    def test_spawn_rate_at_target(self):
        """t=100 时每秒 10 发 - v0.2.0 调整"""
        self.assertAlmostEqual(bullet_spawn_rate_at(100), 10.0, places=5)

    def test_spawn_rate_at_50(self):
        """t=50 时每秒 7 发（线性中点）"""
        # N(50) = 4 + (10-4)*0.5 = 7
        self.assertAlmostEqual(bullet_spawn_rate_at(50), 7.0, places=5)

    def test_spawn_interval_inverse_of_rate(self):
        """spawn_interval 应该等于 1/rate"""
        for t in [0, 25, 50, 75, 100]:
            rate = bullet_spawn_rate_at(t)
            interval = spawn_interval_at(t)
            self.assertAlmostEqual(interval, 1.0 / rate, places=5)

    def test_is_late_game(self):
        """t >= 80 应进入终局"""
        self.assertFalse(is_late_game(79.9))
        self.assertTrue(is_late_game(80.0))
        self.assertTrue(is_late_game(100.0))


if __name__ == "__main__":
    unittest.main()