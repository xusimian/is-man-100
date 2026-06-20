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
        """t=0 时应该返回 baseSpeed (60)"""
        self.assertAlmostEqual(bullet_speed_at(0), 60.0, places=5)

    def test_speed_at_target(self):
        """t=100 时应该返回 maxSpeed (320)"""
        self.assertAlmostEqual(bullet_speed_at(100), 320.0, places=5)

    def test_speed_at_50(self):
        """t=50 时应该返回 110（验证二次曲线关键点）"""
        # v(50) = 60 + 260 * (0.5)^2 = 60 + 65 = 125
        self.assertAlmostEqual(bullet_speed_at(50), 125.0, places=5)

    def test_speed_at_30(self):
        """t=30 时应该返回 60 + 260*0.09 = 83.4"""
        self.assertAlmostEqual(bullet_speed_at(30), 83.4, places=5)

    def test_speed_clamped_below_zero(self):
        """负数时间应视为 t=0"""
        self.assertAlmostEqual(bullet_speed_at(-5), 60.0, places=5)

    def test_speed_clamped_above_target(self):
        """超过 100 秒应视为 t=100"""
        self.assertAlmostEqual(bullet_speed_at(150), 320.0, places=5)

    def test_spawn_rate_at_zero(self):
        """t=0 时每秒 2 发"""
        self.assertAlmostEqual(bullet_spawn_rate_at(0), 2.0, places=5)

    def test_spawn_rate_at_target(self):
        """t=100 时每秒 8 发"""
        self.assertAlmostEqual(bullet_spawn_rate_at(100), 8.0, places=5)

    def test_spawn_rate_at_50(self):
        """t=50 时每秒 5 发（线性中点）"""
        self.assertAlmostEqual(bullet_spawn_rate_at(50), 5.0, places=5)

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