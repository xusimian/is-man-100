"""
测试游戏主循环和状态转换
"""
import unittest
from core.game import Game
from core.game_state import GameState
from core.player import Player
from core.bullet import Bullet
from core.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BULLET_MAX_ON_SCREEN,
)


class TestGameState(unittest.TestCase):

    def test_initial_state_is_menu(self):
        """新游戏初始应该是菜单状态"""
        game = Game()
        self.assertEqual(game.state, GameState.MENU)

    def test_start_transitions_to_playing(self):
        """start() 后应该是 playing 状态"""
        game = Game()
        game.start()
        self.assertEqual(game.state, GameState.PLAYING)

    def test_player_at_center_after_start(self):
        """游戏开始后飞机应在屏幕中心"""
        game = Game()
        game.start()
        self.assertAlmostEqual(game.player.x, SCREEN_WIDTH / 2)
        self.assertAlmostEqual(game.player.y, SCREEN_HEIGHT / 2)


class TestGameUpdate(unittest.TestCase):

    def test_update_in_menu_state_does_nothing(self):
        """菜单状态下 update 不改变任何东西"""
        game = Game()
        game.update(1.0)
        self.assertEqual(game.state, GameState.MENU)
        self.assertEqual(game.elapsed_time, 0.0)

    def test_update_increments_elapsed_time(self):
        """游戏中 update 应该累加时间"""
        game = Game()
        game.start()
        game.update(0.5)
        self.assertAlmostEqual(game.elapsed_time, 0.5)
        game.update(0.3)
        self.assertAlmostEqual(game.elapsed_time, 0.8)

    def test_spawns_bullets_over_time(self):
        """长时间不更新应该生成子弹"""
        game = Game()
        game.start()
        # 模拟 5 秒
        for _ in range(50):
            game.update(0.1)
        self.assertGreater(len(game.bullets), 0)

    def test_victory_at_100_seconds(self):
        """撑过 100 秒应该胜利"""
        game = Game()
        game.start()
        # 直接设置时间接近胜利，验证转换
        game.elapsed_time = 99.95
        game.update(0.1)
        self.assertEqual(game.state, GameState.VICTORY)


class TestPlayer(unittest.TestCase):

    def test_player_initialized_at_position(self):
        p = Player(100, 200)
        self.assertEqual(p.x, 100)
        self.assertEqual(p.y, 200)

    def test_move_clamps_to_screen_bounds(self):
        """移动应该被限制在屏幕内"""
        p = Player(100, 100)
        p.move_to(-100, -100)
        self.assertGreaterEqual(p.x, 0)
        self.assertGreaterEqual(p.y, 0)
        p.move_to(SCREEN_WIDTH + 100, SCREEN_HEIGHT + 100)
        self.assertLessEqual(p.x, SCREEN_WIDTH)
        self.assertLessEqual(p.y, SCREEN_HEIGHT)

    def test_collision_detection(self):
        """近距离应该判定碰撞"""
        p = Player(100, 100)
        self.assertTrue(p.collides_with_point(105, 105))
        self.assertFalse(p.collides_with_point(200, 200))


class TestBullet(unittest.TestCase):

    def test_bullet_moves(self):
        """子弹应该按速度移动"""
        b = Bullet(100, 100, 50, 0)
        b.update(1.0)
        self.assertAlmostEqual(b.x, 150)
        self.assertAlmostEqual(b.y, 100)

    def test_bullet_off_screen_detection(self):
        """飞出屏幕应判定出界"""
        b = Bullet(-100, 100, 0, 0)
        self.assertTrue(b.is_off_screen())

        b2 = Bullet(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 0, 0)
        self.assertFalse(b2.is_off_screen())

    def test_spawn_from_edge_within_bounds(self):
        """生成的子弹应该在屏幕边缘附近"""
        b = Bullet.spawn_from_edge(speed=100)
        # 至少有一个坐标在边缘
        on_edge = (
            b.x < 50
            or b.x > SCREEN_WIDTH - 50
            or b.y < 50
            or b.y > SCREEN_HEIGHT - 50
        )
        self.assertTrue(on_edge)


if __name__ == "__main__":
    unittest.main()