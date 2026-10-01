"""Bounded read-only JSON-RPC over the user's existing Codex CLI."""
import json
import os
from pathlib import Path
import psutil
from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal
from quota import desktop_kind, parse_snapshot


def desktop_running(target="both"):
    # Names are cheap to enumerate on Windows. Query full executable paths
    # only for matching clients rather than opening every process every 3s.
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name") or ""
            if name.lower() not in ("chatgpt.exe", "codex.exe"):
                continue
            kind = desktop_kind(name, proc.exe() or "")
            if kind and (target == "both" or kind == target):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def find_cli(preferred=""):
    if preferred and Path(preferred).is_file():
        return preferred
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info.get("name") or "").lower() == "codex.exe":
                exe = proc.exe()
                if exe and not desktop_kind("codex.exe", exe) and Path(exe).is_file():
                    return exe
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI/Codex/bin"
    if root.is_dir():
        for folder in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            candidate = folder / "codex.exe"
            if candidate.is_file():
                return str(candidate)
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(folder.strip('"')) / "codex.exe"
        if candidate.is_file() and "windowsapps" not in str(candidate).lower():
            return str(candidate)
    return None


class QuotaProvider(QObject):
    received = pyqtSignal(object)
    failed = pyqtSignal(str)
    busyChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.proc.started.connect(self.initialize)
        self.proc.readyReadStandardOutput.connect(self.consume)
        # Drain diagnostics, but never log or save account/auth payloads.
        self.proc.readyReadStandardError.connect(lambda: self.proc.readAllStandardError())
        self.proc.errorOccurred.connect(self.process_error)
        self.proc.finished.connect(self.process_finished)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(lambda: self.fail("读取超时，稍后再试"))
        self.busy, self.buffer = False, b""
        self.cached_cli = None

    def refresh(self, preferred=""):
        if self.busy or self.proc.state() != QProcess.ProcessState.NotRunning:
            return
        path = preferred if preferred and Path(preferred).is_file() else self.cached_cli
        if not path or not Path(path).is_file():
            path = find_cli(preferred)
        if not path:
            self.failed.emit("未找到 Codex CLI，请在菜单中选择 codex.exe")
            return
        self.cached_cli = path
        self.busy, self.buffer = True, b""
        self.busyChanged.emit(True)
        self.timeout.start(20000)
        self.proc.setProgram(path)
        self.proc.setArguments(["app-server", "--listen", "stdio://"])
        self.proc.start()

    def send(self, obj):
        self.proc.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))

    def initialize(self):
        self.send({"id": 1, "method": "initialize", "params": {"clientInfo": {
            "name": "codex_glass", "title": "Codex-Glass", "version": "3.1.1"}}})

    def consume(self):
        self.buffer += bytes(self.proc.readAllStandardOutput())
        if len(self.buffer) > 2_000_000:
            self.fail("额度响应过大")
            return
        while b"\n" in self.buffer and self.busy:
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                obj = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            if not isinstance(obj, dict) or obj.get("id") not in (1, 2):
                continue
            if "error" in obj:
                self.fail("Codex 暂未返回额度，请检查登录与网络")
                return
            if obj["id"] == 1:
                self.send({"method": "initialized"})
                self.send({"id": 2, "method": "account/rateLimits/read"})
            else:
                try:
                    snapshot = parse_snapshot(obj)
                except (ValueError, TypeError, AttributeError):
                    self.fail("账号没有返回可识别的订阅额度")
                    return
                self.finish()
                self.received.emit(snapshot)

    def finish(self):
        self.timeout.stop()
        self.busy = False
        self.proc.kill()  # Only this tool's own app-server child.
        self.busyChanged.emit(False)

    def fail(self, reason):
        self.finish()
        self.failed.emit(reason)

    def process_error(self, error):
        if self.busy:
            self.fail("本机 Codex 查询无法启动或已中断")

    def process_finished(self, code, status):
        if self.busy:
            self.fail("Codex 查询提前结束，请稍后重试")

    def close(self):
        self.timeout.stop()
        self.busy = False
        self.proc.kill()
        self.proc.waitForFinished(1200)
