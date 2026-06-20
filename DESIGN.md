# 是男人就100 - 游戏设计文档

> 版本 v0.1.0 | 状态：设计阶段 | 最后更新：2026-06-16

---

## 1. 项目概述

### 1.1 一句话描述
玩家通过手指拖动屏幕中央的飞机，躲避从四面八方飞来的子弹，**撑过 100 秒即为胜利**。

### 1.2 目标用户
- 喜欢极简挑战、休闲竞技的玩家
- iPhone/iPad 用户
- 单局时长 1-2 分钟的碎片化游戏场景

### 1.3 核心体验
- **紧张感**：持续威胁感，无安全时刻
- **专注感**：纯反应和操作，无需思考
- **成就感**：撑过 100 秒的明确胜利反馈

### 1.4 项目代号
`is-man-100`（GitHub 仓库名）

---

## 2. 核心玩法机制

### 2.1 游戏循环

```
┌─────────────┐
│  开始界面    │ ← 玩家点击"开始"
└──────┬──────┘
       ↓
┌─────────────┐
│  游戏进行中  │ ← 计时器从 0 跑到 100
└──────┬──────┘
       ↓
   ┌───┴───┐
   │       │
碰到子弹  撑过100s
   │       │
   ↓       ↓
失败界面  胜利界面
```

### 2.2 操作方式
- **唯一输入**：手指触屏拖动
- **飞机跟随**：飞机实时跟随手指位置
- **飞机限制**：飞机不能移出屏幕边界
- **点击操作**：开始 / 重玩按钮

### 2.3 碰撞规则
- **飞机**：椭圆形 hitbox（飞机图标的视觉边界）
- **子弹**：圆形 hitbox
- **判定**：两个 hitbox 重叠即判定失败
- **容错**：可调参数（默认飞机 hitbox 略小于视觉大小，给玩家一点容错）

### 2.4 胜负条件
- ✅ **胜利**：计时器到 100 秒，玩家仍然存活
- ❌ **失败**：飞机与任何子弹发生碰撞

---

## 3. 难度曲线

### 3.1 速度公式

采用**二次曲线**（先慢后快）：

```
bulletSpeed(t) = baseSpeed + (maxSpeed - baseSpeed) × (t/100)²
```

参数（**v0.2.0 调整**，开局更难）：
- `baseSpeed = 90 pt/s`（起始速度，**原 60**，更紧张）
- `maxSpeed = 380 pt/s`（终局速度，**原 320**，更刺激）
- `t` 为当前游戏时间（秒），范围 0-100

### 3.2 关键时刻速度表

| 时间 (s) | 速度 (pt/s) | 主观感受 |
|---------|------------|---------|
| 0       | 90         | 紧凑开局（不再慢悠悠） |
| 10      | 92.9       | 维持紧张 |
| 30      | 116.1      | 明显压力 |
| 50      | 162.5      | 需要专注 |
| 70      | 232.1      | 手心出汗 |
| 90      | 324.9      | 高强度反应 |
| 100     | 380        | 极限 |

### 3.3 子弹生成频率

每秒生成 `N(t)` 个子弹：

```
N(t) = floor(baseCount + (maxCount - baseCount) × (t/100))
```

参数（**v0.2.0 调整**）：
- `baseCount = 4`（每秒 4 发，**原 2**，开局即有压力）
- `maxCount = 10`（每秒 10 发，**原 8**，终局地狱）

### 3.4 子弹生成位置
- 从屏幕**四条边**随机一点出现
- 飞行方向：屏幕中心点 ± 一定角度随机偏移（±30°）
- 这样保证子弹主要向中央飞，飞机必须移动

### 3.5 子弹数量上限
- 屏幕内**同时存在最多 100 颗子弹**（性能保护）
- 超过时自动清除最老的

---

## 4. 视觉设计规范

### 4.1 颜色主题

| 元素 | 颜色 | 说明 |
|------|------|------|
| 背景 | 渐变深蓝 → 黑 | `#0A0E27` → `#000000`，从中心向外辐射 |
| 飞机 | 白色 | `#FFFFFF`，高对比度 |
| 子弹 | 浅红色 | `#FF6B6B`，警示色 |
| 子弹拖尾 | 半透明红 | `#FF6B6B33`，运动感 |
| 胜利 UI | 金色 | `#FFD700` |
| 失败 UI | 深红 | `#8B0000` |
| 倒计时文字 | 白色 | `#FFFFFF`，大号字体 |

### 4.2 飞机图标

极简易识别，使用 SF Symbol 或简单绘制：
- 形态：对称飞机剪影（类似 `airplane` SF Symbol）
- 大小：屏幕宽度的 1/10（约 40pt @ iPhone 15）
- 朝向：固定朝上（不影响玩法）

