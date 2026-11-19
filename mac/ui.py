"""
macOS / PC 版本的 Pygame 渲染层（v0.5.0 深空赛博改版）

视觉风格：深空赛博（Deep Space Cyber）
- 深蓝紫虚空 + 星场 + 星云
- 霓虹青 / 品红辉光
- 发光能量弹 + 引擎尾焰 + 粒子

实现说明：
- 视觉资源集中在 mac/visuals.py，本文件只负责编排与交互
- 背景为缓存 surface，逐帧只 blit 一次（原版逐行 draw.line，浪费 852 次绘制）
- 所有辉光贴图的衰减写在 RGB 里（pygame 的 BLEND_RGB_ADD 忽略 alpha 通道）

✅ 推荐运行方式（从项目根目录）：
    python3 -m mac.main
"""
from __future__ import annotations

import sys
import logging
import math
from pathlib import Path
from typing import Optional, List, Tuple

import pygame

from core.game import Game
from core.game_state import GameState
from core.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)
from core.leaderboard import Leaderboard
from mac import visuals as V


# ==================== 常量 ====================

FPS = 60
WINDOW_TITLE = "是男人就100"


# ==================== 中文字体查找 ====================

_CHINESE_FONT_CACHE: Optional[str] = None


def _font_supports_chinese(font_path: Path) -> bool:
    """启发式判断一个字体文件是否支持中文。"""
    name_lc = font_path.name.lower()
    if any(kw in name_lc for kw in V._CJK_FILENAME_KEYWORDS):
        return True

    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()

    try:
        probe_font = pygame.font.Font(str(font_path), 24)
    except Exception:
        return False

    try:
        surface = probe_font.render(V._CJK_PROBE_CHAR, True, (0, 0, 0))
    except Exception:
        return False

    width = surface.get_width()
    del probe_font
    return width > 0


def _iter_font_files(directory: Path):
    """递归产出 directory 下所有 .otf/.ttf/.ttc 文件。"""
    if not directory.exists() or not directory.is_dir():
        return
    try:
        for entry in directory.rglob("*"):
            if not entry.is_file():
                continue
            suffix = entry.suffix.lower()
            if suffix in (".otf", ".ttf", ".ttc"):
                yield entry
    except (PermissionError, OSError):
        return


def find_chinese_font() -> str:
    """找到第一个支持中文的字体文件（跨平台）。"""
    global _CHINESE_FONT_CACHE
    if _CHINESE_FONT_CACHE is not None:
        return _CHINESE_FONT_CACHE

    for directory in V._FONT_SEARCH_DIRS:
        for font_path in _iter_font_files(directory):
            if _font_supports_chinese(font_path):
                resolved = str(font_path)
                _CHINESE_FONT_CACHE = resolved
                return resolved

    fallback = pygame.font.get_default_font()
    msg = (
        f"find_chinese_font: no CJK-capable font found in "
        f"{[str(d) for d in V._FONT_SEARCH_DIRS]}; "
        f"falling back to pygame default ({fallback}). "
        f"Chinese characters will not render correctly."
    )
    logging.warning(msg)
    print(f"[WARN] {msg}", file=sys.stderr)
    _CHINESE_FONT_CACHE = fallback
    return fallback


# ==================== 布局常量 ====================

# 字号
FONT_DISPLAY = 56
FONT_TITLE = 36
FONT_BODY = 22
FONT_CALLOUT = 18
FONT_CAPTION = 14
COUNTDOWN_FONT = 60

# 间距（8pt 栅格）
PAD_S = 8
PAD_M = 16
PAD_L = 24
PAD_XL = 32
RADIUS = 18
BUTTON_RADIUS = 26


# ==================== 主类 ====================

