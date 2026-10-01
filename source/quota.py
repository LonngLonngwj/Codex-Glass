"""Pure quota rules. Unknown is never converted into 100% remaining."""
from __future__ import annotations
import math
import time
from dataclasses import dataclass
from pathlib import PureWindowsPath


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


@dataclass(frozen=True)
class Window:
    used: float
    minutes: int | None
    reset: float | None

    @property
    def remaining(self):
        return min(100.0, max(0.0, 100.0 - self.used))

    def expired(self, now):
        return self.reset is not None and self.reset <= now

    @property
    def label(self):
        if self.minutes == 300:
            return "5 小时"
        if self.minutes == 10080:
            return "每周"
        if not self.minutes:
            return "周期未知"
        if self.minutes >= 1440:
            return f"{self.minutes / 1440:g} 天"
        if self.minutes >= 60:
            return f"{self.minutes / 60:g} 小时"
        return f"{self.minutes} 分钟"

    def countdown(self, now):
        if self.reset is None:
            return "重置时间未知"
        if self.expired(now):
            return "等待同步"
        minutes = max(1, math.ceil((self.reset - now) / 60))
        days, rest = divmod(minutes, 1440)
        hours, mins = divmod(rest, 60)
        if days:
            return f"{days}天 {hours}小时后"
        if hours:
            return f"{hours}小时 {mins}分后"
        return f"{mins}分钟后"

    def view(self, now, language="zh"):
        valid = not self.expired(now)
        label, countdown = self.label, self.countdown(now)
        if language == "en":
            label = "5-hour" if self.minutes == 300 else "Weekly" if self.minutes == 10080 else "Period"
            if self.reset is None:
                countdown = "Reset time unknown"
            elif self.expired(now):
                countdown = "Awaiting update"
            else:
                mins = max(1, math.ceil((self.reset-now)/60))
                days, rest = divmod(mins, 1440)
                hours, minutes = divmod(rest, 60)
                countdown = f"{days}d {hours}h" if days else f"{hours}h {minutes}m" if hours else f"{minutes}m"
        return {"label": self.label, "number": str(math.floor(self.remaining + .5)) if valid else "—",
                "valid": valid, "fraction": self.remaining / 100 if valid else 0,
                "countdown": countdown, "low": valid and self.remaining <= 20,
                "periodLabel": label, "reset": self.reset or 0}


def parse_window(data):
    if not isinstance(data, dict) or number(data.get("usedPercent")) is None:
        return None
    mins, reset = number(data.get("windowDurationMins")), number(data.get("resetsAt"))
    return Window(float(data["usedPercent"]), int(mins) if mins and 0 < mins < 2147483647 else None,
                  float(reset) if reset and 0 < reset < 253402300799 else None)


def parse_snapshot(data):
    if not isinstance(data, dict) or "error" in data:
        raise ValueError("额度响应无效")
    data = data.get("result", data)
    buckets = data.get("rateLimitsByLimitId")
    if not isinstance(buckets, dict) or not buckets:
        legacy = data.get("rateLimits")
        buckets = {legacy.get("limitId") or "codex": legacy} if isinstance(legacy, dict) else {}
    result = {}
    for key, value in buckets.items():
        if isinstance(value, dict):
            result[key] = {"id": key, "name": value.get("limitName") or ("Codex" if key == "codex" else key),
                           "primary": parse_window(value.get("primary")), "secondary": parse_window(value.get("secondary")),
                           "plan": value.get("planType") if isinstance(value.get("planType"), str) else "",
                           "resetCredits": parse_credits(data.get("rateLimitResetCredits"))}
    if not result:
        raise ValueError("账号未返回订阅额度")
    return result


def choose_bucket(snapshot, selected="codex"):
    return snapshot.get(selected) or snapshot.get("codex") or next(iter(snapshot.values()), None)


def parse_credits(data):
    if not isinstance(data, dict) or number(data.get("availableCount")) is None:
        return None
    rows = []
    for item in data.get("credits", []) if isinstance(data.get("credits"), list) else []:
        if isinstance(item, dict) and item.get("status") == "available":
            expiry = number(item.get("expiresAt"))
            if expiry and 0 < expiry < 253402300799:
                rows.append(float(expiry))
    return {"availableCount": max(0, int(data["availableCount"])), "expires": sorted(rows)}


def observed_consumption(previous, current):
    """A decrease within the same quota cycle is evidence of recent use."""
    if not previous or not current:
        return False
    for slot in ("primary", "secondary"):
        before, after = previous.get(slot), current.get(slot)
        if (before and after and before.reset and after.reset
                and abs(before.reset-after.reset) <= 120 and after.used > before.used + .01):
            return True
    return False


def tone(window, now):
    if not window or window.expired(now):
        return "blue"
    return "blue" if window.remaining >= 50 else "cream" if window.remaining > 10 else "peach"


def alert_key(window, bucket, slot, now, previous):
    if window is None or window.reset is None or window.expired(now) or window.remaining > 20:
        return None
    level = 10 if window.remaining <= 10 else 20
    # The server can vary reset timestamps slightly between reads.
    key = {"bucket": bucket, "slot": slot, "level": level, "reset": window.reset}
    for old in previous:
        if (isinstance(old, dict) and old.get("bucket") == bucket and old.get("slot") == slot
                and old.get("level") == level and number(old.get("reset")) is not None
                and abs(old["reset"] - window.reset) <= 120):
            return None
    return key


def desktop_kind(name, exe):
    path = str(exe).replace("/", "\\").lower()
    name = name.lower()
    codex_desktop = ("\\openai.codex_" in path or
                     ("\\openai\\codex\\" in path and "\\bin\\" not in path) or
                     path.endswith("\\codex\\codex.exe"))
    if name in ("chatgpt.exe", "codex.exe") and codex_desktop:
        return "codex"
    if name == "chatgpt.exe":
        return "chatgpt"
    return None


class Lifecycle:
    """Window state reducer; never treats our app-server child as the desktop."""
    def __init__(self):
        self.was_running = False
        self.hidden = False
        self.revealed = False

    def update(self, running, follow=True):
        changed = running != self.was_running
        if changed:
            self.hidden = self.revealed = False
        self.was_running = running
        return (running or not follow or self.revealed) and not self.hidden, changed

    def hide(self):
        self.hidden, self.revealed = True, False

    def reveal(self):
        self.hidden, self.revealed = False, True


def demo_snapshot():
    now = time.time()
    return {"codex": {"id": "codex", "name": "Codex", "primary": Window(53, 300, now + 4*3600 + 38*60),
                      "secondary": Window(14, 10080, now + 3*86400 + 19*3600)}}
