"""
游戏状态机

定义游戏的所有状态及转换规则。
"""
from enum import Enum


class GameState(Enum):
    """游戏状态"""
    MENU = "menu"                         # 开始界面
    PLAYING = "playing"                   # 游戏进行中
    GAME_OVER = "game_over"               # 失败
    VICTORY = "victory"                   # 胜利

    def is_active(self) -> bool:
        """是否处于活跃状态（需要更新游戏逻辑）"""
        return self == GameState.PLAYING

    def is_terminal(self) -> bool:
        """是否处于结束状态（失败或胜利）"""
        return self in (GameState.GAME_OVER, GameState.VICTORY)