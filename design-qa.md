# Reference widget design QA

final result: passed

## Comparison scope

This is an update to the user's native desktop widget, not a website or phone
prototype. The supplied phone screenshots are posters containing the desired
desktop card; phone chrome and surrounding poster content are excluded.
The user expressly requested a code-native gradient material. Standard Feather
icons are used for controls, with the upstream license included.

- Source: 用户提供的桌面卡片参考截图.
- Source normalization: poster card at (310,471)-(637,797), measured in the
  945px-wide displayed reference, scaled to the original image dimensions and
  normalized to 240 × 240px for comparison.
- Implementation: `preview-light.png`, actual Qt Quick framebuffer, card crop
  (28,28)-(268,268), 240 logical pixels at device pixel ratio 1.
- Full and focused comparison: `reference-comparison.png`, both source and
  implementation in a single image. The entire card is the focused component.
- State: Chinese, light, 36% primary and 58% weekly sample data. Reset dates and
  plan details are runtime data; screenshot poster annotations are excluded.
- Color states: `preview-palette.png`; compact: `preview-bubble.png`;
  dark: `preview-dark.png`.

## Required visual surfaces

- Typography: system Segoe UI, medium tracking for CODEX · PLUS, large primary
  percentage with a smaller baseline-aligned percent sign, smaller weekly value.
  Hierarchy follows the source. Minor font rasterization differs from iOS.
- Layout: a vertical primary section, thin progress rail, reset caption and a
  separate weekly block. 23px gutters and a 34px superellipse align closely with
  the reference. There is no central rectangle, rectangular glass helper or
  second opaque contour.
- Color: pale blue at 50% and above; pale cream between 10% and 50%; warm peach
  at 10% and below. Blue / warm-orange progress colors follow the quota state.
  The surface is a 97% tinted alpha gradient, with a subtle rim and soft shadow.
- Assets: actual upstream Feather terminal and refresh icons, rendered as
  scalable SVG assets. No poster photograph is used as a fake desktop backdrop.
- Copy: main/weekly remaining, plan and read-only reset-credit details are
  sourced from the current account response. Missing values remain unknown.

## Iteration and validation evidence

1. Previous HWND material introduced four corner wedges and, after an inset
   workaround, a central rectangular plate. Removed that material layer entirely;
   edge, fill and shadow now share one Qt Quick shape. The comparison above is
   the post-fix image.
2. Adjusted primary numeral position and size to restore space above the rail;
   raised surface opacity to keep desktop content from competing with numbers.
3. Found a menu-close path that could strand a hover card expanded. Added a
   deferred pointer check after menu dismissal.
4. Component integration verification (`work/reference-integration.json`): actual
   QML hover expansion and delayed pointer-exit collapse passed; language toggle
   passed; bubble corners are transparent. Card corner alpha is [0,0,4,4], where
   the two lower values are only the diffuse outer shadow (under 2% alpha).
5. Renderer is Direct3D11Rhi. Fifteen core checks passed. A Windows live window
   was inspected and the compact-mode menu action was exercised. Native UI
   capture became inconsistent after window activation, so hover details are
   verified by Qt component events rather than claimed as an OS mouse test.

## Intentional differences and remaining limits

- The card has a soft glass appearance but does not blur live desktop pixels.
  This avoids the compositor artifact present in both previous screenshots.
- The lower-right terminal icon opens settings. Reset credit redemption stays
  in Codex; this widget only shows count and expiry dates.
- Activity means a quota decrease observed between 60-second samples, not a
  real-time agent activity signal.
- Other multi-monitor configurations and Windows logout/login were not
  exhaustively tested. No actionable P0/P1/P2 visual difference remains
  in the compared card; font rasterization is a P3 platform difference.

## Mixed-DPI follow-up — 2026-10-01

- Actual screens: external primary 1920×1080 at 100%; laptop 2560×1600 at 150%.
  Laptop native origin is (1920, -774); Qt logical screen sizes therefore form
  an irregular virtual desktop. The initial direct-position probe did not
  reproduce enlargement, while the old custom drag mixed global coordinates
  from these two different scales and clamped position during DPI transitions.
- Changed to `QWindow.startSystemMove()`. Windows owns the drag and its pointer
  anchor; `WM_EXITSIZEMOVE` finishes the gesture. QML grab cancellation does not
  prematurely finish it. Inertia uses physical cursor samples divided once by
  the current DPR, and samples clear on DPI transitions.
- Qt continues to own `WM_DPICHANGED`. A deferred check restores the canonical
  296×308 logical surface when necessary; it never multiplies that size by DPR.
  Bounds checking waits until dragging ends and respects the current screen.
