"""
深空赛博（Deep Space Cyber）视觉系统

独立的渲染资源层：
- 缓存式星场背景（一次性生成，逐帧只 blit）
- 预渲染发光光晕（子弹 / 引擎尾焰 / 粒子）
- 粒子系统（引擎尾焰、爆散、冲击波）

设计要点：
1. 所有发光效果用 **预渲染 surface + BLEND_RGB_ADD** 实现，
   避免逐帧逐像素运算，实测比逐帧画圆快一个数量级。
2. 背景是静态缓存（星点固定），仅在 resize 时重建。
3. 颜色统一走 CYBER 色板，和 mac/ui.py 保持解耦。

作者备注：个人娱乐项目，风格取向为「深空赛博」——
深蓝紫渐变虚空 + 霓虹青/品红辉光 + 扫描线质感。
"""
from __future__ import annotations

import math
import os
import random
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

Color = Tuple[int, int, int]
ColorRGBA = Tuple[int, int, int, int]


# ==================== CYBER 色板 ====================

# 背景（深空）
BG_TOP = (12, 10, 32)          # 深紫黑
BG_MID = (18, 16, 52)          # 深蓝紫
BG_BOTTOM = (4, 4, 14)         # 近黑
NEBULA_A = (58, 32, 120)       # 星云紫（叠加层）
NEBULA_B = (16, 62, 122)       # 星云蓝（叠加层）

# 霓虹主色
CYAN = (0, 229, 255)           # 霓虹青（主）
MAGENTA = (255, 45, 170)       # 品红（副）
VIOLET = (150, 90, 255)        # 紫
LIME = (120, 255, 170)         # 荧光绿（胜利）
AMBER = (255, 180, 40)         # 琥珀（警告）
CORAL = (255, 85, 85)          # 珊瑚红（危险 / 失败）

# 文字
TEXT_HI = (235, 245, 255)      # 主文字（偏冷的白）
TEXT_MID = (150, 165, 200)     # 次要文字
TEXT_DIM = (95, 108, 140)      # 弱化文字

# 面板
PANEL_BG = (16, 18, 42, 205)   # 半透明面板
PANEL_EDGE = (90, 130, 190, 120)
PANEL_EDGE_HI = (0, 229, 255, 180)


# ==================== 字体查找（跨平台） ====================

# 字体搜索目录（按优先级扫描，存在性即可）
_FONT_SEARCH_DIRS: List[Path] = [
    Path.home() / "Library" / "Fonts",               # macOS 用户字体
    Path("/Library/Fonts"),                           # macOS 系统公共字体
    Path("/System/Library/Fonts"),                    # macOS 系统字体
    Path("/usr/local/share/fonts"),                   # Intel Mac Homebrew
    Path("/opt/homebrew/share/fonts"),                # Apple Silicon Homebrew
    Path("/usr/share/fonts"),                         # Linux 系统字体
    Path("/usr/share/fonts/truetype"),                # Linux TrueType
    Path("/usr/local/share/fonts"),                   # Linux 自装字体
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",       # Windows 系统字体
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts",        # Windows 用户字体
]

# 文件名启发式关键词（命中即视为候选 CJK 字体）
_CJK_FILENAME_KEYWORDS = (
    "sourcehan",
    "notosanscjk",
    "notosanssc",
    "notosanstc",
    "notoserifcjk",
    "wenquanyi",
    "simhei",
    "simsun",
    "msyh",
    "microsoftyahei",
    "droidsansfallback",
    "pingfang",
    "hiragino",
    "cjk",
    "chinese",
    "han",
)

# 用于渲染探测的已知 CJK 字符（中 = U+4E2D）
_CJK_PROBE_CHAR = "中"

# 玩家飞船
SHIP_HULL = (235, 246, 255)    # 船体高光
SHIP_BODY = (112, 152, 214)    # 船体主体（更亮，提升可读性）
SHIP_DARK = (46, 66, 118)      # 船体暗部
SHIP_COCKPIT = (0, 229, 255)   # 座舱（发光青）

