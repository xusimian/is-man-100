# iOS 版本（占位）

## 状态
⏳ **未实现** —— 当前阶段专注于 Python + Pygame 跨平台原型。

## 计划

iOS 版本将使用 **Swift + SpriteKit** 实现，**复用 core/ 中的游戏逻辑设计**：

- 难度曲线（core/difficulty.py）→ 改写为 Swift
- 飞机 / 子弹类 → 改写为 SKShapeNode
- 主循环 → 改写为 SKScene.update()
- 渲染细节 → 利用 SpriteKit 的硬件加速

## 实现路线

1. 在 Mac 上安装 Xcode（需要 macOS 13+）
2. 创建新项目 iOS Game (SpriteKit)
3. 将 `core/` 中的逻辑逐个翻译为 Swift
4. 添加 iOS 特有的功能：
   - 触屏控制（UIScene / SKScene touchesBegan）
   - Game Center 排行榜
   - 本地高分（UserDefaults）
   - 应用生命周期（pause/resume）

## 设计参考

- DESIGN.md 中的完整设计规范
- core/ 中的所有 Python 代码作为伪代码参考

详见 [DESIGN.md §6 技术架构](../DESIGN.md)