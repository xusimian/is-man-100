"""
macOS / PC 版本入口

✅ 推荐运行方式（从项目根目录）：
    python3 -m mac.main

❌ 不要这样跑（会报 ModuleNotFoundError）：
    python3 mac/main.py
"""
from mac.ui import GameUI


def main() -> None:
    ui = GameUI()
    ui.run()


if __name__ == "__main__":
    main()