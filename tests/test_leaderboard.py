"""
测试高分榜管理
"""
import unittest
import tempfile
import json
from pathlib import Path
from core.leaderboard import Leaderboard


class TestLeaderboard(unittest.TestCase):

    def setUp(self):
        """每个测试用临时文件"""
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        self.tmp_path = Path(self.tmp.name)
        self.tmp.close()
        self.lb = Leaderboard(save_path=self.tmp_path)

    def tearDown(self):
        if self.tmp_path.exists():
            self.tmp_path.unlink()

    def test_empty_leaderboard(self):
        self.assertEqual(len(self.lb), 0)

    def test_add_entry(self):
        self.lb.add_entry("Tony", 50.5)
        self.assertEqual(len(self.lb), 1)

    def test_add_entry_default_name(self):
        """空名字应变成"匿名" """
        self.lb.add_entry("", 30.0)
        self.assertEqual(self.lb.entries[0]["name"], "匿名")
        self.lb.add_entry("   ", 30.0)
        self.assertEqual(self.lb.entries[1]["name"], "匿名")

    def test_entries_sorted_descending(self):
        """条目应按时间倒序"""
        self.lb.add_entry("Alice", 30.0)
        self.lb.add_entry("Bob", 70.0)
        self.lb.add_entry("Carol", 50.0)
        self.assertEqual(self.lb.entries[0]["name"], "Bob")
        self.assertEqual(self.lb.entries[1]["name"], "Carol")
        self.assertEqual(self.lb.entries[2]["name"], "Alice")

    def test_max_five_entries(self):
        """最多保留 5 条"""
        for i in range(10):
            self.lb.add_entry(f"Player{i}", float(i * 10))
        self.assertEqual(len(self.lb), 5)
        # 最高分应该是 Player9 (90 秒)
        self.assertEqual(self.lb.entries[0]["name"], "Player9")

    def test_return_rank_on_add(self):
        """add_entry 返回名次"""
        rank = self.lb.add_entry("Tony", 80.0)
        self.assertEqual(rank, 1)

        rank = self.lb.add_entry("Better", 90.0)  # Better 90 > Tony 80
        self.assertEqual(rank, 1)
        # Worse 70 < Tony 80 < Better 90 → Worse 应该排第 3
        rank = self.lb.add_entry("Worse", 70.0)
        self.assertEqual(rank, 3)

    def test_is_high_score(self):
        """前 5 名都算高分"""
        for i in range(3):
            self.lb.add_entry(f"P{i}", float(i * 10))
        self.assertTrue(self.lb.is_high_score(5.0))  # 比最低高
        self.assertTrue(self.lb.is_high_score(35.0))  # 比最高高

    def test_zero_score_is_not_high_score(self):
        """0 秒（即时死亡）不应被视为上榜分数

        修复：之前空榜时 is_high_score(0.0) 会返回 True，导致游戏还没
        开始就被提示输入名字。
        """
        # 空榜
        self.assertFalse(self.lb.is_high_score(0.0))
        # 有记录时 0 分也不应上榜
        self.lb.add_entry("Alice", 50.0)
        self.assertFalse(self.lb.is_high_score(0.0))

    def test_is_high_score_full(self):
        """5 个时，新分低于最低就不算高分"""
        for i in range(5):
            self.lb.add_entry(f"P{i}", float((i + 1) * 10))
        # 最低是 10 秒
        self.assertFalse(self.lb.is_high_score(5.0))
        self.assertTrue(self.lb.is_high_score(15.0))

    def test_persistence(self):
        """数据应能持久化"""
        self.lb.add_entry("Tony", 60.0)
        self.lb.add_entry("Bob", 50.0)
        # 重新加载
        lb2 = Leaderboard(save_path=self.tmp_path)
        self.assertEqual(len(lb2), 2)
        self.assertEqual(lb2.entries[0]["name"], "Tony")
        self.assertAlmostEqual(lb2.entries[0]["time"], 60.0)

    def test_clear(self):
        self.lb.add_entry("Tony", 60.0)
        self.lb.clear()
        self.assertEqual(len(self.lb), 0)


if __name__ == "__main__":
    unittest.main()