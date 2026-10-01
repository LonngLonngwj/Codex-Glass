import json
import os
from pathlib import Path
import shutil
import sys
from geometry import CARD, CARD_SIZES

FOLDER = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "QuotaGlass"
FILE = FOLDER / "settings-v2.json"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_NAME = "Codex-Glass"
LEGACY_STARTUP_NAME = "QuotaGlass"
# Preserve the historical preference directory when rebranding.


def load():
    result = {"theme": "light", "follow": True, "target": "both", "topmost": True,
              "alerts": True, "bucket": "codex", "cli": "", "notified": [], "position": None,
              "language": "zh", "mode": "card", "card_size": CARD}
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            result.update({k: data[k] for k in result if k in data})
    except (OSError, ValueError):
        # Migrate only the position, leaving the previous program's settings intact.
        try:
            old = json.loads((FOLDER / "settings.json").read_text(encoding="utf-8-sig"))
            if -20000 < old.get("Left", -100000) < 20000:
                result["position"] = [old["Left"] - 28, old["Top"] - 28]
        except (OSError, ValueError, TypeError):
            pass
    if result["theme"] not in ("light", "dark"):
        result["theme"] = "light"
    if result["target"] not in ("codex", "chatgpt", "both"):
        result["target"] = "both"
    if result["language"] not in ("zh", "en"):
        result["language"] = "zh"
    if result["mode"] not in ("card", "bubble"):
        result["mode"] = "card"
    if type(result["card_size"]) is not int or result["card_size"] not in CARD_SIZES:
        result["card_size"] = CARD
    if not isinstance(result["notified"], list):
        result["notified"] = []
    pos = result["position"]
    if not (isinstance(pos, list) and len(pos) == 2 and all(isinstance(v, (int, float)) and -100000 < v < 100000 for v in pos)):
        result["position"] = None
    return result


def save(data):
    FOLDER.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if FILE.exists():
        shutil.copy2(FILE, FILE.with_suffix(".json.bak"))
    os.replace(tmp, FILE)


def command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --watch'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw}" "{Path(__file__).with_name("main.py")}" --watch'


def startup_enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, STARTUP_NAME)[0] == command()
    except OSError:
        return False


def set_startup(enabled):
    if sys.platform != "win32":
        return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            try:
                previous = winreg.QueryValueEx(key, STARTUP_NAME)[0]
                if previous != command():
                    FOLDER.mkdir(parents=True, exist_ok=True)
                    (FOLDER / "startup-before-v2.txt").write_text(previous, encoding="utf-8")
            except OSError:
                pass
            try:
                legacy = winreg.QueryValueEx(key, LEGACY_STARTUP_NAME)[0]
            except OSError:
                legacy = None
            owned = owns_legacy_startup(legacy)
            if owned:
                FOLDER.mkdir(parents=True, exist_ok=True)
                (FOLDER / "startup-before-rename.json").write_text(
                    json.dumps({LEGACY_STARTUP_NAME: legacy}, ensure_ascii=False, indent=2), encoding="utf-8")
            winreg.SetValueEx(key, STARTUP_NAME, 0, winreg.REG_SZ, command())
            if owned:
                winreg.DeleteValue(key, LEGACY_STARTUP_NAME)
        elif startup_enabled():
            winreg.DeleteValue(key, STARTUP_NAME)


def owns_legacy_startup(value):
    """Recognize only our packaged legacy watcher, never an arbitrary Run value."""
    import re
    from pathlib import PureWindowsPath
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r'\s*"([^"]+)"\s+--watch\s*', value)
    return bool(match and PureWindowsPath(match[1]).name.lower() == "quotaglassqt.exe")


def migrate_startup():
    """Carry enabled startup to this EXE; leave a disabled setup disabled."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            legacy = winreg.QueryValueEx(key, LEGACY_STARTUP_NAME)[0]
    except OSError:
        return False
    if not owns_legacy_startup(legacy):
        return False
    set_startup(True)
    return True
