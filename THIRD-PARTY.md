# 第三方软件、许可和源码

Codex-Glass 项目自身采用 GPL-3.0-only；第三方组件保留原作者版权及各自许可证。本文件与 `third-party-licenses/`、`dependency-sources/` 一起分发。

| 组件 | 版本 / 用途 | 许可证 / 附带材料 |
|---|---|---|
| Python | 3.12，嵌入式运行库 | Python / PSF；`Python-LICENSE` |
| PyQt6 | 6.11.0，Qt 绑定 | GPLv3；`PyQt6-LICENSE`、原版 sdist |
| PyQt6-sip | 13.12.0，绑定运行时 | BSD-2-Clause；`PyQt6-sip-LICENSE`、原版 sdist |
| Qt | 6.11.2，Core / GUI / Network / QML / Quick / Widgets / SVG 与翻译等 | LGPLv3 及各模块内的第三方许可；`Qt6-LICENSE`、对应模块源码 |
| psutil | 7.2.2，检测客户端进程 | BSD-3-Clause；`psutil-LICENSE`、原版 sdist |
| Feather | 小图标，保留原 SVG | MIT；`Feather-LICENSE` |
| PyInstaller | 6.22.3，打包及 bootloader | GPLv2-or-later 与 bootloader 分发例外；原版源码归档中附完整许可 |
| Microsoft Visual C++ Runtime | 来自 Qt wheel 的运行库 | Microsoft 运行库分发条款；原始 DLL 随 Qt 包用于运行此程序 |
| Mesa 软件 OpenGL 后备库 | Qt wheel 附带的 `opengl32sw.dll` | MIT 与相关作者声明；`Mesa-LICENSE.html` 保留 [Mesa 官方许可页](https://docs.mesa3d.org/license.html) |
| Inno Setup | 6.7.3，安装器引擎与编译器 | 许可文本见 `Inno-Setup-LICENSE`；编译器不随应用安装 |

Qt 模块源码归档包含该模块的 `LICENSES/`、第三方声明及构建脚本。安装器提供 qtbase、qtdeclarative、qtsvg、qtshadertools、qtimageformats、qttranslations 6.11.2；程序依赖动态 DLL，没有修改这些上游库。可在开发环境中重新编译并替换相应 DLL / 绑定，或按 [开发说明](DEVELOPMENT.md) 重新运行和构建整个程序；没有禁止调试、替换库或重打包的技术锁定。

上游源码及 SHA-256 清单位于 `dependency-sources/manifest.json`。项目源码和打包脚本位于 `source/`；素材生成器使用的 Pillow、文档转换使用的 Python-Markdown 仅为构建工具，不包含在应用运行时。

构建器从 [PyPI](https://pypi.org/) 获取固定版本的原版 sdist，从 [Qt 官方源码目录](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/) 获取固定模块归档，并验证发布方 SHA-256。安装后可离线取得这些源码，无需依赖下载链接继续有效。
