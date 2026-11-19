"""无头渲染预览工具：把各 UI 状态渲染成 PNG，便于离线检查视觉效果。

用法：
    SDL_VIDEODRIVER=dummy python3 tools/preview.py [输出目录]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402
import random  # noqa: E402

from mac.ui import GameUI  # noqa: E402
from core.game_state import GameState  # noqa: E402


def save(ui: GameUI, name: str, outdir: Path) -> None:
    ui._render()
    path = outdir / f"{name}.png"
    pygame.image.save(ui.screen, str(path))
    print("saved:", path.name)


def main() -> None:
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "preview")
    outdir.mkdir(parents=True, exist_ok=True)

    ui = GameUI()

    # 1. 菜单（空榜）
    ui._ui_state = "menu"
    save(ui, "01_menu_empty", outdir)

    # 2. 菜单（有榜）
    ui.leaderboard.add_entry("小明", 92.4)
    ui.leaderboard.add_entry("阿强", 67.8)
    ui.leaderboard.add_entry("匿名", 45.1)
    ui.leaderboard.add_entry("Luna", 23.6)
    ui.leaderboard.add_entry("老王", 8.2)
    save(ui, "02_menu_leaderboard", outdir)

    # 3. 游戏进行中
    ui._ui_state = "playing"
    ui.game.start()
    for _ in range(200):
        ui.game.update(1 / 60)
    ui.game.move_player_to(200, 620)
    save(ui, "03_playing", outdir)

    # 4. 终局（>80s 红色警告）
    ui.game.elapsed_time = 87.5
    save(ui, "04_playing_late", outdir)

    # 5. 失败弹窗
    ui._ui_state = "gameover"
    ui.game.state = GameState.GAME_OVER
    ui.game.elapsed_time = 67.8
    ui._submitted_rank = None
    save(ui, "05_gameover", outdir)

    # 6. 胜利弹窗
    ui._ui_state = "victory"
    ui.game.state = GameState.VICTORY
    ui.game.elapsed_time = 100.0
    ui._submitted_rank = None
    save(ui, "06_victory", outdir)

    # 7. 名字输入
    ui._ui_state = "name_input"
    ui._name_input = "测试员"
    save(ui, "07_name_input", outdir)

    pygame.quit()
    print(f"\nall screenshots -> {outdir.resolve()}")


if __name__ == "__main__":
    main()