class GameUI:
    """Pygame 渲染 + 输入处理（深空赛博风格）"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.game = Game()
        self.leaderboard = Leaderboard()

        # 视觉系统
        self.starfield = V.StarField(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.assets = V.GlowAssets()
        self.ship_renderer = V.ShipRenderer(self.assets)
        self.bullet_renderer = V.BulletRenderer(self.assets)
        self.particles = V.ParticleSystem()

        # 字体
        self._chinese_font_path = find_chinese_font()
        self.font_display = pygame.font.Font(self._chinese_font_path, FONT_DISPLAY)
        self.font_title = pygame.font.Font(self._chinese_font_path, FONT_TITLE)
        self.font_countdown = pygame.font.Font(self._chinese_font_path, COUNTDOWN_FONT)
        self.font_body = pygame.font.Font(self._chinese_font_path, FONT_BODY)
        self.font_callout = pygame.font.Font(self._chinese_font_path, FONT_CALLOUT)
        self.font_caption = pygame.font.Font(self._chinese_font_path, FONT_CAPTION)

        self.hud = V.HUD({
            "countdown": self.font_countdown,
            "body": self.font_body,
            "callout": self.font_callout,
            "caption": self.font_caption,
        })

        self.dragging = False
        self._time: float = 0.0          # 全局动画时钟
        self._shake: float = 0.0         # 屏幕震动强度
        self._flash: float = 0.0         # 受击红闪

        # 状态机
        self._ui_state: str = "menu"  # menu / playing / gameover / victory / name_input
        self._name_input: str = ""
        self._cursor_timer: float = 0.0
        self._submitted_rank: Optional[int] = None

    # ==================== 主循环 ====================

    def run(self) -> None:
        """主循环"""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self._time += dt

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

            # 游戏逻辑
            if self._ui_state == "playing":
                self.game.update(dt)
                if self.game.state == GameState.GAME_OVER:
                    self._on_game_over()
                elif self.game.state == GameState.VICTORY:
                    self._on_victory()

            # 粒子与反馈
            self.particles.update(dt)
            self._shake = max(0.0, self._shake - dt * 3.0)
            self._flash = max(0.0, self._flash - dt * 2.5)

            # 引擎尾焰粒子（游戏中）
            if self._ui_state in ("playing", "gameover", "victory"):
                self._spawn_engine_trail(dt)

            # 光标闪烁
            self._cursor_timer += dt

            self._render()
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    # ==================== 输入处理 ====================

    def _handle_keydown(self, event) -> None:
        if event.key == pygame.K_ESCAPE:
            if self._ui_state == "name_input":
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
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self._ui_state in ("menu", "gameover", "victory"):
                    self._start_game()

    def _handle_mouse_down(self, pos: Tuple[int, int]) -> None:
        if self._ui_state == "name_input":
            self._submit_name(anonymous=False)
        elif self._ui_state == "playing":
            self.dragging = True
            self.game.move_player_to(*pos)
        elif self._ui_state == "menu":
            if self._hit_start_button(pos):
                self._start_game()
        elif self._ui_state in ("gameover", "victory"):
            if self._hit_retry_button(pos):
                self._start_game()
                return
            if (self._ui_state == "gameover"
                    and self._qualifies_for_name_input()
                    and self._hit_input_box(pos)):
                self._enter_name_input()
                return

    def _hit_start_button(self, pos: Tuple[int, int]) -> bool:
        button_rect = pygame.Rect(0, 0, 240, 58)
        button_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62)
        return button_rect.collidepoint(pos)

    def _hit_retry_button(self, pos: Tuple[int, int]) -> bool:
        button_rect = pygame.Rect(0, 0, 200, 52)
        button_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 82)
        return button_rect.collidepoint(pos)

    def _hit_input_box(self, pos: Tuple[int, int]) -> bool:
        box_rect = pygame.Rect(0, 0, SCREEN_WIDTH - 2 * PAD_XL, 56)
        box_rect.center = (SCREEN_WIDTH // 2, 470 + 28)
        return box_rect.collidepoint(pos)
    def _qualifies_for_name_input(self) -> bool:
        if self._submitted_rank is not None:
            return False
        if self.game.survival_time <= 0.0:
            return False
        return bool(self.leaderboard.is_high_score(self.game.survival_time))

    # ==================== 状态转换 ====================

    def _start_game(self) -> None:
        self.game.start()
        self._ui_state = "playing"
        self._submitted_rank = None
        self.particles.clear()
        self._shake = 0.0
        self._flash = 0.0

    def _enter_name_input(self) -> None:
        self._ui_state = "name_input"
        self._name_input = ""
        self._cursor_timer = 0.0

    def _submit_name(self, anonymous: bool) -> None:
        name = "匿名" if anonymous else (self._name_input.strip() or "匿名")
        rank = self.leaderboard.add_entry(name, self.game.survival_time)
        self._submitted_rank = rank
        self._ui_state = "gameover" if self.game.state == GameState.GAME_OVER else "victory"
        self._name_input = ""

    def _on_game_over(self) -> None:
        """碰撞失败：红闪 + 震动 + 爆散粒子"""
        self._ui_state = "gameover"
        self._shake = 1.0
        self._flash = 1.0
        self._burst_at_player()

    def _on_victory(self) -> None:
        """通关：金色粒子爆发"""
        self._ui_state = "victory"
        self._burst_at_player(colors=[V.LIME, V.AMBER, V.CYAN], count=80, speed=420)

    def _burst_at_player(
        self,
        colors: Optional[List[Tuple[int, int, int]]] = None,
        count: int = 55,
        speed: float = 340,
    ) -> None:
        """在玩家位置爆发粒子"""
        import random
        if colors is None:
            colors = [V.CYAN, V.MAGENTA, V.VIOLET]
        px, py = self.game.player.x, self.game.player.y
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.25, speed)
            self.particles.spawn(V.Particle(
                px, py,
                math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(0.4, 1.1),
                random.choice(colors),
                random.uniform(2, 5),
            ))

    def _spawn_engine_trail(self, dt: float) -> None:
        """引擎尾焰粒子（随机间隔）"""
        import random
        if random.random() > dt * 40.0:
            return
        px, py = self.game.player.x, self.game.player.y
        self.particles.spawn(V.Particle(
            px + random.uniform(-3, 3), py + 16,
            random.uniform(-12, 12), random.uniform(40, 90),
            random.uniform(0.25, 0.5),
            random.choice([V.CYAN, V.BULLET_MID]),
            random.uniform(1.5, 3),
            drag=0.9,
        ))

    # ==================== 渲染 ====================

    def _render(self) -> None:
        """主渲染入口"""
        self._draw_background()

        # 屏幕震动（对游戏层整体位移）
        shake_x = shake_y = 0
        if self._shake > 0.01:
            mag = self._shake * 7
            shake_x = math.sin(self._time * 47.0) * mag
            shake_y = math.cos(self._time * 53.0) * mag

        if self._ui_state == "menu":
            self._draw_menu()
        else:
            # 游戏画面（受震动影响）
            self._draw_game(shake_x, shake_y)

        # 粒子画在游戏层之上
        self.particles.draw(self.screen)

        if self._ui_state == "gameover":
            self._draw_game_over_modal()
        elif self._ui_state == "victory":
            self._draw_victory_modal()
        elif self._ui_state == "name_input":
            self._draw_name_input_modal()

        # 受击红闪（覆盖全屏）
        if self._flash > 0.01:
            flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surface.fill((255, 40, 40))
            flash_surface.set_alpha(int(self._flash * 90))
            self.screen.blit(flash_surface, (0, 0))

    def _draw_background(self) -> None:
        """绘制缓存的深空背景"""
        self.starfield.draw(self.screen)

    def _draw_game(self, shake_x: float = 0.0, shake_y: float = 0.0) -> None:
        """绘制游戏画面（子弹 + 飞船 + HUD）"""
        danger = self.game.elapsed_time > 80.0
        frozen = self._ui_state in ("gameover", "victory", "name_input")

        # 子弹
        for bullet in self.game.bullets:
            self.bullet_renderer.draw(
                self.screen,
                int(bullet.x + shake_x),
                int(bullet.y + shake_y),
                bullet.vx, bullet.vy,
                bullet.radius,
                danger=danger,
            )

        # 飞船
        self.ship_renderer.draw(
            self.screen,
            int(self.game.player.x + shake_x),
            int(self.game.player.y + shake_y),
            time=self._time,
            engine_intensity=1.0 if self._ui_state == "playing" else 0.35,
            shield=self._ui_state == "playing",
        )

        # HUD
        finished = self.game.state == GameState.VICTORY
        self.hud.draw(
            self.screen,
            SCREEN_WIDTH,
            remaining=self.game.remaining_time,
            progress=self.game.progress,
            elapsed=self.game.elapsed_time,
            time=self._time,
            finished=finished,
            dim=frozen,
        )

    # ==================== 菜单页 ====================

    def _draw_menu(self) -> None:
        """菜单（深空赛博）"""
        # 标题（带柔和辉光）
        title = self.font_display.render("是男人就100", True, V.TEXT_HI)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        glow = V.make_radial_glow(150, V.CYAN, inner_alpha=42, falloff=3.0)
        self.screen.blit(glow, (title_rect.centerx - 150, title_rect.centery - 150),
                         special_flags=pygame.BLEND_RGB_ADD)
        self.screen.blit(title, title_rect)

        # 副标题
        subtitle = self.font_callout.render("撑过 100 秒 证明自己", True, V.TEXT_MID)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 205)))

        # 悬浮飞船（带尾焰 + 护盾）
        hover = math.sin(self._time * 1.6) * 6
        self.ship_renderer.draw(
            self.screen, SCREEN_WIDTH // 2, int(330 + hover),
            time=self._time, engine_intensity=1.0, shield=True,
        )

        # 排行榜卡片
        self._draw_leaderboard_card(y=400, height=340)

        # 开始按钮
        self._draw_button(
            text="开始挑战",
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62),
            width=240, height=58,
            fill_color=V.CYAN,
            text_color=(4, 14, 28),
        )

    def _draw_leaderboard_card(self, y: int, height: int) -> None:
        """排行榜面板"""
        card_rect = pygame.Rect(PAD_L, y, SCREEN_WIDTH - 2 * PAD_L, height)

        # 面板背景
        bg = pygame.Surface(card_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, V.PANEL_BG, bg.get_rect(), border_radius=RADIUS)
        self.screen.blit(bg, card_rect.topleft)

        # 描边
        pygame.draw.rect(self.screen, V.PANEL_EDGE, card_rect, 1, border_radius=RADIUS)

        # 标题
        title = self.font_body.render("排行榜 · TOP 5", True, V.CYAN)
        self.screen.blit(title, (card_rect.x + PAD_M, card_rect.y + PAD_M))

        if len(self.leaderboard) == 0:
            empty = self.font_callout.render("暂无记录 · 成为第一个挑战者", True, V.TEXT_DIM)
            self.screen.blit(empty, empty.get_rect(center=card_rect.center))
        else:
            self._draw_leaderboard_entries(card_rect)

    def _draw_leaderboard_entries(self, card_rect: pygame.Rect) -> None:
        """排行榜条目"""
        start_y = card_rect.y + 60
        line_height = (card_rect.height - 70) // 5

        for idx, entry in enumerate(self.leaderboard, start=1):
            y = start_y + (idx - 1) * line_height

            medal_cx = card_rect.x + PAD_M + 14
            medal_cy = y + 12
            medal_radius = 14

            if idx <= 3:
                medal_color = [V.AMBER, (200, 205, 220), (205, 127, 50)][idx - 1]
                pygame.draw.circle(self.screen, medal_color, (medal_cx, medal_cy), medal_radius)
                pygame.draw.circle(self.screen, (80, 80, 80), (medal_cx, medal_cy), medal_radius, 1)
                num_surf = self.font_caption.render(str(idx), True, (30, 30, 40))
                self.screen.blit(num_surf, num_surf.get_rect(center=(medal_cx, medal_cy)))
                name_x = card_rect.x + 70
            else:
                # 4/5 名：直接显示排名数字
                rank_surf = self.font_body.render(f"{idx}.", True, V.TEXT_DIM)
                self.screen.blit(rank_surf, rank_surf.get_rect(midleft=(card_rect.x + PAD_M, y + 12)))
                name_x = card_rect.x + 52

            # 名字（最多 10 字符）
            name = entry["name"][:10]
            name_color = V.AMBER if idx == 1 else V.TEXT_HI
            name_surf = self.font_body.render(name, True, name_color)
            self.screen.blit(name_surf, (name_x, y))

            # 时间（右对齐）
            time_surf = self.font_body.render(f"{entry['time']:.1f}s", True, name_color)
            self.screen.blit(time_surf, time_surf.get_rect(midright=(card_rect.right - PAD_M, y + 12)))

            if idx < len(self.leaderboard):
                line_y = y + line_height - 4
                pygame.draw.line(
                    self.screen, (40, 48, 82),
                    (card_rect.x + PAD_M, line_y),
                    (card_rect.right - PAD_M, line_y), 1,
                )

    # ==================== 失败/胜利弹窗 ====================

    def _draw_modal_sheet(self) -> None:
        """弹窗遮罩"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((2, 2, 12, 155))
        self.screen.blit(overlay, (0, 0))

    def _draw_game_over_modal(self) -> None:
        """失败弹窗"""
        self._draw_modal_sheet()

        cx, cy = SCREEN_WIDTH // 2, 240
        # 图标外辉光
        glow = V.make_radial_glow(52, V.CORAL, inner_alpha=55, falloff=2.6)
        self.screen.blit(glow, (cx - 52, cy - 52), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(self.screen, V.CORAL, (cx, cy), 36)
        pygame.draw.line(self.screen, (255, 255, 255), (cx - 14, cy - 14), (cx + 14, cy + 14), 4)
        pygame.draw.line(self.screen, (255, 255, 255), (cx + 14, cy - 14), (cx - 14, cy + 14), 4)

        title = self.font_title.render("挑战失败", True, V.TEXT_HI)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 320)))

        time_text = f"{self.game.survival_time:.1f} 秒"
        time_surf = self.font_countdown.render(time_text, True, V.CORAL)
        self.screen.blit(time_surf, time_surf.get_rect(center=(SCREEN_WIDTH // 2, 380)))

        if self._qualifies_for_name_input():
            hint = self.font_body.render("新纪录！输入名字上榜", True, V.AMBER)
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 440)))
            self._draw_input_field(y=470)
        elif self._submitted_rank is not None:
            rank_text = f"已上榜 · 第 {self._submitted_rank} 名"
            rank_surf = self.font_body.render(rank_text, True, V.AMBER)
            self.screen.blit(rank_surf, rank_surf.get_rect(center=(SCREEN_WIDTH // 2, 440)))
            self._draw_leaderboard_card(y=470, height=280)
        else:
            self._draw_leaderboard_card(y=440, height=280)

        self._draw_retry_button()

    def _draw_victory_modal(self) -> None:
        """胜利弹窗"""
        self._draw_modal_sheet()

        cx, cy = SCREEN_WIDTH // 2, 250
        star = self._make_star_points(cx, cy, 38, 16, 5)
        glow = V.make_radial_glow(75, V.LIME, inner_alpha=55, falloff=2.8)
        self.screen.blit(glow, (cx - 75, cy - 75), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.polygon(self.screen, V.LIME, star)

        title = self.font_title.render("是男人！", True, V.LIME)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 330)))

        time_surf = self.font_countdown.render("100.0", True, V.LIME)
        self.screen.blit(time_surf, time_surf.get_rect(center=(SCREEN_WIDTH // 2, 390)))

        sub = self.font_callout.render("完美通关", True, V.TEXT_MID)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 428)))

        if self._submitted_rank is None:
            hint = self.font_body.render("输入名字上榜", True, V.TEXT_HI)
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 466)))
            self._draw_input_field(y=496)
        else:
            rank_text = f"已上榜 · 第 {self._submitted_rank} 名"
            rank_surf = self.font_body.render(rank_text, True, V.AMBER)
            self.screen.blit(rank_surf, rank_surf.get_rect(center=(SCREEN_WIDTH // 2, 466)))
            self._draw_leaderboard_card(y=496, height=254)

        self._draw_retry_button()

    def _draw_input_field(self, y: int) -> None:
        """输入框"""
        box_w = SCREEN_WIDTH - 2 * PAD_XL
        box_h = 56
        box_rect = pygame.Rect(0, 0, box_w, box_h)
        box_rect.center = (SCREEN_WIDTH // 2, y + box_h // 2)

        bg = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (28, 32, 66, 255), bg.get_rect(), border_radius=12)
        self.screen.blit(bg, box_rect.topleft)
        pygame.draw.rect(self.screen, V.CYAN, box_rect, 2, border_radius=12)

        if self._name_input:
            display = self._name_input
            if int(self._cursor_timer * 2) % 2 == 0:
                display += "|"
            text_surf = self.font_body.render(display, True, V.TEXT_HI)
        else:
            text_surf = self.font_body.render("点击输入名字...", True, V.TEXT_DIM)

        self.screen.blit(text_surf, text_surf.get_rect(center=box_rect.center))

        hint = self.font_caption.render("回车确认 · Esc 跳过(匿名)", True, V.TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, box_rect.bottom + 18)))

    def _draw_name_input_modal(self) -> None:
        """名字输入模态"""
        if self.game.state == GameState.GAME_OVER:
            self._draw_game_over_modal()
        else:
            self._draw_victory_modal()

    def _draw_retry_button(self) -> None:
        """再来一次按钮"""
        self._draw_button(
            text="再来一次",
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 82),
            width=200, height=52,
            fill_color=V.CYAN,
            text_color=(4, 14, 28),
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
        """霓虹按钮（胶囊形 + 柔光）"""
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center

        # 按钮外柔光
        glow_r = int(width * 0.42)
        glow = V.make_radial_glow(glow_r, fill_color, inner_alpha=38, falloff=3.0)
        self.screen.blit(glow, (rect.centerx - glow_r, rect.centery - glow_r),
                         special_flags=pygame.BLEND_RGB_ADD)

        pygame.draw.rect(self.screen, fill_color, rect, border_radius=BUTTON_RADIUS)

        text_surf = self.font_body.render(text, True, text_color)
        self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    # ==================== 工具方法 ====================

    @staticmethod
    def _make_star_points(cx: int, cy: int, outer_r: int, inner_r: int, points: int):
        """生成五角星顶点"""
        result = []
        for i in range(points * 2):
            angle = math.pi / points * i - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            result.append((int(cx + math.cos(angle) * r), int(cy + math.sin(angle) * r)))
        return result