# 子弹
BULLET_CORE = (255, 255, 255)  # 核心（纯白）
BULLET_MID = (0, 229, 255)     # 中层（青）
BULLET_EDGE = (120, 60, 255)   # 外层（紫）


# ==================== 工具函数 ====================

def lerp_color(c1: Color, c2: Color, t: float) -> Color:
    """线性插值两个 RGB 颜色"""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def ease_out_cubic(t: float) -> float:
    """三次缓出（用于动效的减速）"""
    t = max(0.0, min(1.0, t))
    inv = 1.0 - t
    return 1.0 - inv * inv * inv


def make_radial_glow(
    radius: int,
    color: Color,
    inner_alpha: int = 255,
    falloff: float = 2.2,
) -> pygame.Surface:
    """预渲染一个径向发光光晕（additive 混合用）。

    ⚠️ 关键：pygame 的 BLEND_RGB_ADD 混合公式是 dst = dst + src，
    **逐像素的 alpha 通道会被完全忽略**。如果把 alpha 写进像素里，
    辉光会变成满强度的纯色圆盘（标题、按钮全糊成一坨）。

    因此这里把衰减直接写进 RGB 值（颜色向黑色收敛），
    并用 BLEND_RGB_ADD 叠加，得到真实的柔和辉光。
    """
    size = radius * 2
    surface = pygame.Surface((size, size))

    r, g, b = color
    cx = cy = radius
    inv_r = 1.0 / radius
    peak = max(0.0, min(1.0, inner_alpha / 255.0))

    for y in range(size):
        dy = y - cy
        for x in range(size):
            dx = x - cx
            dist2 = dx * dx + dy * dy
            if dist2 > radius * radius:
                continue
            t = math.sqrt(dist2) * inv_r
            # 中心也不给满（留叠加空间），边缘快速归零
            strength = peak * ((1.0 - t) ** falloff) * (1.0 - 0.55 * t)
            if strength <= 0.002:
                continue
            surface.set_at((x, y), (
                int(r * strength),
                int(g * strength),
                int(b * strength),
            ))
    return surface


def make_soft_dot(radius: int, color: Color, alpha: int = 255) -> pygame.Surface:
    """预渲染一个柔和圆点（additive 用，衰减写在 RGB 里）。"""
    return make_radial_glow(radius, color, inner_alpha=alpha, falloff=1.6)


# ==================== 背景 ====================