- A live demo trace captured 8 full mixed-DPI round trips / 16 screen changes,
  with 134 samples and zero invalid sizes. Logical surface stayed 296×308;
  physical surface was 296×308 at 100% and 444×462 at 150%. The last sample
  returned to the primary screen at 96 DPI with dragging flags cleared.
  Evidence: `work/dpi-native-ui.json` in the workspace. The native automation
  capture API reported an invalid screenshot ID, so this evidence is from the
  application's geometry / native drag telemetry, not a claimed successful
  automated pointer replay.
- Three additional component round trips passed (`work/dpi-after.json`). The
  15 existing core tests and the QML hover, collapse, language and transparency
  integration check also passed. Other DPI layouts remain untested.

## Compact card size — 2026-10-01

- At the user's request, the full card is now 200×200 logical pixels. Its
  reference layout is uniformly rendered at 5/6 scale, with a ~28.3px corner,
  ~19.2px content gutter and 45px primary numeral. The compact bubble stays
  72×72. `preview-200.png` shows the current size; older reference comparison
  and palette images document the original 240px design.
- Native hit testing and fixed logical window size were updated together with
  the visual size. Surface is 256×268 at 100%, 384×402 at 150%, including shadow
  margins. Three component round trips across the actual screens returned the
  exact original size (`work/dpi-200.json`). The QML integration check passed
  hover expansion/collapse, language switching and transparent card/bubble
  corners. Card corner alpha was [0,0,4,4].

## Selectable sizes — 2026-10-01

- Added exclusive 180 / 200 / 220 / 240 presets under Card size; 200 remains
  the default. Choice persists and restores on startup. All content and native
  hit testing follow the selected size; the bubble stays 72px.
- Separate immediate size scaling from the hover animation to avoid clipping
  while shrinking. Window constraints, bounds and deferred DPI reconciliation
  all use the selected size.
- `test_widget_sizes.py` passed menu action activation, exclusive selection,
  temporary preference save/load, invalid-value fallback, fresh-controller
  restoration, visible QML card bounds and all four sizes on both actual
  100% and 150% screens. User preferences were isolated from the test.

## Follow startup correction — 2026-10-01

- After the user closed and reopened the client, the watcher process was
  absent although follow was enabled. A logon Run entry alone does not relaunch
  a watcher on each client restart. The prior session-launched process was not
  a sufficient persistence check.
- Resolved the settings file handles in both contexts. The Codex-hosted
  environment redirected LocalAppData to the Codex package's LocalCache; the
  independent process used the ordinary user LocalAppData path. Migrated the
  current follow/codex/220px preferences with backup to the ordinary profile.
- Started the application through local Win32_Process.Create, with hidden
  startup and CREATE_BREAKAWAY_FROM_JOB. The running process's ancestor chain
  is WmiPrvSE → svchost → services → wininit, not the client. A Windows job
  association still exists, so no claim is made that the process is job-free.
  Added source/start-independent.ps1 for future launches from hosted terminals.
- Registered/verified the logon Run command in the independent context. The
  widget read the migrated 220px setting and synced real quota successfully.
- Three simulated stop/restart cycles against the actual Qt window passed
  (`work/follow-window-result.json`). The active client was not shut down by
  the test; a complete real client exit/reopen cycle remains a user check.

## Resource use and pointer recovery — 2026-10-01

- The user clarified that buttons/menus become unresponsive while quota
  continues updating. Found missing completion recovery for native moves,
  plus popup menus without an explicit disposal lifecycle. These are concrete
  interaction gaps; the exact original intermittent failure was not captured.
- Added a 150ms watcher active only during dragging. It uses the actual left
  button state, never times out a held gesture, and releases our QML/native
  capture after a missed move-end. Cancel/capture-change events also request
  recovery. Hiding/closing clears interactions. Menus reuse an active popup
  and delete it after hiding, including all owned submenus/actions.
- Default rendering is software rasterization. Removed shader blur, icon
  colorization, and offscreen MSAA layers. Contours/gradients remain vector
  paths; shadows are generated from the same contour at build time. Icons
  remain SVG with baked tint. Text uses actual logical sizes and native raster
  fonts; small Chinese labels use Microsoft YaHei UI with a 10px minimum.
- Limited consumption pulse to three repeats and disabled UI animations while
  hidden. Client process enumeration now reads names first, then full paths
  only for candidates; valid CLI paths are cached.
- 19 core/GUI checks passed, including all four sizes on both actual monitors,
  12 missed native completion simulations with real QML mouse grabs and later
  button clicks, 20 popup close/open cycles with deferred destruction and
  subsequent clicks, and hiding during a press. Temporary preferences isolate
  these checks from the user's profile.
- Captured 12 frames: three quota palettes, light/dark, 100%/150% DPI. Actual
  framebuffer dimensions and transparent corners passed. Evidence:
  `work/performance-visual.json`. `preview-200.png` is updated to this version.
- Same-machine portable-process initial measurements: before 148.5 MiB working
  set / 124.8 MiB private; after 121.4 / 66.9 MiB. Private memory fell 46.4%.
  A five-second sample after loading showed 0.02% total-machine-normalized CPU.
  These measurements exclude the short-lived quota CLI child.
