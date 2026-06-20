"""
macOS / PC 版本的 Pygame 渲染层（v0.3.0 iOS 风格重设计）

设计参考 Apple Human Interface Guidelines：
- 8pt 栅格
- SF Pro / 苹方字体分级
- 圆角卡片 + 半透明背景
- 系统色板
- 底部 sheet 式弹窗

集成排行榜 + 中文输入支持。
"""
from __future__ import annotations

import sys
from typing import Optional, List, Tuple

import pygame

from core.game import Game
from core.game_state import GameState
from core.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYER_COLOR,
    BULLET_COLOR,
)
from core.leaderboard import Leaderboard


# ==================== 常量 ====================

FPS = 60
WINDOW_TITLE = "是男人就100"

# 中文字体
CHINESE_FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"

# iOS 系统色板
COLOR_BG_TOP = (28, 28, 30)         # 深灰背景（暗模式）
COLOR_BG_BOTTOM = (0, 0, 0)
COLOR_LABEL = (255, 255, 255)        # 主文字（白色）
COLOR_LABEL_SECONDARY = (142, 142, 147)  # 次要文字（灰）
COLOR_BLUE = (10, 132, 255)          # iOS 系统蓝
COLOR_GREEN = (48, 209, 88)          # iOS 系统绿
COLOR_RED = (255, 69, 58)            # iOS 系统红
COLOR_GOLD = (255, 214, 10)          # iOS 黄
COLOR_CARD_BG = (44, 44, 46, 230)    # 半透明卡片（暗模式）
COLOR_CARD_STROKE = (72, 72, 74)     # 卡片边框
COLOR_OVERLAY = (0, 0, 0, 140)       # 背景遮罩

# 字号（iOS 风格）
FONT_DISPLAY = 56   # 超大标题（"是男人就100"）
FONT_TITLE = 36     # 大标题
FONT_BODY = 22      # 正文
FONT_CALLOUT = 18   # 注释
FONT_CAPTION = 14   # 小字

# 间距（8pt 栅格）
PAD_S = 8
PAD_M = 16
PAD_L = 24
PAD_XL = 32
RADIUS = 16         # 卡片圆角
BUTTON_RADIUS = 22  # 按钮圆角（胶囊）

# 倒计时位置
COUNTDOWN_Y = 80
COUNTDOWN_FONT = 60


# ==================== 主类 ====================