class StarField:
    """缓存式深空背景。

    一次性生成渐变 + 星点 + 星云光晕，之后每帧只 blit。
    星点分三层（远/中/近），带不同亮度，制造视差感。
    """

    def __init__(self, width: int, height: int, seed: int = 20261119):
        self.width = width
        self.height = height
        self._seed = seed
        self._surface: Optional[pygame.Surface] = None

    def _build(self) -> pygame.Surface:
        rng = random.Random(self._seed)
        surf = pygame.Surface((self.width, self.height)).convert()

        # 1. 垂直渐变：BG_TOP -> BG_MID -> BG_BOTTOM
        mid = self.height // 2
        for y in range(self.height):
            if y < mid:
                t = y / max(1, mid)
                color = lerp_color(BG_TOP, BG_MID, t)
            else:
                t = (y - mid) / max(1, self.height - mid)
                color = lerp_color(BG_MID, BG_BOTTOM, t)
            pygame.draw.line(surf, color, (0, y), (self.width, y))

        # 2. 星云光晕（大块柔和色斑，制造纵深）
        # ⚠️ 用 SRCALPHA + BLEND_RGB_ADD 时，alpha=0 区域的 RGB(0,0,0) 仍会被加进去
        #    （ADD 忽略 alpha），导致背景出现矩形色块。
        #    正确做法：直接用不带 alpha 的 RGB 衰减贴图叠加。
        nebula = pygame.Surface((self.width, self.height))
        for _ in range(5):
            cx = rng.randint(-40, self.width + 40)
            cy = rng.randint(0, self.height)
            rad = rng.randint(160, 300)
            tint = rng.choice([NEBULA_A, NEBULA_B])
            glow = make_radial_glow(rad, tint, inner_alpha=46, falloff=2.6)
            nebula.blit(glow, (cx - rad, cy - rad), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(nebula, (0, 0))

        # 3. 星点三层
        layers = (
            # (数量, 半径范围, 亮度范围)
            (420, (0, 1), (60, 115)),
            (150, (1, 2), (110, 180)),
            (46, (1, 3), (190, 255)),
        )
        for count, (r0, r1), (b0, b1) in layers:
            for _ in range(count):
                x = rng.randint(0, self.width)
                y = rng.randint(0, self.height)
                rad = rng.randint(r0, r1)
                brightness = rng.randint(b0, b1)
                tint = rng.choice([(255, 255, 255), (190, 220, 255), (255, 210, 240)])
                color = lerp_color(tint, (0, 0, 0), 1.0 - brightness / 255.0)
                if rad <= 1:
                    surf.set_at((x, y), color)
                else:
                    pygame.draw.circle(surf, color, (x, y), rad)

        # 4. 少量十字星芒（近景亮点）
        for _ in range(16):
            x = rng.randint(10, self.width - 10)
            y = rng.randint(10, self.height - 10)
            arm = rng.randint(4, 8)
            c = (235, 245, 255)
            pygame.draw.line(surf, c, (x - arm, y), (x + arm, y), 1)
            pygame.draw.line(surf, c, (x, y - arm), (x, y + arm), 1)

        return surf

    def get_surface(self) -> pygame.Surface:
        """取得（必要时构建）背景缓存"""
        if self._surface is None:
            self._surface = self._build()
        return self._surface

    def draw(self, target: pygame.Surface) -> None:
        """绘制背景到目标 surface"""
        target.blit(self.get_surface(), (0, 0))


# ==================== 粒子系统 ====================

class Particle:
    """单个粒子：位置、速度、生命周期、颜色、尺寸。"""

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "drag")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        color: Color,
        size: float,
        drag: float = 0.92,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.drag = drag

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float) -> None:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # 阻尼衰减
        d = self.drag ** (dt * 60.0)
        self.vx *= d
        self.vy *= d


class ParticleSystem:
    """粒子池（上限保护，避免性能抖动）。"""

    MAX_PARTICLES = 600

    def __init__(self, max_particles: int = MAX_PARTICLES):
        self.max_particles = max_particles
        self.particles: List[Particle] = []
        self._dot_cache: dict = {}
        # 亮度档位（用于粒子淡出，避免逐帧 fill）
        self._dim_levels = (1.0, 0.7, 0.45, 0.25, 0.12)

    def _dot(self, radius: int, color: Color, level: float = 1.0) -> pygame.Surface:
        """取得（必要时构建）粒子贴图。

        ⚠️ 关键：粒子用 BLEND_RGB_ADD 叠加，而 ADD **忽略 alpha 通道**。
        如果用带 alpha 的 SRCALPHA 贴图，整张方形区域（含透明像素）
        都会以满强度加到屏幕上 —— 表现为满屏彩色方块。

        因此粒子贴图必须是**不带 alpha 的 RGB 衰减贴图**，
        亮度档位直接烘焙进 RGB 值里。
        """
        key = (radius, color, level)
        if key not in self._dot_cache:
            self._dot_cache[key] = make_radial_glow(
                radius, color, inner_alpha=int(255 * level), falloff=1.6
            )
        return self._dot_cache[key]

    def spawn(self, particle: Particle) -> None:
        if len(self.particles) >= self.max_particles:
            self.particles.pop(0)
        self.particles.append(particle)

    def clear(self) -> None:
        self.particles.clear()

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, target: pygame.Surface) -> None:
        """绘制粒子（additive 混合，营造辉光）

        ⚠️ 不能用 faded.fill((k,k,k), BLEND_RGB_MULT) 做淡出 ——
        fill() 会把整张 surface 压暗（包括透明区域），
        导致粒子变成实心方块。正确做法：预渲染多个亮度档位。
        """
        for p in self.particles:
            t = p.life / p.max_life if p.max_life > 0 else 0.0
            if t <= 0.05:
                continue
            rad = max(1, int(p.size * (0.35 + 0.65 * t)))
            # 按亮度档位选预渲染贴图（避免逐帧 fill）
            level = min(len(self._dim_levels) - 1, int(t * len(self._dim_levels)))
            dot = self._dot(rad, p.color, self._dim_levels[level])
            target.blit(dot, (int(p.x) - rad, int(p.y) - rad), special_flags=pygame.BLEND_RGB_ADD)


