"""
macOS / PC 版本入口

运行方式：
    python -m mac.main
或：
    cd ~/Desktop/project/是男人就100
    python mac/main.py
"""
from mac.ui import GameUI


def main() -> None:
    ui = GameUI()
    ui.run()


if __name__ == "__main__":
    main()