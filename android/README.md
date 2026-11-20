# Android 版本

用 Kotlin + Android Canvas 重写的原生 Android 版，与 Python/Pygame 版共享同一套玩法设计。

## 🎮 玩法

1. 手指拖动屏幕中央的飞机
2. 四面八方持续飞来子弹（速度随时间加速）
3. 飞机碰到子弹 → 失败
4. **撑过 100 秒 → 胜利**

## 📦 安装

APK 已签名，直接安装即可：

```bash
adb install -r app-release.apk
```

或者把 APK 传到手机，在文件管理器里点击安装（需允许「安装未知来源应用」）。

**最低系统版本**：Android 7.0（API 24）
**目标版本**：Android 14（API 34）

## 🛠 从源码构建

### 依赖

| 组件 | 版本 |
|------|------|
| JDK | 17+ |
| Android SDK | platform 34 + build-tools 34.0.0 |
| Gradle | 8.7+ |

### 构建命令

```bash
cd android
export ANDROID_HOME=/path/to/android-sdk

# Debug APK（带调试器，可断点）
./gradlew assembleDebug

# Release APK（已用 debug 签名，可直接安装）
./gradlew assembleRelease

# 单元测试
./gradlew testDebugUnitTest

# Lint 检查
./gradlew lintRelease
```

产物位置：

```
android/app/build/outputs/apk/debug/app-debug.apk
android/app/build/outputs/apk/release/app-release.apk
```

### 签名说明

`release` 构建目前使用 **debug keystore** 签名，保证产出的 APK 能直接安装。
正式上架 Google Play 前需要换成自己的 release keystore：

```bash
keytool -genkey -v -keystore my-release.jks -keyalg RSA -keysize 2048 \
        -validity 10000 -alias my-key
```

然后在 `app/build.gradle` 里配置 `signingConfigs.release` 并引用它。

## 📁 目录结构

```
android/
├── app/
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── java/com/xusimian/isman100/
│   │   │   ├── MainActivity.kt          # 入口：全屏沉浸 + IME 输入
│   │   │   ├── core/                    # 平台无关的游戏逻辑
│   │   │   │   ├── Constants.kt         # 常量（对应 core/constants.py）
│   │   │   │   ├── GameState.kt
│   │   │   │   ├── GameContext.kt       # 屏幕尺寸 + 缩放
│   │   │   │   ├── Difficulty.kt        # 难度曲线
│   │   │   │   ├── Bullet.kt
│   │   │   │   ├── Player.kt
│   │   │   │   ├── Game.kt              # 主控制器
│   │   │   │   └── Leaderboard.kt       # 高分榜（SharedPreferences）
│   │   │   ├── render/                  # 渲染层
│   │   │   │   ├── Palette.kt           # 深空赛博色板
│   │   │   │   ├── Glow.kt              # 辉光贴图工具
│   │   │   │   ├── StarField.kt         # 缓存式星场背景
│   │   │   │   ├── Renderers.kt         # 飞船 / 子弹 / 粒子
│   │   │   │   ├── Hud.kt               # 倒计时 + 进度条
│   │   │   │   └── TextRenderer.kt
│   │   │   └── ui/
│   │   │       └── GameView.kt          # 状态机 + 触屏交互
│   │   └── res/                         # 图标 / 主题 / 字符串
│   └── src/test/                        # 单元测试（36 个）
├── build.gradle
├── settings.gradle
└── gradle.properties
```

## 🔄 与 Python 版的关系

`core/` 目录下的 Kotlin 逻辑与 Python 版 `core/` 一一对应，**参数完全相同**：

| Python | Kotlin | 说明 |
|--------|--------|------|
| `core/constants.py` | `core/Constants.kt` | 难度参数、尺寸、阈值 |
| `core/difficulty.py` | `core/Difficulty.kt` | 速度/生成率曲线 |
| `core/bullet.py` | `core/Bullet.kt` | 子弹生成与移动 |
| `core/player.py` | `core/Player.kt` | 飞机移动与边界 |
| `core/game.py` | `core/Game.kt` | 主循环与状态机 |
| `core/leaderboard.py` | `core/Leaderboard.kt` | 高分榜 |
| `mac/ui.py` | `ui/GameView.kt` | 界面状态机 + 交互 |
| `mac/visuals.py` | `render/*` | 视觉系统 |

两端的 bug 修复也保持同步：

- 榜单同分同名时名次错误 → 用插入索引定位，不按内容反查
- 负 dt 让计时器倒退 → `dt = max(dt, 0f)`
- 单帧卡顿瞬间判死 → `MAX_FRAME_DT` 钳制（**在渲染层**，逻辑层不干预）
- ESC 跳过名字输入后错判胜利 → 记录 `settleState`，兜底不把 PLAYING 映射成 victory

### 与 Python 版的差异

| 方面 | Python 版 | Android 版 |
|------|----------|-----------|
| 屏幕尺寸 | 固定 393×852 | 动态，按 `scale` 等比缩放 |
| 坐标基准 | 绝对像素 | 基准分辨率 × scale |
| 高分榜存储 | JSON 文件 | SharedPreferences |
| 字体 | 扫描系统找 CJK 字体 | 系统自带 Sans + 中文 |
| 名字输入 | 键盘直接键入 | IME 软键盘（隐藏 EditText 承载） |

## ✅ 测试

```bash
cd android && ./gradlew testDebugUnitTest
```

**36 个测试全过**：

- `GameLogicTest`（30 个）—— 逻辑层与 Python 版行为对齐
- `GameViewRenderTest`（6 个）—— Robolectric NATIVE 图形模式真实执行 Canvas 绘制，验证各状态能画出内容

> ⚠️ Robolectric 必须用 `@GraphicsMode(NATIVE)`：默认 LEGACY 模式不栅格化 Canvas 操作，连 `drawColor` 出来的都是黑图，像素断言会全部误判。

## 📝 已知限制

- **Release APK 用 debug keystore 签名** —— 能直接装，但正式上架要换签名
- **没有音效/震动反馈** —— 碰撞只有红闪 + 屏幕震动
- **没有 iOS 版** —— `ios/` 目录仍是占位
