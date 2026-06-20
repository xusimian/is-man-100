# 第三方资源与合规清单

本项目严格遵守 App Store 审核准则，所有代码、图形、字体均为原创或使用明确许可的开源资源。

## ✅ 自有资源（无版权问题）

| 资源 | 实现方式 |
|------|---------|
| 飞机图形 | 多边形自绘（无任何第三方资源引用） |
| 子弹图形 | `pygame.draw.circle` 圆点 |
| 奖牌图标 | `pygame.draw.circle` 圆 + 数字 |
| 胜利星星 | `_make_star_points` 多边形自绘 |
| 失败 X 图标 | `pygame.draw.line` 自绘 |
| 颜色板 | RGB 值，无版权 |
| 排行榜数据 | 用户数据，应用沙盒存储 |
| 游戏代码 | 100% 原创 |

## ✅ 开源字体（推荐使用）

以下字体均为 SIL Open Font License 1.1，**可免费用于商业用途、App Store 上架**：

1. **Noto Sans CJK**（思源黑体，Google + Adobe 联合开发）
   - 下载：https://fonts.google.com/noto/specimen/Noto+Sans+SC
   - 许可：OFL 1.1
   - 路径建议：`/Library/Fonts/NotoSansCJK-Regular.ttc`

2. **Source Han Sans CN**（思源黑体，Adobe）
   - 下载：https://github.com/adobe-fonts/source-han-sans
   - 许可：OFL 1.1
   - 路径建议：`/usr/local/share/fonts/SourceHanSansCN-Regular.otf`

## ⚠️ 已避免的资源

| 资源 | 风险 | 替代方案 |
|------|------|---------|
| **SF Symbol 图标** | Apple 专有，App Store 不能直接用 | 自绘多边形 |
| **SF Pro 字体** | Apple 专有字体 | Noto Sans CJK / 思源黑体 |
| **Hiragino（苹方）** | Apple 授权字体，App Store 应用有版权风险 | Noto Sans CJK / 思源黑体 |
| **Apple Emoji** | Apple 版权，emoji 在 iOS 应用中归 Apple 所有 | 自绘图形 |
| **Apple Design Resources** | 设计素材仅供开发参考，不能直接打包 | 重绘 |

## 📋 App Store 上架前 Checklist

- [ ] 安装 Noto Sans CJK 或思源黑体（替换系统字体依赖）
- [ ] 自检代码中无任何 emoji 字符
- [ ] 自检代码中无 "SF Symbol" / "SF Pro" 字符串
- [ ] 所有图形资源自绘或已获商业许可
- [ ] 添加完整 LICENSE 文件（已包含 MIT）
- [ ] 准备隐私政策（不收集任何用户数据 → 标准模板）
- [ ] 准备应用截图 + 应用图标（自绘或购买授权）
- [ ] TestFlight 内测无审核警告

## 🎨 颜色板（无版权）

以下 RGB 值自由使用：

```
COLOR_BG_TOP    = (28, 28, 30)      # 暗模式背景
COLOR_BG_BOTTOM = (0, 0, 0)
COLOR_LABEL     = (255, 255, 255)   # 主文字
COLOR_BLUE      = (10, 132, 255)    # 系统蓝
COLOR_GREEN     = (48, 209, 88)     # 系统绿
COLOR_RED       = (255, 69, 58)     # 系统红
COLOR_GOLD      = (255, 214, 10)    # 强调色
```

## 📚 参考资料

- App Store Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
- 字体 OFL 许可: https://scripts.sil.org/OFL
- pygame 文档: https://www.pygame.org/docs/