### 4.3 子弹视觉

- 形态：实心圆点
- 大小：8pt 半径（固定）
- 拖尾：可选 v0.2 实现
- 闪烁：终局（t > 80s）时子弹轻微闪烁（0.5Hz），增加紧张感

### 4.4 屏幕布局（竖屏）

```
┌─────────────────┐
│                 │
│   倒计时: 73    │ ← 顶部居中，大字
│                 │
│        ✈        │ ← 飞机初始在屏幕中心
│                 │
│   ● ●     ●     │ ← 子弹从四面八方飞来
│       ●         │
│                 │
│                 │
└─────────────────┘
```

---

## 5. UI/UX 流程

### 5.1 开始界面
- 大标题"是男人就100"
- 副标题"撑过 100 秒即为胜利"
- 中央按钮"开始挑战"
- 底部小字"v0.1.0"

### 5.2 游戏界面
- 顶部：倒计时（秒，1 位小数，如 "73.4"）
- 中间：游戏画面
- 无其他 UI 干扰（沉浸感）

### 5.3 失败界面
- 大字"挑战失败"
- 显示存活秒数："你撑了 X.X 秒"
- 按钮"再来一次"
- 按钮"返回首页"

### 5.4 胜利界面
- 大字"是男人！"（金色）
- 显示完成时间："100.0 秒"
- 按钮"再次挑战"
- 按钮"返回首页"

### 5.5 音效（v0.2+）
- 子弹发射：微弱"嗖"声
- 碰撞：失败音
- 胜利：胜利音
- 倒计时最后 10 秒：每滴答一声

---

## 6. 技术架构

### 6.1 技术选型

| 维度 | 选择 | 理由 |
|------|------|------|
| 语言 | Swift 5.9+ | iOS 原生 |
| 框架 | SpriteKit | 2D 游戏引擎标杆，性能优秀 |
| 最低 iOS 版本 | iOS 16.0 | 覆盖 95%+ 活跃设备 |
| 开发工具 | Xcode 15+ | 标配 |
| 依赖管理 | Swift Package Manager | 零外部依赖，最简 |
| 状态管理 | 原生 + 简单枚举 | 游戏状态少，不需要框架 |

### 6.2 架构模式

采用轻量级 MVC：

```
GameViewController (View Controller)
    │
    ├── GameScene (SpriteKit SKScene)
    │     ├── 渲染循环
    │     ├── 子弹管理
    │     ├── 飞机管理
    │     └── 碰撞检测
    │
    └── GameState (Model)
          ├── .menu
          ├── .playing
          ├── .gameOver(survivalTime)
          └── .victory
```

### 6.3 核心类设计

```swift
// 状态机
enum GameState {
    case menu
    case playing(elapsedTime: TimeInterval)
    case gameOver(survivalTime: TimeInterval)
    case victory
}

// 子弹
class Bullet: SKShapeNode {
    let spawnTime: TimeInterval
    let speed: CGFloat
    init(speed: CGFloat, direction: CGVector, position: CGPoint)
    func update(deltaTime: TimeInterval)
}

// 飞机
class Player: SKShapeNode {
    var position: CGPoint { didSet { /* 边界限制 */ } }
    let hitboxRadius: CGFloat = 15
}

// 主场景
class GameScene: SKScene {
    var state: GameState
    var player: Player
    var bullets: [Bullet]
    var spawnTimer: TimeInterval
    let difficulty: DifficultyCurve
    func didMove(to view: SKView)
    override func update(_ currentTime: TimeInterval)
    func spawnBullet()
    func checkCollisions()
}
```

### 6.4 性能预算

- 目标帧率：60 FPS
- 最大子弹数：100 颗
- 碰撞检测：O(n)，n ≤ 100 完全够用
- 内存：< 50 MB

---

## 7. 文件结构

```
is-man-100/
├── README.md                       # 项目说明
├── DESIGN.md                       # 本文档
├── LICENSE                         # 待定（建议 MIT）
├── .gitignore                      # ✅ 已配置
│
├── IsMan100/                       # Xcode 项目主目录
│   ├── IsMan100.xcodeproj/
│   ├── IsMan100/
│   │   ├── AppDelegate.swift
│   │   ├── GameViewController.swift
│   │   ├── GameScene.swift
│   │   ├── Models/
│   │   │   ├── GameState.swift
│   │   │   ├── DifficultyCurve.swift
│   │   │   ├── Bullet.swift
│   │   │   └── Player.swift
│   │   ├── Views/
│   │   │   ├── MenuView.swift
│   │   │   ├── GameView.swift
│   │   │   ├── GameOverView.swift
│   │   │   └── VictoryView.swift
│   │   ├── Resources/
│   │   │   └── Assets.xcassets/
│   │   └── Info.plist
│   └── IsMan100Tests/
│       └── DifficultyCurveTests.swift
│
└── docs/
    ├── screenshots/
    └── gifs/
```

