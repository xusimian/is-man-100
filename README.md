# 是男人就100

> 一个"100"主题的极简挑战游戏。100 秒内躲避四面八方飞来的子弹，撑住就是胜利。

![Platform: macOS / PC (Python) | iOS (Swift, planned)](https://img.shields.io/badge/platform-macOS%20%7C%20PC%20%7C%20iOS-lightgrey)
![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue)
![License: TBD](https://img.shields.io/badge/license-TBD-orange)

## 🎮 玩法

1. 玩家拖动屏幕中央的飞机
2. 四面八方持续飞来子弹（速度随时间加速）
3. 飞机碰到子弹 → 失败
4. **撑过 100 秒 → 胜利**

详见 [DESIGN.md](DESIGN.md) 完整设计文档。

## 📁 项目结构

```
is-man-100/
├── core/              # 共享游戏逻辑（平台无关，Python）
├── mac/               # macOS / PC 版本（Pygame 渲染）
├── ios/               # iOS 版本（占位，未来用 Swift/SpriteKit）
├── tests/             # 单元测试
├── DESIGN.md          # 完整设计文档
├── requirements.txt   # Python 依赖
└── README.md
```

## 🚀 快速开始（macOS / PC）

### 1. 安装依赖

```bash
pip3 install pygame
```

### 2. 运行游戏

```bash
cd ~/Desktop/project/是男人就100
python3 -m mac.main
```

或者直接双击 `~/Desktop/run-game.sh` 启动。

### 3. 运行测试

```bash
cd ~/Desktop/project/是男人就100
python3 -m unittest discover tests -v
```

## 🕹️ 操作

| 操作 | 效果 |
|------|------|
| 鼠标按住拖动 | 控制飞机移动 |
| 点击屏幕 | 开始 / 重玩 |
| `Enter` / `Space` | 开始 / 重玩 |
| `Esc` | 退出游戏 |

## 🎯 难度曲线

```
子弹速度 v(t) = 60 + 260 × (t/100)²  pt/s
子弹频率 N(t) = 2 + 6 × (t/100)       发/s
```

- t=0s：60 pt/s, 2 发/s（热身）
- t=50s：125 pt/s, 5 发/s（专注）
- t=100s：320 pt/s, 8 发/s（极限）

## 📱 iOS 版本（计划中）

未来将使用 **Swift + SpriteKit** 实现，复用 `core/` 中的游戏逻辑设计。详见 [ios/README.md](ios/README.md)。

## 🤝 贡献

欢迎 Issue 和 PR！

## 📄 License

TBD