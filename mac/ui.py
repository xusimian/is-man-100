"""
macOS / PC 版本的 Pygame 渲染层

调用 core/ 中的共享逻辑，添加鼠标控制和图形渲染。
集成排行榜系统（Top 5）。
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
    PLAYER_COLOR,
    BULLET_COLOR,
    FONT_SIZE_LARGE,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_SMALL,
    COUNTDOWN_DECIMAL_PLACES,
    LATE_GAME_THRESHOLD,
)
from core.leaderboard import Leaderboard


FPS = 60
WINDOW_TITLE = "是男人就100"
LEADERBOARD_TITLE_Y = 180
LEADERBOARD_ENTRY_HEIGHT = 60


class GameUI:
    """Pygame 渲染 + 输入处理"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game = Game()
        self.leaderboard = Leaderboard()

        # macOS 系统自带的中文字体（避免中文乱码）
        chinese_font_path = "/System/Library/Fonts/Hiragino Sans GB.ttc"
        self.font_large = pygame.font.Font(chinese_font_path, FONT_SIZE_LARGE)
        self.font_medium = pygame.font.Font(chinese_font_path, FONT_SIZE_MEDIUM)
        self.font_small = pygame.font.Font(chinese_font_path, FONT_SIZE_SMALL)
        self.font_tiny = pygame.font.Font(chinese_font_path, 18)

        self.dragging = False
        # 输入名字相关状态
        self._name_input = ""
        self._awaiting_name_input = False
        self._cursor_visible = True
        self._cursor_timer = 0.0

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
                        if self._awaiting_name_input:
                            self._awaiting_name_input = False
                            self._name_input = ""
                        else:
                            running = False
                    elif self._awaiting_name_input:
                        if event.key == pygame.K_RETURN:
                            self._submit_name()
                        elif event.key == pygame.K_BACKSPACE:
                            self._name_input = self._name_input[:-1]
                        else:
                            # 接受所有可见字符（含中文）
                            if event.unicode and len(self._name_input) < 12:
                                self._name_input += event.unicode
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.game.state in (GameState.MENU, GameState.GAME_OVER, GameState.VICTORY):
                            self.game.start()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self._awaiting_name_input:
                        # 输入框中点击 = 确认（简化）
                        self._submit_name()
                    elif self.game.state == GameState.PLAYING:
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
            if not self._awaiting_name_input:
                self.game.update(dt)

            # 闪烁光标计时
            self._cursor_timer += dt

            # 渲染
            self._render()

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    def _submit_name(self) -> None:
        """提交名字到排行榜"""
        if self.game.state == GameState.GAME_OVER or self.game.state == GameState.VICTORY:
            self.leaderboard.add_entry(self._name_input, self.game.survival_time)
            self._awaiting_name_input = False
            self._name_input = ""

    # ==================== 渲染方法 ====================

    def _render(self) -> None:
        """根据当前状态渲染画面"""
        self._draw_background()
        if self._awaiting_name_input:
            self._draw_game()  # 游戏画面在背景
            self._draw_name_input()
        elif self.game.state == GameState.MENU:
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
            color = BULLET_COLOR
            if self.game.elapsed_time > LATE_GAME_THRESHOLD:
                if int(self.game.elapsed_time * 2) % 2 == 0:
                    color = (255, 200, 200)
            pygame.draw.circle(self.screen, color, (int(bullet.x), int(bullet.y)), bullet.radius)

        # 飞机（流线型剪影）
        self._draw_airplane(int(self.game.player.x), int(self.game.player.y))

        # 倒计时（顶部）
        remaining = self.game.remaining_time
        text = f"{remaining:.{COUNTDOWN_DECIMAL_PLACES}f}"
        surface = self.font_medium.render(text, True, COLOR_TEXT)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(surface, rect)

    def _draw_airplane(self, cx: int, cy: int) -> None:
        """绘制流线型飞机图标（SF Symbol airplane 风格）"""
        body_length = 50
        wing_width = 70
        tail_width = 30

        # 机身
        body = [
            (cx, cy - body_length // 2),
            (cx - 6, cy - body_length // 4),
            (cx - 6, cy + body_length // 2 - 4),
            (cx + 6, cy + body_length // 2 - 4),
            (cx + 6, cy - body_length // 4),
        ]
        pygame.draw.polygon(self.screen, PLAYER_COLOR, body)

        # 主翼
        wing_y = cy + 2
        left_wing = [
            (cx - 6, wing_y - 5),
            (cx - wing_width // 2, wing_y + 8),
            (cx - wing_width // 2, wing_y + 14),
            (cx - 6, wing_y + 6),
        ]
        right_wing = [
            (cx + 6, wing_y - 5),
            (cx + wing_width // 2, wing_y + 8),
            (cx + wing_width // 2, wing_y + 14),
            (cx + 6, wing_y + 6),
        ]
        pygame.draw.polygon(self.screen, PLAYER_COLOR, left_wing)
        pygame.draw.polygon(self.screen, PLAYER_COLOR, right_wing)

        # 尾翼
        tail = [
            (cx, cy + body_length // 2 - 8),
            (cx - tail_width // 2, cy + body_length // 2 - 4),
            (cx + tail_width // 2, cy + body_length // 2 - 4),
        ]
        pygame.draw.polygon(self.screen, PLAYER_COLOR, tail)

        # 舷窗
        pygame.draw.circle(self.screen, (50, 100, 200), (cx, cy - 5), 4)

    def _draw_menu(self) -> None:
        """开始菜单"""
        title = self.font_large.render("是男人就100", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 120))
        self.screen.blit(title, title_rect)

        subtitle = self.font_small.render("撑过 100 秒即为胜利", True, COLOR_TEXT)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(subtitle, subtitle_rect)

        # 飞机展示（菜单中央）
        self._draw_airplane(SCREEN_WIDTH // 2, 320)

        # 榜单
        self._draw_leaderboard(start_y=420)

        button_text = self.font_medium.render("点击屏幕开始", True, COLOR_VICTORY)
        button_rect = button_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
        self.screen.blit(button_text, button_rect)

    def _draw_leaderboard(self, start_y: int = LEADERBOARD_TITLE_Y) -> None:
        """绘制高分榜"""
        title = self.font_medium.render("排行榜 Top 5", True, COLOR_VICTORY)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, start_y))
        self.screen.blit(title, title_rect)

        if len(self.leaderboard) == 0:
            empty = self.font_small.render("暂无记录，成为第一个！", True, (180, 180, 180))
            empty_rect = empty.get_rect(center=(SCREEN_WIDTH // 2, start_y + 50))
            self.screen.blit(empty, empty_rect)
            return

        # 表头
        header_y = start_y + 50
        rank_text = self.font_tiny.render("排名", True, (180, 180, 180))
        name_text = self.font_tiny.render("名字", True, (180, 180, 180))
        time_text = self.font_tiny.render("时间", True, (180, 180, 180))
        date_text = self.font_tiny.render("日期", True, (180, 180, 180))
        self.screen.blit(rank_text, (40, header_y))
        self.screen.blit(name_text, (110, header_y))
        self.screen.blit(time_text, (220, header_y))
        self.screen.blit(date_text, (300, header_y))

        # 分割线
        pygame.draw.line(
            self.screen, (100, 100, 100),
            (30, header_y + 25), (SCREEN_WIDTH - 30, header_y + 25), 1
        )

        # 条目
        for idx, entry in enumerate(self.leaderboard, start=1):
            y = header_y + 35 + (idx - 1) * 45
            # 第一名高亮
            color = COLOR_VICTORY if idx == 1 else COLOR_TEXT

            rank = self.font_small.render(f"#{idx}", True, color)
            name = self.font_small.render(entry["name"][:8], True, color)  # 名字最长 8 字符
            time_s = self.font_small.render(f"{entry['time']:.1f}s", True, color)
            date_s = self.font_tiny.render(entry["date"][5:], True, (180, 180, 180))  # 只显示月-日

            self.screen.blit(rank, (40, y))
            self.screen.blit(name, (110, y))
            self.screen.blit(time_s, (220, y))
            self.screen.blit(date_s, (300, y))

    def _draw_game_over(self) -> None:
        """失败界面"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("挑战失败", True, COLOR_GAME_OVER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        time_text = f"你撑了 {self.game.survival_time:.1f} 秒"
        time_surface = self.font_medium.render(time_text, True, COLOR_TEXT)
        time_rect = time_surface.get_rect(center=(SCREEN_WIDTH // 2, 240))
        self.screen.blit(time_surface, time_rect)

        # 判断是否上榜
        if self.leaderboard.is_high_score(self.game.survival_time):
            hint = self.font_small.render("恭喜上榜！请输入名字", True, COLOR_VICTORY)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, 320))
            self.screen.blit(hint, hint_rect)
            self._awaiting_name_input = True

            # 输入框
            self._draw_input_box()
        else:
            self._draw_leaderboard(start_y=320)
            retry = self.font_small.render("点击屏幕再来一次", True, COLOR_TEXT)
            retry_rect = retry.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
            self.screen.blit(retry, retry_rect)

    def _draw_input_box(self) -> None:
        """绘制文字输入框"""
        box_y = 380
        box_h = 70
        # 输入框背景
        pygame.draw.rect(self.screen, (40, 40, 60), (60, box_y, SCREEN_WIDTH - 120, box_h), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_VICTORY, (60, box_y, SCREEN_WIDTH - 120, box_h), 2, border_radius=8)

        # 已输入文字 + 光标
        display = self._name_input
        if int(self._cursor_timer * 2) % 2 == 0:
            display += "│"  # 光标
        text_surface = self.font_medium.render(display, True, COLOR_TEXT)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, box_y + box_h // 2))
        self.screen.blit(text_surface, text_rect)

        # 提示
        hint = self.font_tiny.render("按回车确认 / Esc 跳过（匿名）", True, (180, 180, 180))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, box_y + box_h + 30))
        self.screen.blit(hint, hint_rect)

    def _draw_name_input(self) -> None:
        """独立的输入界面（在游戏中失败/胜利后）"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("挑战失败", True, COLOR_GAME_OVER)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        time_text = f"你撑了 {self.game.survival_time:.1f} 秒"
        time_surface = self.font_medium.render(time_text, True, COLOR_TEXT)
        time_rect = time_surface.get_rect(center=(SCREEN_WIDTH // 2, 240))
        self.screen.blit(time_surface, time_rect)

        hint = self.font_small.render("恭喜上榜！请输入名字", True, COLOR_VICTORY)
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, 320))
        self.screen.blit(hint, hint_rect)

        self._draw_input_box()

    def _draw_victory(self) -> None:
        """胜利界面"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("是男人！", True, COLOR_VICTORY)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        time_text = "100.0 秒 完美通关"
        time_surface = self.font_medium.render(time_text, True, COLOR_TEXT)
        time_rect = time_surface.get_rect(center=(SCREEN_WIDTH // 2, 240))
        self.screen.blit(time_surface, time_rect)

        # 通关也上榜
        if self.leaderboard.is_high_score(self.game.survival_time):
            hint = self.font_small.render("恭喜上榜！请输入名字", True, COLOR_VICTORY)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, 320))
            self.screen.blit(hint, hint_rect)
            self._awaiting_name_input = True
            self._draw_input_box()
        else:
            self._draw_leaderboard(start_y=320)
            retry = self.font_small.render("点击屏幕再次挑战", True, COLOR_TEXT)
            retry_rect = retry.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
            self.screen.blit(retry, retry_rect)