# ==================== 预渲染发光资源 ====================

class GlowAssets:
    """所有预渲染发光贴图的集中缓存。

    避免每帧重复生成（生成一次成本不低）。
    """

    def __init__(self):
        self._cache: dict = {}

    def bullet_glow(self, radius: int) -> pygame.Surface:
        """子弹外发光（青→紫渐层）"""
        key = ("bullet", radius)
        if key not in self._cache:
            glow = make_radial_glow(int(radius * 3.0), BULLET_MID, inner_alpha=95, falloff=2.8)
            self._cache[key] = glow
        return self._cache[key]
    def bullet_core(self, radius: int) -> pygame.Surface:
        """子弹核心（白色实心 + 青边）"""
        key = ("core", radius)
        if key not in self._cache:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, BULLET_MID, (radius, radius), radius)
            pygame.draw.circle(surf, BULLET_CORE, (radius, radius), max(1, int(radius * 0.62)))
            self._cache[key] = surf
        return self._cache[key]

    def bullet_core_danger(self, radius: int) -> pygame.Surface:
        """子弹核心（危险模式：红色版）

        ⚠️ 必须预渲染成独立贴图，不能用 fill()+BLEND_RGBA_ADD 就地改色 ——
        fill() 不区分 alpha=0 的区域，ADD 混合下会炸出整片色块。
        """
        key = ("core_danger", radius)
        if key not in self._cache:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (150, 30, 30), (radius, radius), radius)
            pygame.draw.circle(surf, CORAL, (radius, radius), max(1, int(radius * 0.62)))
            pygame.draw.circle(surf, (255, 235, 235), (radius, radius), max(1, int(radius * 0.3)))
            self._cache[key] = surf
        return self._cache[key]

    def engine_flame(self, size: int) -> pygame.Surface:
        """引擎尾焰（青芯 + 紫边，向上收窄）"""
        key = ("flame", size)
        if key not in self._cache:
            w = size
            h = int(size * 2.2)
            surf = pygame.Surface((w, h))
            # 多层椭圆叠出渐变感（衰减写在 RGB 里，避免 ADD 忽略 alpha 的色块问题）
            for alpha, shrink, color in [
                (70, 1.00, BULLET_EDGE),
                (120, 0.62, BULLET_MID),
                (220, 0.28, (220, 255, 255)),
            ]:
                ew = max(1, int(w * shrink))
                eh = max(1, int(h * shrink))
                layer = pygame.Surface((ew, eh))
                k = alpha / 255.0
                pygame.draw.ellipse(layer, (
                    int(color[0] * k), int(color[1] * k), int(color[2] * k),
                ), layer.get_rect())
                surf.blit(layer, ((w - ew) // 2, h - eh), special_flags=pygame.BLEND_RGB_ADD)
            self._cache[key] = surf
        return self._cache[key]

    def ring(self, radius: int, color: Color, width: int = 3) -> pygame.Surface:
        """冲击波圆环"""
        key = ("ring", radius, color, width)
        if key not in self._cache:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (radius, radius), radius, width)
            self._cache[key] = surf
        return self._cache[key]


# ==================== 飞船绘制 ====================

class ShipRenderer:
    """玩家飞船渲染器（深空赛博风格）。

    组成：
    - 护盾光环（呼吸脉动）
    - 引擎尾焰（additive）
    - 船体（分层多边形，带高光与暗部）
    - 座舱（发光）
    """

    def __init__(self, assets: GlowAssets):
        self.assets = assets
        self._hull_cache: Optional[pygame.Surface] = None
        self._hull_size = 0

    def _build_hull(self, size: int = 40) -> pygame.Surface:
        """预渲染船体（离屏画一次，之后 blit + 旋转/缩放）。

        使用 4x 超采样后缩小，得到平滑边缘。
        """
        scale = 4  # 超采样倍数
        s = size * scale
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        cx = cy = s // 2
        u = s / 40.0  # 单位缩放（相对 PLAYER_SIZE=40 的设计稿）

        def poly(points, color):
            pygame.draw.polygon(surf, color, [(cx + px * u, cy + py * u) for px, py in points])

        # 尾翼（暗部，压在机身后）
        poly([(-13, 12), (-19, 25), (-5, 23)], SHIP_DARK)
        poly([(13, 12), (19, 25), (5, 23)], SHIP_DARK)

        # 主翼（主体色）
        poly([(-7, -4), (-29, 11), (-29, 19), (-7, 8)], SHIP_BODY)
        poly([(7, -4), (29, 11), (29, 19), (7, 8)], SHIP_BODY)

        # 机身主体
        poly([(0, -25), (-7, -11), (-7, 19), (7, 19), (7, -11)], SHIP_BODY)

        # 机身高光条（左侧受光）
        poly([(0, -25), (-7, -11), (-7, 5), (-2, -3)], SHIP_HULL)

        # 座舱（发光）
        cockpit = pygame.Surface((s, s), pygame.SRCALPHA)
        pygame.draw.ellipse(cockpit, (*SHIP_COCKPIT, 235), (cx - 3.2 * u, cy - 9 * u, 6.4 * u, 13 * u))
        surf.blit(cockpit, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # 座舱高光点
        pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy - 5 * u)), max(1, int(1.4 * u)))

        # 细描边，提升轮廓清晰度
        pygame.draw.polygon(
            surf, (235, 250, 255),
            [(cx + px * u, cy + py * u) for px, py in
             [(0, -25), (-7, -11), (-7, 19), (7, 19), (7, -11)]],
            max(1, int(u * 0.8)),
        )

        # 缩小回目标尺寸（抗锯齿）
        return pygame.transform.smoothscale(surf, (size, size))

    def _get_hull(self, size: int) -> pygame.Surface:
        """取得（必要时构建）船体贴图，按尺寸缓存。"""
        if self._hull_cache is None or self._hull_size != size:
            self._hull_cache = self._build_hull(size)
            self._hull_size = size
        return self._hull_cache

    def draw(
        self,
        target: pygame.Surface,
        cx: int,
        cy: int,
        time: float = 0.0,
        engine_intensity: float = 1.0,
        shield: bool = False,
    ) -> None:
        """绘制飞船到 target。

        Args:
            time: 全局时间（用于脉动动画）
            engine_intensity: 引擎强度 0~1
            shield: 是否显示护盾光环
        """
        # 1. 护盾光环（呼吸脉动）
        if shield:
            pulse = 0.5 + 0.5 * math.sin(time * 3.2)
            ring_r = 30 + int(pulse * 4)
            ring = self.assets.ring(ring_r, CYAN, 2)
            ring_alpha = ring.copy()
            ring_alpha.set_alpha(int(40 + 45 * pulse))
            target.blit(ring_alpha, (cx - ring_r, cy - ring_r), special_flags=pygame.BLEND_RGB_ADD)

        # 2. 引擎尾焰（additive，画在机身下方）
        flame_size = max(6, int(9 * engine_intensity))
        flame = self.assets.engine_flame(flame_size)
        flame_alpha = flame.copy()
        flicker = 0.75 + 0.25 * math.sin(time * 24.0)
        flame_alpha.set_alpha(int(160 * engine_intensity * flicker))
        # 尾焰向下延伸（机头朝上）
        target.blit(flame_alpha, (cx - flame_size // 2, cy + 17), special_flags=pygame.BLEND_RGB_ADD)

        # 3. 船体
        hull = self._get_hull(40)
        hw, hh = hull.get_size()
        target.blit(hull, (cx - hw // 2, cy - hh // 2))

        # 4. 座舱外辉光（柔和，衰减已写在 RGB 里，不再叠加 set_alpha）
        glow = make_radial_glow(15, SHIP_COCKPIT, inner_alpha=70, falloff=2.8)
        target.blit(glow, (cx - 15, cy - 15), special_flags=pygame.BLEND_RGB_ADD)


# ==================== 子弹渲染 ====================

class BulletRenderer:
    """子弹渲染器：拖尾残影 + 外发光 + 发光核心。"""

    def __init__(self, assets: GlowAssets):
        self.assets = assets
        self._trail_cache: dict = {}

    def _trail_strip(self, radius: int, danger: bool = False) -> pygame.Surface:
        """预渲染拖尾（沿 -x 方向的尖尾导弹迹）。

        ⚠️ 关键约束：additive 混合（BLEND_RGB_ADD）**忽略 alpha 通道**，
        所以辉光类贴图必须把衰减写进 RGB，不能用 alpha。
        否则整张贴图会以满强度叠加，变成实心色块。

        ⚠️ 拖尾朝向随速度方向变化，不能直接 rotate 这个非正方形贴图 ——
        pygame.transform.rotate 会把结果裁剪回原始尺寸，尖尾会被切成硬边楔形。
        正确做法：预渲染一张「正方形 + 以中心为轴向」的贴图，
        再用 rotozoom 缩放并旋转（正方形旋转不会裁剪）。

        ⚠️ 危险模式必须**预渲染成独立贴图**，不能事后用 fill() 改色 ——
        fill() 会把整张方图的黑色像素也填成红色，ADD 叠加后就是满屏红方块。
        """
        key = (radius, danger)
        if key not in self._trail_cache:
            # 正方形画布，尾迹沿 -x 延伸，尖端在左端
            size = radius * 6
            surf = pygame.Surface((size, size))
            half = size // 2
            base = CORAL if danger else BULLET_MID
            r, g, b = base
            for x in range(size):
                # 从尾尖(0)到头部(size)：宽度由尖变宽
                t = x / (size - 1)
                if t <= 0.0:
                    continue
                width = radius * (0.12 + 0.88 * t)
                along = 105 * (t ** 1.9)
                if along <= 1.5:
                    continue
                for y in range(half - radius - 1, half + radius + 2):
                    dy = abs(y - half)
                    if dy > width:
                        continue
                    # 纵向柔化 + 沿长度衰减，都写进 RGB
                    k = (along / 255.0) * ((1.0 - dy / max(0.01, width)) ** 1.3)
                    if k <= 0.004:
                        continue
                    surf.set_at((x, y), (int(r * k), int(g * k), int(b * k)))
            self._trail_cache[key] = surf
        return self._trail_cache[key]

    def draw(
        self,
        target: pygame.Surface,
        x: int,
        y: int,
        vx: float,
        vy: float,
        radius: int,
        danger: bool = False,
    ) -> None:
        """绘制单颗子弹。

        Args:
            danger: 终局模式 —— 转为珊瑚红警告色
        """
        # 1. 拖尾（朝向运动方向的反向）
        speed = math.hypot(vx, vy)
        if speed > 1.0:
            angle = math.atan2(vy, vx)
            trail = self._trail_strip(radius, danger)
            # 正方形贴图旋转不会裁剪
            trail_rot = pygame.transform.rotozoom(trail, -math.degrees(angle), 1.0)
            target.blit(
                trail_rot,
                (x - trail_rot.get_width() // 2, y - trail_rot.get_height() // 2),
                special_flags=pygame.BLEND_RGB_ADD,
            )

        # 2. 外发光（柔和，不可饱和成实心盘）
        if danger:
            glow = make_radial_glow(int(radius * 3.0), CORAL, inner_alpha=110, falloff=2.8)
        else:
            glow = self.assets.bullet_glow(radius)
        target.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2),
                    special_flags=pygame.BLEND_RGB_ADD)

        # 3. 核心
        core = self.assets.bullet_core(radius)
        if danger:
            # ⚠️ 不能用 core.fill((r,g,b,0), BLEND_RGBA_ADD) 改色 ——
            #    fill() 会作用到整张 surface（包括 alpha=0 的区域），
            #    配合 ADD 混合会在屏幕上炸出满屏色块。
            #    正确做法：预渲染一张红色版本的核心贴图。
            core = self.assets.bullet_core_danger(radius)
        target.blit(core, (x - radius, y - radius))


# ==================== HUD ====================

class HUD:
    """游戏内 HUD：倒计时面板 + 进度条 + 生存计时。"""

    def __init__(self, fonts: dict):
        self.fonts = fonts

    def draw(
        self,
        target: pygame.Surface,
        screen_w: int,
        remaining: float,
        progress: float,
        elapsed: float,
        time: float,
        finished: bool = False,
        dim: bool = False,
    ) -> None:
        """绘制顶部 HUD 面板。

        Args:
            finished: 已通关 —— 隐藏倒计时，改为显示达成状态（避免显示 0.0）
            dim: 结算中 —— 整体降低透明度，避免与弹窗抢视觉重心
        """
        panel_w, panel_h = 190, 74
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.centerx = screen_w // 2
        panel.y = 14

        # 面板背景（半透明 + 描边）
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, PANEL_BG, bg.get_rect(), border_radius=14)
        if dim:
            bg.set_alpha(110)
        target.blit(bg, panel.topleft)

        # 描边：临近结束转珊瑚红并脉动；通关后转绿
        if finished:
            edge = (120, 255, 170, 180)
        elif remaining <= 10.0:
            pulse = 0.55 + 0.45 * math.sin(time * 7.0)
            edge = (*CORAL, int(90 + 150 * pulse))
            glow = make_radial_glow(int(panel_w * 0.75), CORAL, inner_alpha=int(40 * pulse), falloff=2.6)
            target.blit(glow, (panel.centerx - glow.get_width() // 2, panel.centery - glow.get_height() // 2),
                        special_flags=pygame.BLEND_RGB_ADD)
        else:
            edge = PANEL_EDGE
        pygame.draw.rect(target, edge, panel, 1, border_radius=14)

        # 主数字（通关后显示「达成」，否则显示倒计时）
        if finished:
            num_color = LIME
            num_surf = self.fonts["body"].render("达成 100s", True, num_color)
        else:
            num_color = CORAL if remaining <= 10.0 else CYAN
            num_surf = self.fonts["countdown"].render(f"{remaining:.1f}", True, num_color)
        num_rect = num_surf.get_rect(center=(panel.centerx, panel.y + 28))
        target.blit(num_surf, num_rect)

        if not finished:
            # 单位「秒」
            unit_surf = self.fonts["caption"].render("秒", True, TEXT_DIM)
            target.blit(unit_surf, (num_rect.right + 5, num_rect.centery - 10))

        # 进度条
        bar_w = panel_w - 36
        bar_h = 6
        bar = pygame.Rect(0, 0, bar_w, bar_h)
        bar.centerx = panel.centerx
        bar.y = panel.bottom - 18

        pygame.draw.rect(target, (38, 44, 78), bar, border_radius=3)
        fill_w = int(bar_w * max(0.0, min(1.0, progress)))
        if fill_w > 0:
            fill = pygame.Rect(0, 0, fill_w, bar_h)
            fill.midleft = (bar.left, bar.centery)
            bar_color = LIME if finished else (CORAL if remaining <= 10.0 else CYAN)
            pygame.draw.rect(target, bar_color, fill, border_radius=3)
            # 进度条头部辉光
            head = make_radial_glow(9, bar_color, inner_alpha=140, falloff=2.4)
            target.blit(head, (fill.right - 9, bar.centery - 9), special_flags=pygame.BLEND_RGB_ADD)

        # 左侧：存活计时
        elapsed_surf = self.fonts["caption"].render(f"存活 {elapsed:.1f}s", True, TEXT_MID)
        target.blit(elapsed_surf, (panel.left - elapsed_surf.get_width() - 14, panel.y + 30))