---

## 8. 分阶段实施计划

### 🎯 Phase 0：项目脚手架（已完成 ✅）
- ✅ 创建 GitHub 仓库
- ✅ 初始化 README + .gitignore
- ✅ 写设计文档

### 🎯 Phase 1：最小可玩版本（MVP）
**目标**：能在模拟器跑起来，飞机能躲避子弹，撑到 100 秒显示胜利，碰撞显示失败

**任务清单**：
- [ ] 创建 Xcode 项目 `IsMan100.xcodeproj`
- [ ] 实现 `GameScene` 基础渲染循环
- [ ] 实现 `Player` 飞机类（手指拖动）
- [ ] 实现 `Bullet` 子弹类（从边缘生成，飞向中心）
- [ ] 实现 `DifficultyCurve`（速度/频率公式）
- [ ] 实现碰撞检测（飞机 vs 子弹）
- [ ] 实现 `GameState` 状态机
- [ ] 实现倒计时显示
- [ ] 实现开始 / 失败 / 胜利界面

**交付物**：可在模拟器玩的完整一局游戏

### 🎯 Phase 2：视觉打磨
**任务清单**：
- [ ] 添加飞机图标（SF Symbol 或自绘）
- [ ] 添加子弹拖尾效果
- [ ] 优化背景渐变
- [ ] 失败/胜利界面美化
- [ ] 倒计时字体美化
- [ ] 终局子弹闪烁效果

### 🎯 Phase 3：音效与触觉
- [ ] 添加基础音效
- [ ] 碰撞时震动反馈
- [ ] 倒计时最后 10 秒滴答声

### 🎯 Phase 4：扩展功能
- [ ] 本地最高分记录（UserDefaults）
- [ ] 难度选择（简单/普通/地狱）
- [ ] 排行榜（Game Center）
- [ ] 主题切换

### 🎯 Phase 5：上架准备
- [ ] App Icon（1024×1024）
- [ ] 启动屏
- [ ] 隐私政策
- [ ] App Store 截图
- [ ] TestFlight 内测

---

## 9. 测试策略

### 9.1 单元测试（XCTest）
- `DifficultyCurveTests`：验证速度公式在 t=0, 50, 100 时返回正确值
- `PlayerTests`：验证飞机边界限制
- `GameStateTests`：验证状态转换合法性

### 9.2 手动测试清单
- [ ] iPhone 15 Pro 模拟器：60 FPS
- [ ] iPhone SE（老设备）：≥ 30 FPS
- [ ] 横竖屏切换：锁定竖屏
- [ ] 不同屏幕尺寸：飞机始终居中可见
- [ ] 100 秒通关：能完整跑完一次
- [ ] 失败流程：撞子弹立即结束

### 9.3 边界情况
- [ ] 应用进入后台再回来：游戏暂停
- [ ] 来电中断：游戏暂停
- [ ] 锁屏：游戏暂停

---

## 10. 后续迭代方向

### 10.1 玩法扩展
- **道具系统**：护盾、减速、时间延长
- **多模式**：无尽模式（看能撑多久）、关卡模式（10 关一难度）
- **Boss 关**：每 25 秒出现一波特殊弹幕

### 10.2 社交功能
- **分享成绩**：分享到微信/QQ/微博
- **好友 PK**：同屏双人对抗
- **全球排行榜**

### 10.3 商业化（可选）
- **广告**：失败界面底部横幅
- **内购**：去广告 / 换主题

---

## 附录 A：数学公式速查

### 速度曲线（二次）
```
v(t) = 60 + 260 × (t/100)²     pt/s
```

### 子弹频率（线性）
```
N(t) = floor(2 + 6 × t/100)     发/s
```

### 飞行方向
```
direction = normalize(center - spawnPoint) + randomAngle(±30°)
```

---

## 附录 B：术语表

| 术语 | 解释 |
|------|------|
| Hitbox | 碰撞检测的实际区域 |
| 弹幕 | 从多方向密集飞来的子弹群 |
| 帧率 | FPS，每秒渲染帧数 |
| SpriteKit | 苹果 2D 游戏框架 |
| pt | iOS 逻辑像素单位（point） |

---

## 文档变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1.0 | 2026-06-16 | 初稿，包含完整核心玩法、技术架构、实施计划 |