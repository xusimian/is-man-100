"""
游戏常量定义

跨平台统一常量（mac Pygame 和未来 iOS SpriteKit 共享）。
"""

# 游戏目标
TARGET_SURVIVAL_TIME = 100.0  # 胜利条件：撑过 100 秒

# 屏幕尺寸（iPhone 风格竖屏）
SCREEN_WIDTH = 393
SCREEN_HEIGHT = 852

# 玩家飞机
PLAYER_SIZE = 40               # 飞机视觉大小（像素）
PLAYER_HITBOX_RADIUS = 18      # 碰撞判定半径（比视觉略小，给容错）
PLAYER_COLOR = (255, 255, 255) # 白色

# 子弹
BULLET_RADIUS = 8
BULLET_COLOR = (255, 107, 107)       # 浅红色
BULLET_TRAIL_COLOR = (255, 107, 107, 80)  # 半透明拖尾
BULLET_MAX_ON_SCREEN = 100           # 同时存在最大数量

# 难度参数（参考 DESIGN.md §3）
DIFFICULTY_BASE_SPEED = 60.0    # 起始子弹速度（pt/s）
DIFFICULTY_MAX_SPEED = 320.0    # 终局子弹速度（pt/s）
DIFFICULTY_BASE_COUNT = 2       # 起始每秒生成数
DIFFICULTY_MAX_COUNT = 8        # 终局每秒生成数

# 子弹生成角度偏移（±30 度）
BULLET_DIRECTION_JITTER = 30  # 度

# 颜色
COLOR_BACKGROUND_TOP = (10, 14, 39)       # 深蓝
COLOR_BACKGROUND_BOTTOM = (0, 0, 0)       # 黑
COLOR_VICTORY = (255, 215, 0)             # 金色
COLOR_GAME_OVER = (139, 0, 0)             # 深红
COLOR_TEXT = (255, 255, 255)              # 白色

# UI
FONT_SIZE_LARGE = 72
FONT_SIZE_MEDIUM = 48
FONT_SIZE_SMALL = 24
COUNTDOWN_DECIMAL_PLACES = 1

# 终局闪烁阈值（秒）
LATE_GAME_THRESHOLD = 80.0