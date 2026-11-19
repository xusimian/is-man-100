"""深空赛博风格视觉效果预览（独立于 mac/ui.py）。

用法：
    SDL_VIDEODRIVER=dummy python3 tools/preview_cyber.py [输出目录]

用途：在整合进正式 UI 之前，先单独验证视觉系统本身的观感。
"""
from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from mac import visuals as V  # noqa: E402

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if not Path(FONT_PATH).exists():
    FONT_PATH = None


def make_fonts() -> dict:
    if FONT_PATH:
        base = pygame.font.Font(FONT_PATH, 24)
        return {
            "display": pygame.font.Font(FONT_PATH, 56),
            "title": pygame.font.Font(FONT_PATH, 36),
            "countdown": pygame.font.Font(FONT_PATH, 60),
            "body": pygame.font.Font(FONT_PATH, 22),
            "callout": pygame.font.Font(FONT_PATH, 18),
            "caption": pygame.font.Font(FONT_PATH, 14),
        }
    d = pygame.font.get_default_font()
    return {k: pygame.font.Font(d, s) for k, s in [
        ("display", 56), ("title", 36), ("countdown", 60),
        ("body", 22), ("callout", 18), ("caption", 14),
    ]}


def main() -> None:
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "preview_cyber")
    outdir.mkdir(parents=True, exist_ok=True)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    fonts = make_fonts()

    starfield = V.StarField(SCREEN_WIDTH, SCREEN_HEIGHT)
    assets = V.GlowAssets()
    ship = V.ShipRenderer(assets)
    bullets = V.BulletRenderer(assets)
    particles = V.ParticleSystem()
    hud = V.HUD(fonts)

    t = 0.0

    def draw_bg():
        starfield.draw(screen)

    # ---------- 1. 游戏画面（子弹 + 飞船 + HUD） ----------
    draw_bg()
    rng = random.Random(7)
    for _ in range(26):
        x = rng.randint(20, SCREEN_WIDTH - 20)
        y = rng.randint(120, SCREEN_HEIGHT - 20)
        ang = rng.uniform(0, math.tau)
        spd = rng.uniform(40, 150)
        bullets.draw(screen, x, y, math.cos(ang) * spd, math.sin(ang) * spd, 8)

    ship.draw(screen, SCREEN_WIDTH // 2, 620, time=t, engine_intensity=1.0, shield=True)
    hud.draw(screen, SCREEN_WIDTH, remaining=62.4, progress=0.376, elapsed=37.6, time=t)
    pygame.image.save(screen, str(outdir / "cyber_01_playing.png"))

    # ---------- 2. 终局（红色警告） ----------
    draw_bg()
    for _ in range(26):
        x = rng.randint(20, SCREEN_WIDTH - 20)
        y = rng.randint(120, SCREEN_HEIGHT - 20)
        ang = rng.uniform(0, math.tau)
        spd = rng.uniform(40, 150)
        bullets.draw(screen, x, y, math.cos(ang) * spd, math.sin(ang) * spd, 8, danger=True)
    ship.draw(screen, SCREEN_WIDTH // 2, 620, time=t, engine_intensity=1.0, shield=True)
    hud.draw(screen, SCREEN_WIDTH, remaining=8.3, progress=0.917, elapsed=91.7, time=t)
    pygame.image.save(screen, str(outdir / "cyber_02_danger.png"))

    # ---------- 3. 菜单 ----------
    draw_bg()
    title = fonts["display"].render("是男人就100", True, V.TEXT_HI)
    # 标题辉光：柔和、低 alpha，不能糊成圆盘
    glow = V.make_radial_glow(150, V.CYAN, inner_alpha=42, falloff=3.0)
    screen.blit(glow, (SCREEN_WIDTH // 2 - 150, 150 - 150), special_flags=pygame.BLEND_RGB_ADD)
    tr = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
    screen.blit(title, tr)

    sub = fonts["callout"].render("撑过 100 秒 证明自己", True, V.TEXT_MID)
    screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 205)))

    ship.draw(screen, SCREEN_WIDTH // 2, 330, time=t, engine_intensity=1.0, shield=True)

    # 排行榜面板
    panel = pygame.Rect(24, 400, SCREEN_WIDTH - 48, 300)
    bg = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(bg, V.PANEL_BG, bg.get_rect(), border_radius=18)
    screen.blit(bg, panel.topleft)
    pygame.draw.rect(screen, V.PANEL_EDGE, panel, 1, border_radius=18)

    hd = fonts["body"].render("排行榜 · TOP 5", True, V.CYAN)
    screen.blit(hd, (panel.x + 20, panel.y + 16))

    entries = [("小明", 92.4), ("阿强", 67.8), ("匿名", 45.1), ("Luna", 23.6), ("老王", 8.2)]
    for i, (name, tm) in enumerate(entries):
        y = panel.y + 62 + i * 46
        medal_color = [V.AMBER, (200, 205, 220), (205, 130, 70)][i] if i < 3 else V.TEXT_DIM
        pygame.draw.circle(screen, medal_color, (panel.x + 34, y + 12), 13)
        num = fonts["caption"].render(str(i + 1), True, (20, 20, 30))
        screen.blit(num, num.get_rect(center=(panel.x + 34, y + 12)))
        nc = V.AMBER if i == 0 else V.TEXT_HI
        screen.blit(fonts["body"].render(name, True, nc), (panel.x + 62, y))
        ts = fonts["body"].render(f"{tm:.1f}s", True, nc)
        screen.blit(ts, ts.get_rect(midright=(panel.right - 20, y + 12)))
        if i < len(entries) - 1:
            pygame.draw.line(screen, (40, 48, 82), (panel.x + 20, y + 38), (panel.right - 20, y + 38), 1)

    # 开始按钮（霓虹青胶囊）
    btn = pygame.Rect(0, 0, 240, 58)
    btn.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62)
    bglow = V.make_radial_glow(80, V.CYAN, inner_alpha=38, falloff=3.0)
    screen.blit(bglow, (btn.centerx - 80, btn.centery - 80), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.rect(screen, V.CYAN, btn, border_radius=29)
    bt = fonts["body"].render("开始挑战", True, (5, 15, 30))
    screen.blit(bt, bt.get_rect(center=btn.center))
    pygame.image.save(screen, str(outdir / "cyber_03_menu.png"))

    # ---------- 4. 失败弹窗 ----------
    draw_bg()
    ship.draw(screen, SCREEN_WIDTH // 2, 620, time=t, engine_intensity=0.4, shield=True)
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    # 爆散粒子
    for _ in range(40):
        ang = rng.uniform(0, math.tau)
        spd = rng.uniform(60, 320)
        particles.spawn(V.Particle(
            SCREEN_WIDTH // 2, 400, math.cos(ang) * spd, math.sin(ang) * spd,
            rng.uniform(0.4, 1.0), rng.choice([V.CYAN, V.MAGENTA, V.VIOLET]),
            rng.uniform(2, 5),
        ))
    for _ in range(12):
        particles.update(1 / 60)
    particles.draw(screen)

    cx, cy = SCREEN_WIDTH // 2, 240
    pygame.draw.circle(screen, V.CORAL, (cx, cy), 36)
    pygame.draw.line(screen, (255, 255, 255), (cx - 14, cy - 14), (cx + 14, cy + 14), 4)
    pygame.draw.line(screen, (255, 255, 255), (cx + 14, cy - 14), (cx - 14, cy + 14), 4)
    t1 = fonts["title"].render("挑战失败", True, V.TEXT_HI)
    screen.blit(t1, t1.get_rect(center=(SCREEN_WIDTH // 2, 320)))
    t2 = fonts["countdown"].render("67.8", True, V.CORAL)
    screen.blit(t2, t2.get_rect(center=(SCREEN_WIDTH // 2, 380)))
    t3 = fonts["body"].render("新纪录！输入名字上榜", True, V.AMBER)
    screen.blit(t3, t3.get_rect(center=(SCREEN_WIDTH // 2, 440)))

    box = pygame.Rect(0, 0, SCREEN_WIDTH - 64, 56)
    box.center = (SCREEN_WIDTH // 2, 498)
    bg2 = pygame.Surface(box.size, pygame.SRCALPHA)
    pygame.draw.rect(bg2, (28, 32, 66, 255), bg2.get_rect(), border_radius=12)
    screen.blit(bg2, box.topleft)
    pygame.draw.rect(screen, V.CYAN, box, 2, border_radius=12)
    ph = fonts["body"].render("点击输入名字...", True, V.TEXT_DIM)
    screen.blit(ph, ph.get_rect(center=box.center))

    rbtn = pygame.Rect(0, 0, 200, 52)
    rbtn.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 82)
    pygame.draw.rect(screen, V.CYAN, rbtn, border_radius=26)
    rt = fonts["body"].render("再来一次", True, (5, 15, 30))
    screen.blit(rt, rt.get_rect(center=rbtn.center))
    pygame.image.save(screen, str(outdir / "cyber_04_gameover.png"))

    # ---------- 5. 胜利弹窗 ----------
    draw_bg()
    overlay2 = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay2.fill((0, 0, 0, 150))
    screen.blit(overlay2, (0, 0))

    # 胜利粒子爆发
    for _ in range(70):
        ang = rng.uniform(0, math.tau)
        spd = rng.uniform(80, 380)
        particles.spawn(V.Particle(
            SCREEN_WIDTH // 2, 300, math.cos(ang) * spd, math.sin(ang) * spd,
            rng.uniform(0.6, 1.4), rng.choice([V.LIME, V.CYAN, V.AMBER]),
            rng.uniform(2, 6),
        ))
    for _ in range(20):
        particles.update(1 / 60)
    particles.draw(screen)

    # 五角星
    cx, cy = SCREEN_WIDTH // 2, 250
    star = []
    for i in range(10):
        ang = math.pi / 5 * i - math.pi / 2
        r = 38 if i % 2 == 0 else 16
        star.append((int(cx + math.cos(ang) * r), int(cy + math.sin(ang) * r)))
    sglow = V.make_radial_glow(75, V.LIME, inner_alpha=55, falloff=2.8)
    screen.blit(sglow, (cx - 75, cy - 75), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.polygon(screen, V.LIME, star)

    t1 = fonts["title"].render("是男人！", True, V.LIME)
    screen.blit(t1, t1.get_rect(center=(SCREEN_WIDTH // 2, 330)))
    t2 = fonts["countdown"].render("100.0", True, V.LIME)
    screen.blit(t2, t2.get_rect(center=(SCREEN_WIDTH // 2, 390)))
    t3 = fonts["body"].render("完美通关", True, V.TEXT_MID)
    screen.blit(t3, t3.get_rect(center=(SCREEN_WIDTH // 2, 430)))
    pygame.image.save(screen, str(outdir / "cyber_05_victory.png"))

    pygame.quit()
    print(f"saved -> {outdir.resolve()}")
    for p in sorted(outdir.glob("*.png")):
        print("  ", p.name)


if __name__ == "__main__":
    main()
