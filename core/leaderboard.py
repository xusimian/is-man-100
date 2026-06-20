"""
高分榜管理

保存到用户目录的 JSON 文件，跨平台通用。
"""
from __future__ import annotations  # 兼容 Python 3.9

import json
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


# 最多保存多少条记录
MAX_ENTRIES = 5


def _get_save_path() -> Path:
    """获取高分榜文件的保存路径（跨平台）"""
    system = platform.system()
    if system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:  # Linux / 其他
        base = Path.home() / ".local" / "share"
    save_dir = base / "IsMan100"
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / "leaderboard.json"


class Leaderboard:
    """高分榜管理器"""

    def __init__(self, save_path: Optional[Path] = None):
        self.save_path = save_path or _get_save_path()
        self.entries: List[Dict] = []
        self._load()

    def _load(self) -> None:
        """从文件加载榜单"""
        if self.save_path.exists():
            try:
                with open(self.save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entries = data.get("entries", [])[:MAX_ENTRIES]
            except (json.JSONDecodeError, IOError):
                self.entries = []

    def _save(self) -> None:
        """保存到文件"""
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump({"entries": self.entries[:MAX_ENTRIES]}, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # 静默失败，不影响游戏

    def add_entry(self, name: str, survival_time: float) -> int:
        """添加一条记录，返回插入后的排名（1-based，0 表示未上榜）

        Args:
            name: 玩家名字
            survival_time: 存活时间（秒）

        Returns:
            1-5 表示上榜名次，0 表示未进入 Top 5
        """
        entry = {
            "name": name.strip() or "匿名",
            "time": round(float(survival_time), 2),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        # 找到插入位置（按 time 倒序）
        self.entries.append(entry)
        # 按时间倒序
        self.entries.sort(key=lambda e: e["time"], reverse=True)
        # 保留前 5
        self.entries = self.entries[:MAX_ENTRIES]
        self._save()

        # 返回名次：用时间匹配（避免字典对象比较）
        for idx, e in enumerate(self.entries, start=1):
            if (e["name"] == entry["name"]
                    and e["time"] == entry["time"]
                    and e["date"] == entry["date"]):
                return idx
        return 0

    def is_high_score(self, survival_time: float) -> bool:
        """判断某个分数是否值得上榜

        0 秒（即时死亡）不视为上榜分数，避免空榜时玩家还没开始就被
        提示输入名字。
        """
        if survival_time <= 0.0:
            return False
        if len(self.entries) < MAX_ENTRIES:
            return True
        return survival_time > self.entries[-1]["time"]

    def clear(self) -> None:
        """清空榜单"""
        self.entries = []
        self._save()

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)