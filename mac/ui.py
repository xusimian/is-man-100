"""
macOS / PC 版本的 Pygame 渲染层

调用 core/ 中的共享逻辑，添加鼠标控制和图形渲染。
"""
import sys
import pygame
from core.game import Game
from core.game_state import GameState
from core.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_BACKGROUND_TOP,
    COLOR_BACKGROUND_BOTTOM,
    COLOR_TEXT,
    COLOR_VICTORY,
    COLOR_GAME_OVER,
    COLOR_VICTORY,
    PLAYER_COLOR,
    BULLET_COLOR,
    FONT_SIZE_LARGE,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    COUNTDOWN_DECIMAL_PLACES,
    LATE_GAME_THRESHOLD,
)


FPS = 60
WINDOW_TITLE = "是男人就100"


class GameUI:
    """Pygame 渲染 + 输入处理"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game = Game()
        self.font_large = pygame.font.SysFont("arial", FONT_SIZE_LARGE, bold=True)
        self.font_medium = pygame.font.SysFont("arial", FONT_SIZE_MEDIUM, bold=True)
        self.font_small = pygame.font.SysFont("arial", FONT_SIZE_SMALL)
        self.dragging = False

    def run(self) -> None:
        """主循环"""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # 转为秒

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.game.state in (GameState.MENU, GameState.GAME_OVER, GameState.VICTORY):
                            self.game.start()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.game.state == GameState.PLAYING:
                        self.dragging = True
                        self.game.move_player_to(*event.pos)
                    elif self.game.state != GameState.PLAYING:
                        # 点击屏幕任意位置开始游戏
                        self.game.start()
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging and self.game.state == GameState.PLAYING:
                        self.game.move_player_to(*event.pos)

            # 更新游戏逻辑
            self.game.update(dt)

            # 渲染
            self._render()

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    # ==================== 渲染方法 ====================

    def _render(self) -> None:
        """根据当前状态渲染画面"""
        self._draw_background()
        if self.game.state == GameState.MENU:
            self._draw_menu()
        elif self.game.state == GameState.PLAYING:
            self._draw_game()
        elif self.game.state == GameState.GAME_OVER:
            self._draw_game()
            self._draw_game_over()
        elif self.game.state == GameState.VICTORY:
            self._draw_game()
            self._draw_victory()

    def _draw_background(self) -> None:
        """绘制渐变背景（从顶部深蓝到底部黑）"""
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(COLOR_BACKGROUND_TOP[0] * (1 - ratio) + COLOR_BACKGROUND_BOTTOM[0] * ratio)
            g = int(COLOR_BACKGROUND_TOP[1] * (1 - ratio) + COLOR_BACKGROUND_BOTTOM[1] * ratio)
            b = int(COLOR_BACKGROUND_TOP[2] * (1 - ratio) + COLOR_BACKGROUND_BOTTOM[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    def _draw_game(self) -> None:
        """绘制游戏画面（子弹 + 飞机 + 倒计时）"""
        # 子弹
        for bullet in self.game.bullets:
            # 终局闪烁效果
            color = BULLET_COLOR
            if self.game.elapsed_time > LATE_GAME_THRESHOLD:
                # 每 0.5 秒闪烁一次
                if int(self.game.elapsed_time * 2) % 2 == 0:
                    color = (255, 200, 200)
            pygame.draw.circle(self.screen, color, (int(bullet.x), int(bullet.y)), bullet.radius)

        # 飞机（白色三角形，简易图标）
        px, py = int(self.game.player.x), int(self.game.player.y)
        size = self.game.player.size
        points = [
            (px, py - size // 2),           # 顶点
            (px - size // 2, py + size // 2),  # 左下
            (px, py + size // 3),            # 中下凹陷
            (px + size // 2, py + size // 2),  # 右下
        ]
        pygame.draw.polygon(self.screen, PLAYER_COLOR, points)

        # 倒计时（顶部）
        remaining = self.game.remaining_time
        text = f"{remaining:.{COUNTDOWN_DECIMAL_PLACES}f}"
        surface = self.font_medium.render(text, True, COLOR_TEXT)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(surface, rect)

    def _draw_menu(self) -> None:
        """开始菜单"""
        # 主标题
        title = self.font_large.render("是男人就100", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, title_rect)

        # 副标题
        subtitle = self.font_small.render("撑过 100 秒即为胜利", True, COLOR_TEXT)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 100))
        self.screen.blit(subtitle, subtitle_rect)

        # 开始按钮
        button_text = self.font_medium.render("点击屏幕开始", True, COLOR_VICTORY)
        button_rect = button_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3))
        self.screen.blit(button_text, button_rect)

    def _draw_game_over(self) -> None:
        """失败界面（半透明遮罩 + 文字）"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 标题
        title = self.font_large.render("挑战失败", True, COLOR_GAME_OVER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, title_rect)

        # 存活时间
        time_text = f"你撑了 {self.game.survival_time:.1f} 秒"
        time_surface = self.font_medium.render(time_text, True, COLOR_TEXT)
        time_rect = time_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(time_surface, time_rect)

        # 重新开始
        retry = self.font_small.render("点击屏幕再来一次", True, COLOR_TEXT)
        retry_rect = retry.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3 // 4))
        self.screen.blit(retry, retry_rect)

    def _draw_victory(self) -> None:
        """胜利界面"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 标题（金色）
        title = self.font_large.render("是男人！", True, COLOR_VICTORY)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, title_rect)

        # 时间
        time_text = "100.0 秒 完美通关"
        time_surface = self.font_medium.render(time_text, True, COLOR_TEXT)
        time_rect = time_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(time_surface, time_rect)

        # 重新开始
        retry = self.font_small.render("点击屏幕再次挑战", True, COLOR_TEXT)
        retry_rect = retry.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3 // 4))
        self.screen.blit(retry, retry_rect)