class GameUI:
    """Pygame 渲染 + 输入处理（iOS 风格）"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game = Game()
        self.leaderboard = Leaderboard()

        # 字体（一套字号分级，iOS 风格）
        self.font_display = pygame.font.Font(CHINESE_FONT, FONT_DISPLAY)
        self.font_title = pygame.font.Font(CHINESE_FONT, FONT_TITLE)
        self.font_countdown = pygame.font.Font(CHINESE_FONT, COUNTDOWN_FONT)
        self.font_body = pygame.font.Font(CHINESE_FONT, FONT_BODY)
        self.font_callout = pygame.font.Font(CHINESE_FONT, FONT_CALLOUT)
        self.font_caption = pygame.font.Font(CHINESE_FONT, FONT_CAPTION)

        self.dragging = False

        # 状态机（关键修复：明确分离菜单/游戏/结算/输入四个状态）
        self._ui_state: str = "menu"  # menu / playing / gameover / victory / name_input
        self._name_input: str = ""
        self._cursor_timer: float = 0.0
        self._submitted_rank: Optional[int] = None  # 提交后的名次，用于显示

    # ==================== 主循环 ====================

    def run(self) -> None:
        """主循环"""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging and self._ui_state == "playing":
                        self.game.move_player_to(*event.pos)

            # 只在游戏中更新游戏逻辑
            if self._ui_state == "playing":
                self.game.update(dt)
                # 同步游戏状态到 UI 状态（关键！处理自动状态转换）
                if self.game.state == GameState.GAME_OVER:
                    self._ui_state = "gameover"
                elif self.game.state == GameState.VICTORY:
                    self._ui_state = "victory"

            # 闪烁光标
            self._cursor_timer += dt

            # 渲染
            self._render()

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    # ==================== 输入处理 ====================

    def _handle_keydown(self, event) -> None:
        """统一处理键盘事件"""
        if event.key == pygame.K_ESCAPE:
            if self._ui_state == "name_input":
                # Esc 跳过输入（匿名提交）
                self._submit_name(anonymous=True)
            else:
                sys.exit(0)
            return

        if self._ui_state == "name_input":
            if event.key == pygame.K_RETURN:
                self._submit_name(anonymous=False)
            elif event.key == pygame.K_BACKSPACE:
                self._name_input = self._name_input[:-1]
            else:
                if event.unicode and len(self._name_input) < 12:
                    self._name_input += event.unicode
        else:
            # 其他状态的回车/空格 → 开始游戏
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._ui_state in ("menu", "gameover", "victory"):
                    self._start_game()

    def _handle_mouse_down(self, pos: Tuple[int, int]) -> None:
        """统一处理鼠标点击"""
        if self._ui_state == "name_input":
            # 输入框内点击任意位置 → 确认提交
            self._submit_name(anonymous=False)
        elif self._ui_state == "playing":
            self.dragging = True
            self.game.move_player_to(*pos)
        elif self._ui_state == "menu":
            # 菜单页：检查是否点了开始按钮
            if self._hit_start_button(pos):
                self._start_game()
        elif self._ui_state == "gameover" or self._ui_state == "victory":
            # 优先检查：是否点了"再来一次"按钮
            if self._hit_retry_button(pos):
                self._start_game()
                return
            # 其次：是否点了输入框（仅失败时上榜才显示）
            if (self._ui_state == "gameover"
                    and self.leaderboard.is_high_score(self.game.survival_time)
                    and self._submitted_rank is None
                    and self._hit_input_box(pos)):
                self._enter_name_input()
                return
            # 其他区域点击：不响应（避免误触）

    def _hit_start_button(self, pos: Tuple[int, int]) -> bool:
        """检查是否点击了菜单页"开始挑战"按钮"""
        button_rect = pygame.Rect(0, 0, 240, 56)
        button_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)
        return button_rect.collidepoint(pos)

    def _hit_retry_button(self, pos: Tuple[int, int]) -> bool:
        """检查是否点击了"再来一次"按钮"""
        button_rect = pygame.Rect(0, 0, 200, 50)
        button_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80)
        return button_rect.collidepoint(pos)

    def _hit_input_box(self, pos: Tuple[int, int]) -> bool:
        """检查是否点击了输入框"""
        # 输入框位置和 _draw_game_over_modal 中 y=470 一致
        box_rect = pygame.Rect(0, 0, SCREEN_WIDTH - 2 * PAD_XL, 56)
        box_rect.center = (SCREEN_WIDTH // 2, 470 + 28)  # y + box_h/2
        return box_rect.collidepoint(pos)

    # ==================== 状态转换 ====================

    def _start_game(self) -> None:
        """开始游戏"""
        self.game.start()
        self._ui_state = "playing"
        self._submitted_rank = None

    def _enter_name_input(self) -> None:
        """进入名字输入状态"""
        self._ui_state = "name_input"
        self._name_input = ""
        self._cursor_timer = 0.0

    def _submit_name(self, anonymous: bool) -> None:
        """提交名字"""
        name = "匿名" if anonymous else (self._name_input.strip() or "匿名")
        rank = self.leaderboard.add_entry(name, self.game.survival_time)
        self._submitted_rank = rank
        self._ui_state = "gameover" if self.game.state == GameState.GAME_OVER else "victory"
        self._name_input = ""

    # ==================== 渲染 ====================

    def _render(self) -> None:
        """主渲染入口"""
        self._draw_background()
        if self._ui_state == "playing":
            self._draw_game()
        elif self._ui_state == "menu":
            self._draw_menu()
        elif self._ui_state == "gameover":
            self._draw_game()  # 游戏画面在背景
            self._draw_game_over_modal()
        elif self._ui_state == "victory":
            self._draw_game()
            self._draw_victory_modal()
        elif self._ui_state == "name_input":
            self._draw_game()
            self._draw_name_input_modal()

    def _draw_background(self) -> None:
        """绘制渐变背景（暗模式）"""
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(COLOR_BG_TOP[0] * (1 - ratio) + COLOR_BG_BOTTOM[0] * ratio)
            g = int(COLOR_BG_TOP[1] * (1 - ratio) + COLOR_BG_BOTTOM[1] * ratio)
            b = int(COLOR_BG_TOP[2] * (1 - ratio) + COLOR_BG_BOTTOM[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    def _draw_game(self) -> None:
        """绘制游戏画面"""
        # 子弹
        for bullet in self.game.bullets:
            color = BULLET_COLOR
            if self.game.elapsed_time > 80.0:
                if int(self.game.elapsed_time * 2) % 2 == 0:
                    color = (255, 200, 200)
            pygame.draw.circle(self.screen, color, (int(bullet.x), int(bullet.y)), bullet.radius)

        # 飞机
        self._draw_airplane(int(self.game.player.x), int(self.game.player.y))

        # 倒计时（顶部，SF 风格大数字）
        remaining = self.game.remaining_time
        text = f"{remaining:.1f}"
        surface = self.font_countdown.render(text, True, COLOR_LABEL)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, COUNTDOWN_Y))
        self.screen.blit(surface, rect)

        # "秒" 小字
        unit_surface = self.font_callout.render("秒", True, COLOR_LABEL_SECONDARY)
        unit_rect = unit_surface.get_rect(midleft=(rect.right + 6, rect.centery))
        self.screen.blit(unit_surface, unit_rect)

    def _draw_airplane(self, cx: int, cy: int) -> None:
        """流线型飞机（SF Symbol 风格）"""
        # 机身
        body = [
            (cx, cy - 25),  # 机头
            (cx - 7, cy - 15),
            (cx - 7, cy + 22),
            (cx + 7, cy + 22),
            (cx + 7, cy - 15),
        ]
        pygame.draw.polygon(self.screen, COLOR_LABEL, body)

        # 主翼（梯形）
        wing_y = cy
        left_wing = [
            (cx - 7, wing_y - 5),
            (cx - 35, wing_y + 10),
            (cx - 35, wing_y + 16),
            (cx - 7, wing_y + 8),
        ]
        right_wing = [
            (cx + 7, wing_y - 5),
            (cx + 35, wing_y + 10),
            (cx + 35, wing_y + 16),
            (cx + 7, wing_y + 8),
        ]
        pygame.draw.polygon(self.screen, COLOR_LABEL, left_wing)
        pygame.draw.polygon(self.screen, COLOR_LABEL, right_wing)

        # 尾翼
        tail = [
            (cx, cy + 22),
            (cx - 12, cy + 22),
            (cx - 15, cy + 14),
            (cx + 15, cy + 14),
            (cx + 12, cy + 22),
        ]
        pygame.draw.polygon(self.screen, COLOR_LABEL, tail)

        # 舷窗
        pygame.draw.circle(self.screen, COLOR_BLUE, (cx, cy - 5), 5)

    # ==================== 菜单页 ====================

    def _draw_menu(self) -> None:
        """iOS 风格菜单"""
        # 大标题
        title = self.font_display.render("是男人就100", True, COLOR_LABEL)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 160))
        self.screen.blit(title, title_rect)

        # 副标题
        subtitle = self.font_callout.render("撑过 100 秒 证明自己", True, COLOR_LABEL_SECONDARY)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 215))
        self.screen.blit(subtitle, subtitle_rect)

        # 飞机展示（中央偏上）
        self._draw_airplane(SCREEN_WIDTH // 2, 320)

        # 排行榜卡片
        self._draw_leaderboard_card(y=420, height=340)

        # 开始按钮（iOS 风格蓝色胶囊）
        self._draw_button(
            text="开始挑战",
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60),
            width=240, height=56,
            fill_color=COLOR_BLUE,
            text_color=COLOR_LABEL,
        )

    def _draw_leaderboard_card(self, y: int, height: int) -> None:
        """排行榜卡片（iOS 风格圆角卡片）"""
        card_rect = pygame.Rect(PAD_L, y, SCREEN_WIDTH - 2 * PAD_L, height)

        # 卡片背景（半透明）
        card_surface = pygame.Surface(card_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(card_surface, COLOR_CARD_BG, card_surface.get_rect(), border_radius=RADIUS)
        self.screen.blit(card_surface, card_rect.topleft)

        # 卡片描边（微妙）
        pygame.draw.rect(self.screen, COLOR_CARD_STROKE, card_rect, 1, border_radius=RADIUS)

        # 卡片标题
        title = self.font_body.render("排行榜 · Top 5", True, COLOR_LABEL)
        self.screen.blit(title, (card_rect.x + PAD_M, card_rect.y + PAD_M))

        # 内容
        if len(self.leaderboard) == 0:
            empty = self.font_callout.render("暂无记录 · 成为第一个挑战者", True, COLOR_LABEL_SECONDARY)
            empty_rect = empty.get_rect(center=(card_rect.centerx, card_rect.centery))
            self.screen.blit(empty, empty_rect)
        else:
            self._draw_leaderboard_entries(card_rect)

    def _draw_leaderboard_entries(self, card_rect: pygame.Rect) -> None:
        """排行榜条目"""
        start_y = card_rect.y + 60
        line_height = (card_rect.height - 70) // 5

        for idx, entry in enumerate(self.leaderboard, start=1):
            y = start_y + (idx - 1) * line_height

            # 第一名金色图标
            if idx == 1:
                rank_label = "🥇"
                name_color = COLOR_GOLD
            elif idx == 2:
                rank_label = "🥈"
                name_color = COLOR_LABEL
            elif idx == 3:
                rank_label = "🥉"
                name_color = (205, 127, 50)  # 铜色
            else:
                rank_label = f"{idx}."
                name_color = COLOR_LABEL

            # 排名
            rank_surf = self.font_body.render(rank_label, True, name_color)
            self.screen.blit(rank_surf, (card_rect.x + PAD_M, y))

            # 名字（最多 10 字符）
            name = entry["name"][:10]
            name_surf = self.font_body.render(name, True, name_color)
            self.screen.blit(name_surf, (card_rect.x + 70, y))

            # 时间（右对齐）
            time_surf = self.font_body.render(f"{entry['time']:.1f}s", True, name_color)
            time_rect = time_surf.get_rect(midright=(card_rect.right - PAD_M, y + 12))
            self.screen.blit(time_surf, time_rect)

            # 分隔线（最后一条不画）
            if idx < len(self.leaderboard):
                line_y = y + line_height - 4
                pygame.draw.line(
                    self.screen,
                    (58, 58, 60),
                    (card_rect.x + PAD_M, line_y),
                    (card_rect.right - PAD_M, line_y),
                    1,
                )

    # ==================== 失败/胜利弹窗 ====================

    def _draw_game_over_modal(self) -> None:
        """失败弹窗（iOS 风格 sheet）"""
        self._draw_modal_sheet()

        # 失败图标（大圆 + 叉）
        cx, cy = SCREEN_WIDTH // 2, 240
        pygame.draw.circle(self.screen, COLOR_RED, (cx, cy), 36)
        # 画叉
        pygame.draw.line(self.screen, COLOR_LABEL, (cx - 14, cy - 14), (cx + 14, cy + 14), 4)
        pygame.draw.line(self.screen, COLOR_LABEL, (cx + 14, cy - 14), (cx - 14, cy + 14), 4)

        # 标题
        title = self.font_title.render("挑战失败", True, COLOR_LABEL)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 320))
        self.screen.blit(title, title_rect)

        # 存活时间
        time_text = f"{self.game.survival_time:.1f} 秒"
        time_surf = self.font_countdown.render(time_text, True, COLOR_RED)
        time_rect = time_surf.get_rect(center=(SCREEN_WIDTH // 2, 380))
        self.screen.blit(time_surf, time_rect)

        # 上榜提示
        if self.leaderboard.is_high_score(self.game.survival_time) and self._submitted_rank is None:
            hint = self.font_body.render("🎉 新纪录！输入名字上榜", True, COLOR_GOLD)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, 440))
            self.screen.blit(hint, hint_rect)
            self._draw_input_field(y=470)
        elif self._submitted_rank is not None:
            rank_text = f"已上榜 · 第 {self._submitted_rank} 名"
            rank_surf = self.font_body.render(rank_text, True, COLOR_GOLD)
            rank_rect = rank_surf.get_rect(center=(SCREEN_WIDTH // 2, 440))
            self.screen.blit(rank_surf, rank_rect)
            # 显示更新后的榜单
            self._draw_leaderboard_card(y=470, height=280)
        else:
            # 没上榜，显示当前榜单
            self._draw_leaderboard_card(y=440, height=280)

        # 再来一次按钮
        self._draw_retry_button()

    def _draw_victory_modal(self) -> None:
        """胜利弹窗"""
        self._draw_modal_sheet()

        # 胜利图标（星星）
        cx, cy = SCREEN_WIDTH // 2, 240
        # 五角星（简化版：用多边形）
        star_points = self._make_star_points(cx, cy, 36, 18, 5)
        pygame.draw.polygon(self.screen, COLOR_GOLD, star_points)

        # 标题
        title = self.font_title.render("是男人！", True, COLOR_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 320))
        self.screen.blit(title, title_rect)

        # 时间
        time_text = "100.0 秒 完美通关"
        time_surf = self.font_countdown.render("100.0", True, COLOR_GOLD)
        time_rect = time_surf.get_rect(center=(SCREEN_WIDTH // 2, 380))
        self.screen.blit(time_surf, time_rect)

        # 上榜提示
        if self._submitted_rank is None:
            hint = self.font_body.render("🎉 输入名字上榜", True, COLOR_LABEL)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, 440))
            self.screen.blit(hint, hint_rect)
            self._draw_input_field(y=470)
        else:
            rank_text = f"已上榜 · 第 {self._submitted_rank} 名"
            rank_surf = self.font_body.render(rank_text, True, COLOR_GOLD)
            rank_rect = rank_surf.get_rect(center=(SCREEN_WIDTH // 2, 440))
            self.screen.blit(rank_surf, rank_rect)
            self._draw_leaderboard_card(y=470, height=280)

        # 再来一次按钮
        self._draw_retry_button()

    def _draw_modal_sheet(self) -> None:
        """弹窗背景（半透明遮罩 + 底部圆角 sheet）"""
        # 顶部遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        self.screen.blit(overlay, (0, 0))

    def _draw_input_field(self, y: int) -> None:
        """输入框（iOS 风格圆角输入框）"""
        box_w = SCREEN_WIDTH - 2 * PAD_XL
        box_h = 56
        box_rect = pygame.Rect(0, 0, box_w, box_h)
        box_rect.center = (SCREEN_WIDTH // 2, y + box_h // 2)

        # 背景
        box_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(box_surface, (58, 58, 60, 255), box_surface.get_rect(), border_radius=12)
        self.screen.blit(box_surface, box_rect.topleft)

        # 边框（聚焦时金色）
        pygame.draw.rect(self.screen, COLOR_GOLD, box_rect, 2, border_radius=12)

        # 占位文字 vs 已输入文字
        if self._name_input:
            # 显示输入内容 + 光标
            display = self._name_input
            if int(self._cursor_timer * 2) % 2 == 0:
                display += "|"
            text_surf = self.font_body.render(display, True, COLOR_LABEL)
        else:
            # 占位文字
            placeholder = self.font_body.render("点击输入名字...", True, COLOR_LABEL_SECONDARY)
            text_surf = placeholder

        text_rect = text_surf.get_rect(center=box_rect.center)
        self.screen.blit(text_surf, text_rect)

        # 提示
        hint = self.font_caption.render("回车确认 · Esc 跳过(匿名)", True, COLOR_LABEL_SECONDARY)
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, box_rect.bottom + 18))
        self.screen.blit(hint, hint_rect)

    def _draw_name_input_modal(self) -> None:
        """专门的名字输入模态（带输入框但隐藏提示等）"""
        # 重新走 gameover/victory 流程，但强制显示输入框
        # 简化：直接调 gameover 渲染 + 输入框
        if self.game.state == GameState.GAME_OVER:
            self._draw_game_over_modal()
        else:
            self._draw_victory_modal()

    def _draw_retry_button(self) -> None:
        """再来一次按钮"""
        self._draw_button(
            text="再来一次",
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80),
            width=200, height=50,
            fill_color=COLOR_BLUE,
            text_color=COLOR_LABEL,
        )

    # ==================== 通用 UI 组件 ====================

    def _draw_button(
        self,
        text: str,
        center: Tuple[int, int],
        width: int,
        height: int,
        fill_color: Tuple[int, int, int],
        text_color: Tuple[int, int, int],
    ) -> None:
        """iOS 风格按钮（胶囊形）"""
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center

        # 按钮背景（实色填充 + 圆角）
        pygame.draw.rect(self.screen, fill_color, rect, border_radius=BUTTON_RADIUS)

        # 按钮文字
        text_surf = self.font_body.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    # ==================== 工具方法 ====================

    @staticmethod
    def _make_star_points(cx: int, cy: int, outer_r: int, inner_r: int, points: int) -> List[Tuple[int, int]]:
        """生成五角星顶点"""
        import math
        result = []
        for i in range(points * 2):
            angle = math.pi / points * i - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            x = cx + math.cos(angle) * r
            y = cy + math.sin(angle) * r
            result.append((int(x), int(y)))
        return result