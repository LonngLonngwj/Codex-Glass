# Codex-Glass 分享与安装

版本 3.1.1 · Windows x64 · GPL-3.0-only

## 分享 GitHub 下载链接

把 [最新版本下载页](https://github.com/LonngLonngwj/Codex-Glass/releases/latest) 发给别人即可；页面的 Assets 中下载 **Codex-Glass-3.1.1-Windows-x64-Setup.exe**。仓库首页与源码见 [Codex-Glass](https://github.com/LonngLonngwj/Codex-Glass)。

## 发给别人哪个文件

分享 **Codex-Glass-3.1.1-Windows-x64-Setup.exe** 即可。安装包包含可运行程序、中文离线使用说明、完整项目源码、构建脚本、许可证，以及随程序提供的 PyQt / Qt 等依赖的对应上游源码。接收者不需要安装 Python 或编译源码。

SHA-256 校验文件可同时发送，用于核对下载完整性。校验值不能代替发布者签名。

## 接收者怎么安装

1. 双击安装程序，按向导选择安装目录。
2. 可选“创建桌面快捷方式”和“登录 Windows 后自动守候”。后者默认不勾选；在软件菜单中也可设置。
3. 完成后启动 Codex-Glass，打开 Codex 客户端。
4. 如果没有额度数据，按 [使用说明](README.md) 检查本机 Codex CLI 与登录状态。

默认安装目录是 `%LOCALAPPDATA%\Programs\Codex-Glass`，只安装到当前用户，不要求管理员权限。开始菜单提供程序、使用说明和卸载入口。

运行环境为 Windows 10 1809 及以上 / Windows 11，64 位；当前仅在本机 Windows x64 验证。运行库支持范围参考 [Qt 6.11 官方平台说明](https://doc.qt.io/qt-6.11/supported-platforms.html)。未制作 macOS / Linux 或原生 ARM 安装包。

真实额度需要用户自己的、已登录的 Codex CLI。安装包不含发布者的账号、Token、Cookie、偏好、同步记录或诊断数据，不包含 Codex CLI / ChatGPT / Codex 客户端。仅跟随 ChatGPT 显示时，读取的也仍然是 Codex 额度。

## 更新、卸载和便携版迁移

更新时再次运行新版安装程序，沿用原目录即可。安装器会请求当前安装目录的程序正常退出，更新程序文件；大小、主题等个人偏好保留。安装过程中如有文件占用，按向导提示关闭本程序后重试。

卸载可从 Windows“设置 → 应用 → 已安装的应用 → Codex-Glass”或开始菜单进行。卸载会清理此安装目录的程序、快捷方式和属于它的登录启动项，保留 `%LOCALAPPDATA%\QuotaGlass` 内的个人偏好。它不会关闭其他目录中的便携版，也不会删除由其他副本登记的登录启动项。

从便携版转为安装版：先从托盘退出旧副本，再安装并启动安装版。需要自动守候时，在安装向导中勾选，或在安装版菜单中重新启用。偏好会复用历史目录。不要同时运行两个副本；软件对同一 Windows 用户只保留一个真实实例。

## 开源与第三方许可

本项目按 **GNU GPL 第 3 版（GPL-3.0-only）**提供；完整条款见 [LICENSE](LICENSE)。可使用、研究、修改和分发，按许可证保留声明、提供对应源码，并遵守修改版分发要求。软件不提供担保。无需把私人使用的修改公开上传到 GitHub。

安装后 `source/` 是项目源码，`Codex-Glass-3.1.1-Source.zip` 是项目源码压缩副本；`dependency-sources/` 存放依赖的原版源码归档和校验清单。依赖继续遵循各自许可证，详见 [第三方说明](THIRD-PARTY.md)。重新打包时不要只留下 EXE 而移除源码和许可材料。

Codex-Glass 是独立社区工具，与 OpenAI 没有隶属关系。账号和服务由用户自己的客户端与 CLI 管理。

当前安装包和程序没有商业数字签名。Windows 是否展示“未知发布者”或信誉提示取决于系统设置与文件来源；发布时应说明版本、文件来源和校验值。请保留系统安全设置。