- Independent Windows launch preserved the ordinary user's 200px setting and
  position and synced real quota. Renderer reported GraphicsApi.Software.
  Long-term stability and the exact user-reported intermittent freeze remain
  real-use checks; no claim is made to have reproduced that original event.
- Final portable build, sampled for 70.06 seconds: working set 122.3–122.6 MiB,
  private memory 67.1–67.6 MiB, average total-machine-normalized CPU 0.011%.
  No working-set trimming was performed. Evidence:
  `work/performance-final-sample.json`, `work/performance-final-live.json`.
  Only the final independent widget instance remained running (PID 59680 at
  measurement time). This sample covers one automatic-query interval; it does
  not establish long-term memory behavior.
- Final executable also passed live Windows UI checks in temporary inspect
  mode: real Codex Plus quota was visible, the settings button opened its
  popup, Escape dismissed it, and clicking refresh entered and then left
  the loading state. The inspection instance was closed and the ordinary
  frameless Tool window relaunched independently through Windows WMI.

## Codex-Glass branding — 2026-10-01

- User selected Codex-Glass as both project and software name. Active project
  is now `outputs/Codex-Glass`; portable program is
  `app/Codex-Glass/Codex-Glass.exe`, with Windows product/file description
  Codex-Glass and version 3.1.0. Window, card heading, tray, notifications,
  CLI client metadata, launcher, build output and manuals use this name.
- Kept the legacy preference folder and single-instance pipe to preserve
  settings and prevent simultaneous old/new instances. Startup Run value is
  now Codex-Glass. Migration recognizes only the packaged legacy watcher,
  backs up its command before removal, and leaves previously disabled or
  unrelated values untouched. Demo, export and ordinary source runs do not
  automatically migrate the packaged startup.
- 22 checks passed, including three new mocked-registry migration tests.
  In the independent Windows context, all actual preferences matched the
  pre-rename snapshot exactly, the old Run value was removed, and the new
  value pointed at the new EXE. Evidence: `work/brand-before.json`,
  `work/brand-after.json`, `work/codex-glass-live.json`.
- Live executable showed Codex-Glass in its window and card, retrieved real
  Codex Plus quota, and reported software rendering. Its Windows resource
  metadata was verified. The temporary inspection instance was closed and
  the ordinary frameless watcher restored for daily use. Old deliverables
  are retained under `work/backup-before-rename` for recovery.


## 2026-10-01 · 3.1.1 Windows 安装与分享版

- GPL-3.0-only 分享版；附项目源码、ICO 素材生成器、PyInstaller / Inno 构建脚本、完整 GPL 与第三方许可。
- Inno Setup 6.7.3 官方编译器下载后验证 Authenticode：Valid，发布者 Pyrsys B.V.，在工作目录内便携使用。
- 当前用户安装，固定 AppId，默认 LocalAppData/Programs/Codex-Glass，无管理员安装模式；可选桌面快捷方式、登录守候；支持覆盖更新与卸载。
- 固定依赖的 PyPI / Qt 上游源码随安装包提供，按官方 SHA-256 校验；包含 Qt 运行所需模块与随包翻译的源码，不附个人偏好或 CLI 登录数据。
- 24 项核心与 GUI 检查通过。新增路径匹配的退出协议检查：不同安装目录、非法 / 不完整命令不能关闭当前副本。
- 打包时过滤本程序不用的 QML 3D、PDF、StateMachine、传感器等插件及传递 DLL；实际运行库约 140 MB，仍默认软件渲染。
- 安装后的 EXE 导出示例卡片成功，实际图片边角与阴影检查正常。
- 安装版真实守候初始化、选定卡片大小、勾选自动守候后的启动路径登记通过。
- 运行中的安装版可正常退出并完成覆盖更新；再次运行后可正常退出并卸载，安装文件 / 卸载登记清理成功，偏好保留。
- 卸载另一目录的安装副本时，正在运行的便携版及其登录启动值保持不变；安装目录里额外放入的未知文件保留。
- 测试通过 WMI 进入正常用户环境，使用工作目录下的专用安装位置；结束后恢复原始偏好 / 启动项，重新运行原便携实例。
- 文档本地链接与 PowerShell 示例语法检查通过；离线 HTML 与项目源码 ZIP 由同一 Markdown / 源码生成。

证据位于本地 `work/installer-test-result.json`、安装 / 更新 / 卸载日志、`installed-widget-preview.png` 和源文件校验清单；这些含本机路径或运行快照的 QA 文件不加入分享包。

当前实际安装环境为 Windows 11 x64，未在其他电脑 / Windows 10 / ARM、真实注销登录后验证；未关闭当前 Codex 会话。没有购买商业签名证书，安装包的信誉提示取决于接收方系统与分发渠道。
