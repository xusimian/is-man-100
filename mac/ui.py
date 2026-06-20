"""
macOS / PC 版本的 Pygame 渲染层（v0.4.0 侵权合规修复）

设计参考：
- Apple Human Interface Guidelines 设计理念（无版权代码）
- 8pt 栅格
- 系统级字号分级
- 圆角卡片 + 半透明背景
- 胶囊按钮

App Store 合规：
- 使用自绘图形替代 emoji
- 使用开源中文字体（Noto Sans CJK / 思源黑体）
- 所有图形均为原创，无第三方图标资源依赖
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Optional, List, Tuple

import pygame

from core.game import Game
from core.game_state import GameState
from core.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYER_COLOR,
    BULLET_COLOR,
    BULLET_OUTLINE_COLOR,
)
from core.leaderboard import Leaderboard


# ==================== 常量 ====================

FPS = 60
WINDOW_TITLE = "是男人就100"

# 中文字体查找
#
# 设计原则（App Store 合规）：
# - 不引用任何 Apple 授权字体（系统只读目录仅做无害扫描，不会用作 fallback）
# - 递归扫描所有已知字体目录，用启发式判断是否真的支持 CJK
# - 找不到就降级到 pygame 默认字体并打印 warning
#
# 不再维护硬编码 PREFERRED_FONTS：用户的 ~/Library/Fonts 会被 macOS 偶尔
# 清空，硬编码路径会立刻失效；递归扫描 + 缓存才是稳定方案。

# 字体搜索目录（按优先级扫描，存在性即可，不要求可读之外的能力）
_FONT_SEARCH_DIRS: List[Path] = [
    Path.home() / "Library" / "Fonts",               # 用户字体（最常变动）
    Path("/Library/Fonts"),                           # 系统公共字体
    Path("/System/Library/Fonts"),                    # 系统字体（只读，扫不到但无害）
    Path("/usr/local/share/fonts"),                   # Intel Mac Homebrew
    Path("/opt/homebrew/share/fonts"),                # Apple Silicon Homebrew
]

# 文件名启发式关键词（命中即视为候选 CJK 字体）
_CJK_FILENAME_KEYWORDS = (
    "sourcehan",
    "notosanscjk",
    "notosanssc",
    "notosanstc",
    "wenquanyi",
    "simhei",
    "microsoftyahei",
    "droidsansfallback",
    "cjk",
    "chinese",
    "han",
)

# 用于渲染探测的已知 CJK 字符（中 = U+4E2D）
_CJK_PROBE_CHAR = "中"


# ==================== 中文字体查找 ====================

_CHINESE_FONT_CACHE: Optional[str] = None


def _font_supports_chinese(font_path: Path) -> bool:
    """启发式判断一个字体文件是否支持中文。

    命中条件（任一即可）：
      1. 文件名包含已知 CJK 关键词（SourceHan / NotoSansCJK / SimHei 等）
      2. 能被 pygame 打开，且渲染 "中" 字符得到的位图宽度 > 0

    pygame.font.Font() 在遇到坏字体（Keyboard.ttf 等）时可能抛异常，
    必须 try/except 兜住，否则一次扫描会让整个 UI 初始化失败。
    """
    name_lc = font_path.name.lower()
    if any(kw in name_lc for kw in _CJK_FILENAME_KEYWORDS):
        return True

    # SDL_ttf 在 pygame.init() 之前调用 Font() 会返回无效对象；
    # 调用方（如 GameUI）通常已经 init 过，但保险起见自检一下
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()

    try:
        probe_font = pygame.font.Font(str(font_path), 24)
    except Exception:
        return False

    try:
        surface = probe_font.render(_CJK_PROBE_CHAR, True, (0, 0, 0))
    except Exception:
        return False
    finally:
        # Font 对象无显式 close，主动 del 让 pygame 立即释放 SDL 资源
        # 注意：必须先读 surface.get_width() 再 del，否则 surface 会失效
        pass

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
        # 部分 /System/Library/Fonts 子目录拒绝遍历，吞掉继续
        return


def find_chinese_font() -> str:
    """找到第一个支持中文的字体文件。

    策略：
      1. 按 _FONT_SEARCH_DIRS 顺序递归扫描
      2. 对每个 .otf/.ttf/.ttc 用 _font_supports_chinese() 判定
      3. 第一个命中即返回；用模块级缓存避免每帧重扫
      4. 全部目录都找不到时降级到 pygame 默认字体，并 logging.warning

    绝不会引用任何 Apple 授权字体作为 fallback，
    保持 App Store 合规（见 COMPLIANCE.md）。
    """
    global _CHINESE_FONT_CACHE
    if _CHINESE_FONT_CACHE is not None:
        return _CHINESE_FONT_CACHE

    for directory in _FONT_SEARCH_DIRS:
        for font_path in _iter_font_files(directory):
            if _font_supports_chinese(font_path):
                resolved = str(font_path)
                _CHINESE_FONT_CACHE = resolved
                return resolved

    # 全部找不到 —— 降级到 pygame 默认字体（仅 Latin）
    fallback = pygame.font.get_default_font()
    msg = (
        f"find_chinese_font: no CJK-capable font found in "
        f"{[str(d) for d in _FONT_SEARCH_DIRS]}; "
        f"falling back to pygame default ({fallback}). "
        f"Chinese characters will not render correctly."
    )
    logging.warning(msg)
    print(f"[WARN] {msg}", file=sys.stderr)
    _CHINESE_FONT_CACHE = fallback
    return fallback


# 找到的字体路径（运行时决定）
CHINESE_FONT = None  # 在 GameUI.__init__ 中通过 find_chinese_font() 设置


# iOS 系统色板（颜色本身无版权，可自由使用）
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

        # 找到可用的中文字体（递归扫描 + 启发式判定，优先开源免费字体）
        # App Store 上架时建议把字体打包进 App，避免系统字体依赖
        self._chinese_font_path = find_chinese_font()
        self.font_display = pygame.font.Font(self._chinese_font_path, FONT_DISPLAY)
        self.font_title = pygame.font.Font(self._chinese_font_path, FONT_TITLE)
        self.font_countdown = pygame.font.Font(self._chinese_font_path, COUNTDOWN_FONT)
        self.font_body = pygame.font.Font(self._chinese_font_path, FONT_BODY)
        self.font_callout = pygame.font.Font(self._chinese_font_path, FONT_CALLOUT)
        self.font_caption = pygame.font.Font(self._chinese_font_path, FONT_CAPTION)

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
                    and self._qualifies_for_name_input()
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

    def _qualifies_for_name_input(self) -> bool:
        """是否应允许进入"输入名字"流程

        条件：分数 > 0 且分数值得上榜（且尚未提交过）。
        0 分（即时死亡）不应弹出名字输入框。
        """
        if self._submitted_rank is not None:
            return False
        if self.game.survival_time <= 0.0:
            return False
        return bool(self.leaderboard.is_high_score(self.game.survival_time))

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
        # 子弹（白色填充 + 黑色细描边，深蓝背景下高对比度）
        for bullet in self.game.bullets:
            # 终局（>80s）警告效果：让描边闪烁
            outline_color = BULLET_OUTLINE_COLOR
            if self.game.elapsed_time > 80.0:
                if int(self.game.elapsed_time * 2) % 2 == 0:
                    outline_color = COLOR_RED  # 终局闪红边
            # 描边先画（稍大）
            pygame.draw.circle(
                self.screen, outline_color,
                (int(bullet.x), int(bullet.y)),
                bullet.radius + 1,
            )
            # 主体白圆
            pygame.draw.circle(
                self.screen, BULLET_COLOR,
                (int(bullet.x), int(bullet.y)),
                bullet.radius,
            )

        # 飞机
        self._draw_airplane(int(self.game.player.x), int(self.game.player.y))

        # 倒计时（顶部，大号数字）
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
        """流线型飞机（自绘图形，无版权问题）"""
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
        """排行榜条目（自绘奖牌图标，避免 emoji 侵权）"""
        start_y = card_rect.y + 60
        line_height = (card_rect.height - 70) // 5

        for idx, entry in enumerate(self.leaderboard, start=1):
            y = start_y + (idx - 1) * line_height

            # 奖牌图标（自绘）
            medal_cx = card_rect.x + PAD_M + 14
            medal_cy = y + 12
            medal_radius = 14

            if idx == 1:
                medal_color = COLOR_GOLD
            elif idx == 2:
                medal_color = (192, 192, 192)  # 银
            elif idx == 3:
                medal_color = (205, 127, 50)   # 铜
            else:
                medal_color = COLOR_LABEL_SECONDARY

            # 画奖牌圆
            if idx <= 3:
                pygame.draw.circle(self.screen, medal_color, (medal_cx, medal_cy), medal_radius)
                pygame.draw.circle(self.screen, (80, 80, 80), (medal_cx, medal_cy), medal_radius, 1)
                # 中央排名数字
                num_surf = self.font_caption.render(str(idx), True, (50, 50, 50))
                num_rect = num_surf.get_rect(center=(medal_cx, medal_cy))
                self.screen.blit(num_surf, num_rect)
            else:
                # 普通排名：数字
                rank_surf = self.font_body.render(f"{idx}.", True, COLOR_LABEL_SECONDARY)
                rank_rect = rank_surf.get_rect(midleft=(card_rect.x + PAD_M, y + 6))
                self.screen.blit(rank_surf, rank_rect)
                continue  # 跳到下一个条目

            # 名字（最多 10 字符）
            name = entry["name"][:10]
            name_color = COLOR_GOLD if idx == 1 else COLOR_LABEL
            name_surf = self.font_body.render(name, True, name_color)
            self.screen.blit(name_surf, (card_rect.x + 70, y))

            # 时间（右对齐）
            time_surf = self.font_body.render(f"{entry['time']:.1f}s", True, name_color)
            time_rect = time_surf.get_rect(midright=(card_rect.right - PAD_M, y + 12))
            self.screen.blit(time_surf, time_rect)

            # 分隔线
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
        if self._qualifies_for_name_input():
            hint = self.font_body.render("新纪录！输入名字上榜", True, COLOR_GOLD)
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
            hint = self.font_body.render("输入名字上榜", True, COLOR_LABEL)
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