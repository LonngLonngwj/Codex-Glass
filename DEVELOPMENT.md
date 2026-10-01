# Codex-Glass 开发说明

本文件面向源码运行与维护。普通使用、跟随启动和问题排查见 [使用说明](README.md)。

## GitHub 仓库与发行包

本仓库保存源码、构建脚本、说明、预览图和许可声明。预构建 `app/`、依赖源码归档和安装 EXE 不进入 Git 历史；构建时会生成或下载这些文件。[GitHub Releases](https://github.com/LonngLonngwj/Codex-Glass/releases) 提供完整安装程序，安装后可以离线取得项目及依赖源码。

克隆后进入项目目录，再按以下环境和构建步骤操作。

## 环境与目录

已使用 Windows x64、Python 3.12、PyQt6 6.11.0 / Qt 6.11.2、psutil 7.2.2、PyInstaller 6.22.3 构建和验证。固定依赖见 `source/requirements.txt`。

| 路径 | 用途 |
|---|---|
| `app/Codex-Glass/` | 便携 EXE 和完整运行库 |
| `source/main.py` | 入口、托盘、菜单、拖拽、单实例和生命周期 |
| `source/Widget.qml` | 布局、交互和动画 |
| `source/geometry.py` / `native.py` | 超椭圆、命中测试、窗口 DPI 与鼠标捕获 |
| `source/provider.py` / `quota.py` | CLI 异步查询、客户端检测、额度解析 |
| `source/settings.py` | 偏好、备份、Windows 登录启动 |
| `source/assets/` / `icons/` | 透明阴影、着色 SVG 与原始图标 |
| `source/generate_assets.py` | 可选的构建期素材生成器 |
| `source/start-independent.ps1` | 从托管终端独立启动交付 EXE |
| `source/test_*.py` | 核心和 GUI 回归检查 |
| `third-party-licenses/` | 依赖许可文本 |

## 创建环境并运行

进入 `source/` 后执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 默认：跟随客户端，读取真实额度
.\.venv\Scripts\python.exe main.py

# 示例：不读取账号额度、不保存常用偏好
.\.venv\Scripts\python.exe main.py --demo --card --show
```

源码在托管终端中的设置目录可能被宿主重定向。演示 / GUI 测试使用示例和临时设置；验证实际登录启动时应使用独立 EXE 的正常用户环境。

## 常用参数

以下参数也可传给交付 EXE。更改渲染器等启动参数前，先退出已有真实实例；单实例机制通常会唤回旧实例，而不是改变它的启动参数。

```powershell
# 始终显示，不等待客户端（本次运行不随客户端隐藏）
.\.venv\Scripts\python.exe main.py --show --card --language zh

# 示例：三档色调、英文、小浮球、深色
.\.venv\Scripts\python.exe main.py --demo --demo-remaining 74 --card
.\.venv\Scripts\python.exe main.py --demo --demo-remaining 35 --card --language en
.\.venv\Scripts\python.exe main.py --demo --demo-remaining 8 --bubble --dark

# 示例截图：导出后退出
.\.venv\Scripts\python.exe main.py --demo --card --export preview.png

# 默认软件渲染；硬件模式用于比较或排查
.\.venv\Scripts\python.exe main.py --renderer hardware --show

# 便于窗口检查；启动诊断在约 4 秒时输出一个快照
.\.venv\Scripts\python.exe main.py --demo --inspect --diagnostic diagnostic.json

# 完全退出已有真实实例 / 关闭匹配的登录启动项
.\.venv\Scripts\python.exe main.py --quit
.\.venv\Scripts\python.exe main.py --disable-startup
```

`--demo` 的截图和内容明确标记为示例；`--export` 不保存常用偏好。演示 / 导出实例不参与真实实例的单实例锁。诊断文件可能包含额度、套餐、同步状态和窗口位置，分享前检查内容；诊断不是连续日志。

## 查询与渲染实现

额度经 `codex app-server --listen stdio://` 的 JSON-RPC 读取，依次初始化并请求 `account/rateLimits/read`。查询间隔为 60 秒，超时 20 秒；响应缓冲上限 2 MB。采用异步 QProcess，结束时清理本程序创建的查询子进程。

客户端检查每 3 秒枚举进程名称，再只读取匹配候选的完整路径；CLI 有效路径复用。通过路径区分桌面客户端和 CLI，避免自己的查询子进程导致“客户端一直运行”。

默认 `software` 后端，环境已显式设置 `QT_QUICK_BACKEND` 时遵循环境值。轮廓使用指数 2.6 的超椭圆采样；阴影预生成，图标着色在 SVG 中完成。运行时不需要 Pillow。若修改轮廓或阴影，可重新生成素材：

```powershell
.\.venv\Scripts\python.exe -m pip install Pillow
.\.venv\Scripts\python.exe generate_assets.py
```

跨屏拖拽使用 Windows 原生移动，逻辑窗口尺寸始终来自所选档位；DPI 通知处理后延迟校正。拖动时的 150ms 检查只在实际松手后恢复丢失的结束状态，不中断按住的拖动。

## 验证

在 `source/` 下运行：

```powershell
$env:QT_QUICK_BACKEND = 'software'
.\.venv\Scripts\python.exe -m unittest test_core test_widget_sizes test_interaction test_brand test_instance -v
```

GUI 检查会短暂打开本程序自己的窗口和菜单，使用示例额度、临时偏好，不修改正常设置。尺寸检查使用当前连接的显示器；交互检查覆盖丢失拖拽结束事件、菜单销毁及隐藏期间的捕获清理。当前版本共 24 项检查通过，详细验证边界见 [验证记录](design-qa.md)。

## 构建便携版

先退出正在运行的交付 EXE，保留旧便携目录以便恢复，再在 `source/` 执行：

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.22.3
.\build.ps1 -Python .\.venv\Scripts\python.exe

# 可选：将中间文件放到指定目录
.\build.ps1 -Python .\.venv\Scripts\python.exe -WorkPath C:\Codex-Glass-build
```

输出为项目目录中的 `app/Codex-Glass/`。脚本会替换此生成目录；构建后保留完整 EXE、`_internal`、QML、SVG 和阴影素材。它会随包放入 Qt 所需的 VC 运行库，并清理生成包中误收集的不兼容 ICU 文件，不修改全局系统 DLL。

交付时整体压缩项目目录，包含 README、开发说明、验证记录和第三方许可；排除 `.venv`、`__pycache__`、`.pyc` 与个人诊断文件。搬移后重新登记实际部署目录的登录启动项。

## 名称兼容

程序与构建输出名称为 `Codex-Glass`，Windows 文件属性中的产品名和文件描述同名，版本 3.1.1。为了保留旧偏好与防止新旧版本同时运行，设置目录 `QuotaGlass` 和内部单实例管道 `QuotaGlass2-` 保持兼容；它们不是界面名称。登录启动项改为 `Codex-Glass`，打包版首次正常启动时按所有权检查迁移旧启动项，演示与导出不迁移。

## 构建 Windows 安装包

先完成便携 EXE 构建，再安装构建期依赖与 Inno Setup 6.7.3。无需把 Inno 编译器、Pillow 或 Markdown 放进运行库。

```powershell
# 在 source/ 下执行
.\.venv\Scripts\python.exe -m pip install Markdown==3.9 Pillow
.\.venv\Scripts\python.exe generate_icon.py
.\build.ps1 -Python .\.venv\Scripts\python.exe
.\installer\build-installer.ps1 -Python .\.venv\Scripts\python.exe -ISCC 'C:\Inno Setup 6\ISCC.exe' -OutputPath '..\..\installers'
```

ICO 已随源码提供，仅修改图标时需重新生成。`build-installer.ps1` 验证并下载固定版本的上游依赖源码，生成离线 HTML 说明和项目源码 ZIP，然后编译 `Codex-Glass.iss`，生成安装 EXE 与 SHA-256 文件。构建需要网络；安装及查看源码不需要网络。

固定 AppId 支持覆盖更新；默认安装在当前用户 LocalAppData/Programs。安装和卸载使用 `--quit-if-owned`，只向路径匹配的当前实例发出退出请求；它在启动项迁移与 GUI 初始化之前返回，避免影响别处的便携副本。单实例管道保留旧名称兼容。

`hooks/hook-PyQt6.QtQml.py` 在构建分析时只收集本程序所用 QtQml / QtQuick 模块，去除无关的 3D、PDF、传感器等 QML 插件与其传递 DLL。运行所需动态库保留在 `_internal`，可替换；没有向系统目录安装 DLL。

分享版按 GPL-3.0-only，项目源码、许可证、构建脚本和第三方对应源码一起安装。上游来源、版本和校验值见 `dependency-sources/manifest.json`，许可说明见 [第三方说明](THIRD-PARTY.md)。构建目录与发布包中不要混入个人偏好、CLI 登录信息、诊断文件或虚拟环境。
