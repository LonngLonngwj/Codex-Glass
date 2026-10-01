"""Codex-Glass — soft-gradient PyQt6 / Qt Quick desktop widget.

Run: python main.py   |   python main.py --demo --show
Only the existing local Codex app-server is used to retrieve usage.
"""
from __future__ import annotations
import argparse
import ctypes as C
import json
import math
import os
from pathlib import Path
import sys
import time

from PyQt6.QtCore import (QCoreApplication, QObject, QPoint, QSize, QTimer, Qt, QUrl, QVariantAnimation,
                         QEasingCurve, pyqtProperty, pyqtSignal, pyqtSlot)
from PyQt6.QtGui import QActionGroup, QColor, QCursor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap, QSurfaceFormat
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtQuick import QQuickView, QQuickWindow
from PyQt6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon

from geometry import CARD, CARD_SIZES, DESIGN_CARD, DESIGN_RADIUS, MARGIN, BOTTOM, BUBBLE, contour, inside_card, settle_offset, svg_path
from native import IS_WINDOWS, animations_allowed, cursor_pixels, left_button_down, release_window_capture, prepare_alpha_window, window_metrics, user, W
from provider import QuotaProvider, desktop_running
from quota import Lifecycle, Window, alert_key, choose_bucket, demo_snapshot, observed_consumption, tone
import settings
from instance import owns_quit, quit_message


class GlassView(QQuickView):
    def __init__(self, inspect=False):
        super().__init__()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        flags |= Qt.WindowType.Window if inspect else Qt.WindowType.Tool
        self.setFlags(flags)
        self.setColor(QColor("transparent"))
        self.setTitle("Codex-Glass · 柔雾额度卡片")
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.card_size = CARD
        self.logical_size = QSize(CARD + MARGIN * 2, CARD + MARGIN + BOTTOM)
        self.resize(self.logical_size)
        self.setMinimumSize(self.size())
        self.setMaximumSize(self.size())
        self.controller = None
        self.native_id = 0
        self.geometry_timer = QTimer(self)
        self.geometry_timer.setSingleShot(True)
        self.geometry_timer.setInterval(80)
        self.geometry_timer.timeout.connect(self.reconcile_geometry)
        self.screenChanged.connect(self.dpi_changed)
        self.widthChanged.connect(self.check_size)
        self.heightChanged.connect(self.check_size)

    def sync_material(self, *args):
        pass

    def set_card_size(self, size):
        self.card_size = size
        self.logical_size = QSize(size + MARGIN*2, size + MARGIN + BOTTOM)
        # Release the old fixed constraints before shrinking or growing. The
        # canonical size is updated first, so deferred DPI checks use this size.
        self.setMinimumSize(QSize(0, 0))
        self.setMaximumSize(QSize(16777215, 16777215))
        self.resize(self.logical_size)
        self.setMinimumSize(self.logical_size)
        self.setMaximumSize(self.logical_size)

    def check_size(self, *args):
        if self.size() != self.logical_size:
            self.geometry_timer.start()

    def dpi_changed(self, *args):
        # Qt must finish WM_DPICHANGED before we enforce the logical size.
        # Never multiply this size by DPR; Qt already does that for the HWND.
        if self.controller:
            self.controller.glide.stop()
            self.controller.drag_samples.clear()
        self.geometry_timer.start()

    def reconcile_geometry(self):
        if self.size() != self.logical_size:
            self.resize(self.logical_size)
        if self.controller and not self.controller.dragging and not self.controller.closing:
            self.controller.clamp_position(screen=self.screen())

    def nativeEvent(self, event_type, message):
        if IS_WINDOWS:
            msg = W.MSG.from_address(int(message))
            if msg.message == 0x0084 and self.native_id:  # WM_NCHITTEST: transparent margins never block clicks
                rect = W.RECT()
                user.GetWindowRect(self.native_id, C.byref(rect))
                ratio = (rect.right - rect.left) / self.width()
                sx = C.c_short(msg.lParam & 0xffff).value
                sy = C.c_short((msg.lParam >> 16) & 0xffff).value
                x, y = (sx - rect.left)/ratio - MARGIN, (sy - rect.top)/ratio - MARGIN
                compact = self.controller and not self.controller.expanded
                if not inside_card(x, y, size=BUBBLE if compact else self.card_size,
                                   radius=23 if compact else DESIGN_RADIUS*self.card_size/DESIGN_CARD):
                    return True, -1
            elif msg.message in (0x007E, 0x02E0):  # display / DPI change
                self.dpi_changed()
            elif msg.message == 0x0216 and self.controller:  # WM_MOVING, system drag
                self.controller.sample_drag()
            elif msg.message == 0x0232 and self.controller:  # WM_EXITSIZEMOVE
                if self.controller.system_drag:
                    QTimer.singleShot(0, self.controller.finish_system_drag)
            elif msg.message in (0x001F, 0x0215) and self.controller:  # cancel / capture changed
                QTimer.singleShot(0, self.controller.recover_pointer)
        return False, 0


class Controller(QObject):
    changed = pyqtSignal()
    sizeChanged = pyqtSignal()

    def __init__(self, app, view, args):
        super().__init__()
        self.app, self.view, self.args = app, view, args
        self.config = settings.load()
        if args.dark:
            self.config["theme"] = "dark"
        if args.bubble:
            self.config["mode"] = "bubble"
        if args.card:
            self.config["mode"] = "card"
        if args.language:
            self.config["language"] = args.language
        self.expanded = self.config["mode"] != "bubble"
        self.consumption_at = 0
        self.snapshot = demo_snapshot() if args.demo else None
        if args.demo:
            sample = self.snapshot["codex"]
            sample["primary"] = Window(100-args.demo_remaining, 300, time.time()+2*3600+59*60)
            sample["secondary"] = Window(42, 10080, time.time()+3*86400+14*3600)
            sample["plan"] = "plus"
            sample["resetCredits"] = {"availableCount": 1, "expires": [time.time()+10*86400]}
        self.last_good = time.time() if args.demo else None
        self.error = ""
        self.loading = False
        self.next_refresh = 0
        self.life = Lifecycle()
        self.motion = animations_allowed()
        self.dragging = False
        self.system_drag = False
        self.move_started = False
        self.drag_samples = []
        self.drag_origin = self.cursor_origin = QPoint()
        self.pointer_watch = QTimer(self)
        self.pointer_watch.setInterval(150)
        self.pointer_watch.timeout.connect(self.recover_pointer)
        self.drag_started_at = 0
        self.menu = None
        self.closing = False
        self.provider = QuotaProvider(self)
        self.provider.received.connect(self.receive)
        self.provider.failed.connect(self.failed)
        self.provider.busyChanged.connect(self.busy_changed)
        self.glide = QVariantAnimation(self)
        self.glide.setDuration(160)
        self.glide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.glide.valueChanged.connect(lambda p: self.view.setPosition(p))
        self.glide.finished.connect(self.save_position)
        families = QFontDatabase.families()
        self.font = next((f for f in ("Segoe UI Variable", "Segoe UI", "PingFang SC", "Microsoft YaHei UI") if f in families), app.font().family())
        self.label_font = next((f for f in ("Microsoft YaHei UI", "PingFang SC", "Microsoft YaHei") if f in families), self.font)
        self.tray = QSystemTrayIcon(make_icon(), self)
        self.tray.setToolTip("Codex-Glass · Codex 剩余额度")
        self.tray.activated.connect(self.tray_activated)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("显示 / 隐藏浮窗", self.toggle_visible)
        self.tray_menu.addAction("刷新额度", self.refresh)
        self.tray_menu.addAction("外观与设置", self.show_settings)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("退出", self.quit)
        self.tray.setContextMenu(self.tray_menu)
        if not args.export and not args.demo:
            self.tray.show()
        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.tick)
        self.clock = QTimer(self)
        self.clock.setInterval(15000)
        self.clock.timeout.connect(self.changed.emit)

    @pyqtProperty(str, constant=True)
    def fontFamily(self):
        return self.font

    @pyqtProperty(str, constant=True)
    def labelFontFamily(self):
        return self.label_font

    @pyqtProperty(bool, constant=True)
    def isDemo(self):
        return self.args.demo

    @pyqtProperty(bool, constant=True)
    def exporting(self):
        return bool(self.args.export)

    @pyqtProperty(str, constant=True)
    def outline(self):
        return svg_path(size=DESIGN_CARD, radius=DESIGN_RADIUS)

    @pyqtProperty(int, notify=sizeChanged)
    def cardSize(self):
        return self.config["card_size"]

    @pyqtProperty(float, notify=sizeChanged)
    def cardScale(self):
        return self.cardSize / DESIGN_CARD

    @pyqtProperty(str, constant=True)
    def rim(self):
        inner = contour(size=DESIGN_CARD, radius=DESIGN_RADIUS, inset=1.5)
        return self.outline + " M " + " L ".join(f"{x:.4f} {y:.4f}" for x, y in inner) + " Z"

    @pyqtProperty(str, constant=True)
    def bubbleOutline(self):
        return "M " + " L ".join(f"{x:.4f} {y:.4f}" for x, y in contour(size=BUBBLE, radius=23)) + " Z"

    @pyqtSlot(bool)
    def setExpanded(self, value):
        if self.config["mode"] == "card":
            value = True
        if self.dragging or (self.menu and self.menu.isVisible()):
            return
        if value != self.expanded:
            self.expanded = value
            self.changed.emit()

    def collapse_if_outside(self):
        if self.closing or self.config["mode"] != "bubble":
            return
        point = self.view.mapFromGlobal(QCursor.pos())-QPoint(MARGIN, MARGIN)
        if not inside_card(point.x(), point.y(), size=self.cardSize, radius=DESIGN_RADIUS*self.cardScale):
            self.setExpanded(False)

    @pyqtSlot()
    def toggleLanguage(self):
        self.set_option("language", "en" if self.config["language"] == "zh" else "zh")

    @pyqtSlot()
    def toggleMode(self):
        self.set_option("mode", "bubble" if self.config["mode"] == "card" else "card")

    @pyqtProperty("QVariantMap", notify=changed)
    def state(self):
        now = time.time()
        lang = self.config["language"]
        english = lang == "en"
        bucket = choose_bucket(self.snapshot, self.config["bucket"]) if self.snapshot else None
        stale = bool(self.error) or bool(self.last_good and now - self.last_good > 180)
        def column(slot, fallback):
            window = bucket[slot] if bucket else None
            return window.view(now, lang) if window else {"label": fallback, "number": "—", "valid": False, "fraction": 0, "countdown": "No data" if english else "暂无数据", "low": False, "periodLabel": fallback, "reset": 0}
        stamp = time.strftime("%H:%M", time.localtime(self.last_good)) if self.last_good else ""
        expired = bool(bucket and any(bucket[s] and bucket[s].expired(now) for s in ("primary", "secondary")))
        if self.args.demo:
            status = "Demo · sample data" if english else "示例数据"
        elif self.loading:
            status = "Syncing" if english else "正在同步"
        elif stale:
            status = (f"Last {stamp}" if stamp else "Unavailable") if english else (f"上次 {stamp}" if stamp else "暂不可用")
        elif expired:
            status = "Awaiting update" if english else "等待更新"
        elif self.last_good:
            status = f"Synced {stamp}" if english else f"已同步 {stamp}"
        else:
            status = "Awaiting sync" if english else "等待同步"
        detail = self.error or "当前 Codex 登录的订阅额度；每 60 秒读取一次。\n数字为剩余百分比，下方为距重置的时间。"
        if self.last_good:
            detail += "\n最后成功同步：" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_good))
        primary = column("primary", "5-hour" if english else "5 小时")
        secondary = column("secondary", "Weekly" if english else "每周")
        credits = bucket.get("resetCredits") if bucket else None
        weekly_date = time.strftime("%m/%d", time.localtime(secondary["reset"])) if secondary["reset"] else ""
        weekly_date = weekly_date.lstrip("0").replace("/0", "/")
        plan = bucket.get("plan", "") if bucket else ""
        plan = plan.upper().replace("_", " ")[:20]
        consuming = now-self.consumption_at <= 90 and not stale
        activity = ("Recent quota decrease" if english else "检测到额度下降") if consuming else ("Quota synced" if english else "额度已同步")
        activity += (" · sampled every 60 seconds" if english else " · 每 60 秒检测一次")
        return {"primary": primary, "secondary": secondary,
                "dark": self.config["theme"] == "dark", "motion": self.motion, "loading": self.loading,
                "stale": stale, "status": status, "detail": detail,
                "blur": False, "tone": tone(bucket["primary"] if bucket else None, now),
                "english": english, "expanded": self.expanded, "bubbleMode": self.config["mode"] == "bubble",
                "consuming": consuming, "activity": activity,
                "brand": "Codex-Glass" + (" · " + plan if plan else ""),
                "primaryTitle": (primary["periodLabel"] + " remaining") if english else (primary["periodLabel"] + "剩余"),
                "resetCaption": (("resets in " + primary["countdown"]) if primary["valid"] and primary["reset"] else primary["countdown"]) if english else ((primary["countdown"] + "重置") if primary["valid"] and primary["reset"] else primary["countdown"]),
                "weeklyTitle": ("Weekly remaining" if english else "本周剩余") + ((" · until " if english else " · 至 ")+weekly_date if weekly_date else ""),
                "creditsKnown": credits is not None,
                "creditsLabel": ((str(credits["availableCount"])+" reset credit"+("s" if credits["availableCount"] != 1 else "")) if english else str(credits["availableCount"])+" 次重置机会") if credits else ("Reset info" if english else "重置信息"),
                "viewLabel": "View" if english else "查看"}

    def start(self):
        self.view.set_card_size(self.cardSize)
        self.view.create()
        self.view.native_id = int(self.view.winId())
        prepare_alpha_window(self.view.native_id)
        pos = self.config.get("position")
        if pos:
            self.view.setPosition(round(pos[0]), round(pos[1]))
        else:
            self.reset_position(save=False)
        self.clamp_position()
        if not self.config["topmost"]:
            self.apply_topmost()
        self.changed.emit()
        if self.args.demo or self.args.show:
            self.life.reveal()
        if self.args.demo:
            self.view.show()
        else:
            self.tick()
            self.timer.start()
            self.clock.start()
        if self.args.export:
            self.view.show()
            QTimer.singleShot(1000, self.export)

    def tick(self):
        if self.closing:
            return
        running = desktop_running(self.config["target"])
        visible, changed = self.life.update(running, self.config["follow"] and not self.args.show)
        if visible != self.view.isVisible():
            if not visible:
                self.cancel_interaction()
            self.view.setVisible(visible)
            self.view.sync_material()
        if changed and running:
            self.next_refresh = 0
        if (running or visible) and time.time() >= self.next_refresh:
            self.refresh()

    @pyqtSlot()
    def refresh(self):
        if self.args.demo or self.loading or self.closing:
            return
        self.next_refresh = time.time() + 60
        self.provider.refresh(self.config["cli"])

    def busy_changed(self, value):
        self.loading = value
        self.changed.emit()

    def receive(self, snapshot):
        previous = choose_bucket(self.snapshot, self.config["bucket"]) if self.snapshot else None
        if observed_consumption(previous, choose_bucket(snapshot, self.config["bucket"])):
            self.consumption_at = time.time()
        self.snapshot, self.last_good, self.error = snapshot, time.time(), ""
        self.changed.emit()
        self.notify_low()
        self.tray.setToolTip("Codex 剩余 · " + self.state["primary"]["number"] + "% / " + self.state["secondary"]["number"] + "%")

    def failed(self, reason):
        self.error = reason
        self.changed.emit()

    def notify_low(self):
        if not self.config["alerts"] or self.args.demo:
            return
        bucket = choose_bucket(self.snapshot, self.config["bucket"])
        messages = []
        for slot in ("primary", "secondary"):
            w = bucket[slot]
            key = alert_key(w, bucket["id"], slot, time.time(), self.config["notified"])
            if key:
                self.config["notified"].append(key)
                messages.append(f"{w.label}剩余 {w.remaining:.0f}%")
        if messages:
            self.config["notified"] = self.config["notified"][-80:]
            self.save()
            self.tray.showMessage("Codex-Glass 额度提醒", "；".join(messages), QSystemTrayIcon.MessageIcon.Information, 6000)

    @pyqtSlot()
    def dragStart(self):
        self.glide.stop()
        self.dragging = True
        self.system_drag = False
        self.move_started = False
        self.drag_started_at = time.monotonic()
        self.pointer_watch.start()
        self.cursor_origin, self.drag_origin = QCursor.pos(), self.view.position()
        self.drag_samples = []
        self.sample_drag()

    def sample_drag(self):
        if not self.dragging:
            return
        pixels = cursor_pixels()
        cursor = QPoint(*pixels) if pixels is not None else QCursor.pos()
        now = time.monotonic()
        self.drag_samples.append((now, cursor))
        self.drag_samples = [(t, p) for t, p in self.drag_samples if now-t <= .10][-12:]

    @pyqtSlot()
    def dragMove(self):
        if not self.dragging or self.system_drag:
            return
        cursor = QCursor.pos()
        delta = cursor - self.cursor_origin
        if delta.manhattanLength() < QApplication.startDragDistance() and not self.move_started:
            return
        self.move_started = True
        # Let Windows maintain the pointer anchor and per-monitor DPI through
        # the entire gesture. Global Qt coordinates cannot be subtracted across
        # differently scaled Windows monitors as if they were one pixel grid.
        self.system_drag = True
        if self.view.startSystemMove():
            return
        self.system_drag = False
        # Fallback for platforms without a native move operation. Rebase on
        # each step so a DPI transition cannot retain a stale starting size.
        self.view.setPosition(self.drag_origin + delta)
        self.cursor_origin, self.drag_origin = cursor, self.view.position()
        self.sample_drag()

    @pyqtSlot()
    def dragEnd(self):
        # startSystemMove releases the QML mouse grab; its onCanceled is not
        # the end of the Windows move loop. WM_EXITSIZEMOVE finishes it instead.
        if not self.dragging or self.system_drag:
            return
        self.dragging = False
        self.system_drag = False
        self.pointer_watch.stop()
        self.release_pointer()
        self.view.reconcile_geometry()
        now = time.monotonic()
        vx = vy = 0
        if len(self.drag_samples) >= 2 and now - self.drag_samples[-1][0] < .09:
            start, p0 = self.drag_samples[0]
            end, p1 = self.drag_samples[-1]
            if end - start > .01:
                ratio = self.view.devicePixelRatio() if IS_WINDOWS else 1
                vx, vy = (p1.x()-p0.x())/(end-start)/ratio, (p1.y()-p0.y())/(end-start)/ratio
        dx, dy = settle_offset(vx, vy) if self.motion else (0, 0)
        target = self.bounded(self.view.position() + QPoint(dx, dy), screen=self.view.screen())
        if self.motion and target != self.view.position():
            self.glide.setStartValue(self.view.position())
            self.glide.setEndValue(target)
            self.glide.start()
        else:
            self.view.setPosition(target)
            self.save_position()

    def finish_system_drag(self):
        if not self.dragging:
            return
        self.system_drag = False
        self.dragEnd()

    def release_pointer(self):
        item = self.view.mouseGrabberItem()
        if item:
            item.ungrabMouse()
        release_window_capture(self.view.native_id)

    def recover_pointer(self):
        # A native move loop can lose its completion event during DPI/focus
        # changes. Do not time out a held drag: recover only after release.
        if not self.dragging or self.closing:
            self.pointer_watch.stop()
            return
        down = left_button_down()
        if down is None:
            down = bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton)
        if not down and time.monotonic() - self.drag_started_at >= .15:
            self.finish_system_drag()

    def cancel_interaction(self):
        self.pointer_watch.stop()
        self.dragging = self.system_drag = self.move_started = False
        self.drag_samples.clear()
        self.release_pointer()
        if self.menu:
            self.menu.close()

    def bounded(self, pos, screen=None):
        size = self.cardSize
        center = pos + QPoint(MARGIN+size//2, MARGIN+size//2)
        if screen is None:
            screen = self.app.screenAt(center)
        if screen is None:
            # Windows mixed-DPI logical screen rectangles can have gaps.
            # Use the nearest actual screen instead of jumping to the primary.
            def distance(candidate):
                r = candidate.availableGeometry()
                dx = max(r.left()-center.x(), center.x()-r.right(), 0)
                dy = max(r.top()-center.y(), center.y()-r.bottom(), 0)
                return dx*dx+dy*dy
            screen = min(self.app.screens(), key=distance)
        area = screen.availableGeometry()
        return QPoint(max(area.left()-MARGIN+8, min(pos.x(), area.right()-size-MARGIN-8)),
                      max(area.top()-MARGIN+8, min(pos.y(), area.bottom()-size-MARGIN-8)))

    def clamp_position(self, screen=None):
        if not self.dragging:
            self.view.setPosition(self.bounded(self.view.position(), screen=screen))

    @pyqtSlot(int, int)
    def nudge(self, x, y):
        self.glide.stop()
        self.view.setPosition(self.bounded(self.view.position() + QPoint(x, y)))
        self.save_position()

    def reset_position(self, save=True):
        area = self.app.primaryScreen().availableGeometry()
        self.view.setPosition(area.right()-self.cardSize-MARGIN-24, area.bottom()-self.cardSize-MARGIN-24)
        if save:
            self.save_position()

    def save_position(self):
        if self.view.isVisible():
            self.config["position"] = [self.view.x(), self.view.y()]
            self.save()

    def save(self):
        if self.args.demo or self.args.export:
            return
        try:
            settings.save(self.config)
        except OSError:
            self.tray.showMessage("Codex-Glass", "设置暂时无法保存，请检查本地文件权限。")

    def apply_topmost(self):
        if IS_WINDOWS:
            user.SetWindowPos(self.view.native_id, -1 if self.config["topmost"] else -2, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
            self.view.sync_material()

    def set_option(self, name, value):
        if name == "card_size" and (type(value) is not int or value not in CARD_SIZES):
            return
        self.config[name] = value
        if name == "card_size":
            self.glide.stop()
            self.view.set_card_size(value)
            self.sizeChanged.emit()
            self.clamp_position(screen=self.view.screen())
            if self.view.isVisible():
                self.config["position"] = [self.view.x(), self.view.y()]
        if name == "mode":
            self.expanded = value != "bubble"
        if name == "topmost":
            self.apply_topmost()
        self.save()
        self.changed.emit()
        if name in ("target", "follow"):
            self.tick()

    def add_check(self, menu, label, checked, callback):
        action = menu.addAction(label)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(lambda: callback())
        return action

    @pyqtSlot()
    def openMenu(self):
        if self.menu and self.menu.isVisible():
            self.menu.raise_()
            return
        if self.menu:
            old_menu, self.menu = self.menu, None
            old_menu.deleteLater()
        self.recover_pointer()
        menu = QMenu()
        self.menu = menu
        menu.aboutToHide.connect(lambda m=menu: self.menu_closed(m))
        menu.setFont(QFont(self.font, 9))
        dark = self.config["theme"] == "dark"
        tr = lambda zh, en: en if self.config["language"] == "en" else zh
        menu.setStyleSheet("QMenu{background:%s;color:%s;border:1px solid %s;padding:6px;}QMenu::item{padding:7px 23px 7px 12px;border-radius:6px;}QMenu::item:selected{background:%s;}QMenu::separator{height:1px;background:%s;margin:5px 8px;}" %
                           (("#272a30", "#e6eaf1", "#414751", "#3a414d", "#414751") if dark else ("#f9fafc", "#344250", "#dfe4eb", "#e6edf4", "#e3e8ed")))
        menu.addAction(tr("立即刷新    F5", "Refresh    F5"), self.refresh)
        menu.addAction(tr("固定为完整卡片" if self.config["mode"] == "bubble" else "切换为小浮球", "Pin full card" if self.config["mode"] == "bubble" else "Switch to compact bubble"), self.toggleMode)
        menu.addSeparator()
        theme = menu.addMenu(tr("外观", "Appearance"))
        for key, label in (("light", tr("浅色 · 柔雾渐变", "Light · soft gradient")), ("dark", tr("深色 · 柔光", "Dark · soft glow"))):
            self.add_check(theme, label, self.config["theme"] == key, lambda k=key: self.set_option("theme", k))
        sizes = menu.addMenu(tr("卡片大小", "Card size"))
        size_group = QActionGroup(sizes)
        size_group.setExclusive(True)
        for size in CARD_SIZES:
            label = f"{size} × {size}" + (tr("（默认）", " (default)") if size == CARD else "")
            action = self.add_check(sizes, label, self.cardSize == size, lambda s=size: self.set_option("card_size", s))
            size_group.addAction(action)
        modes = menu.addMenu(tr("显示形态", "Display mode"))
        for key, label in (("card", tr("完整卡片", "Full card")), ("bubble", tr("小浮球 · 悬停展开", "Bubble · expand on hover"))):
            self.add_check(modes, label, self.config["mode"] == key, lambda k=key: self.set_option("mode", k))
        language = menu.addMenu("语言 / Language")
        for key, label in (("zh", "中文"), ("en", "English")):
            self.add_check(language, label, self.config["language"] == key, lambda k=key: self.set_option("language", k))
        follow = menu.addMenu(tr("跟随哪个客户端", "Follow client"))
        for key, label in (("both", tr("ChatGPT 或 Codex", "ChatGPT or Codex")), ("codex", tr("仅 Codex", "Codex only")), ("chatgpt", tr("仅 ChatGPT", "ChatGPT only"))):
            self.add_check(follow, label, self.config["target"] == key, lambda k=key: self.set_option("target", k))
        for key, label in (("follow", tr("跟随客户端显示 / 隐藏", "Show and hide with client")), ("topmost", tr("始终置顶", "Always on top")), ("alerts", tr("低额度提醒 · 20% / 10%", "Low quota alerts · 20% / 10%"))):
            self.add_check(menu, label, self.config[key], lambda k=key: self.set_option(k, not self.config[k]))
        self.add_check(menu, tr("登录 Windows 后自动守候", "Start with Windows"), settings.startup_enabled(), self.toggle_startup)
        if self.snapshot and len(self.snapshot) > 1:
            groups = menu.addMenu(tr("额度分组", "Quota group"))
            for key, value in self.snapshot.items():
                self.add_check(groups, value["name"], choose_bucket(self.snapshot, self.config["bucket"])["id"] == key, lambda k=key: self.set_option("bucket", k))
        menu.addSeparator()
        menu.addAction(tr("移到屏幕右下角", "Move to bottom right"), lambda: self.reset_position())
        menu.addAction(tr("选择 Codex CLI…", "Select Codex CLI…"), self.choose_cli)
        menu.addAction(tr("使用说明", "Help"), self.help)
        menu.addSeparator()
        menu.addAction(tr("隐藏浮窗    Esc", "Hide    Esc"), self.hideWindow)
        menu.addAction(tr("退出    Ctrl+Q", "Quit    Ctrl+Q"), self.quit)
        menu.popup(self.view.mapToGlobal(QPoint(MARGIN+self.cardSize-15, MARGIN+46)))

    def menu_closed(self, menu):
        # Give QAction callbacks time to finish before destroying the popup.
        if self.menu is menu:
            self.menu = None
        menu.deleteLater()
        QTimer.singleShot(350, self.collapse_if_outside)

    def toggle_startup(self):
        try:
            settings.set_startup(not settings.startup_enabled())
        except OSError:
            self.tray.showMessage("Codex-Glass", "无法更新当前用户启动项。")

    def choose_cli(self):
        path, _ = QFileDialog.getOpenFileName(None, "选择 Codex CLI", "", "Codex CLI (codex.exe)")
        if path:
            self.set_option("cli", path)
            self.refresh()

    def help(self):
        QMessageBox.information(None, "Codex-Glass", "拖动空白处移动；松手后轻微减速。\nF5 刷新 · Esc 隐藏 · Ctrl+方向键移动\nCtrl+M 菜单 · Ctrl+Q 退出\n\n点击右上角 EN/中 切换语言。\n右下角菜单可切换小浮球；悬停自动展开。\n\n显示的是当前 Codex 账号的订阅额度。")

    @pyqtSlot()
    def showCredits(self):
        bucket = choose_bucket(self.snapshot, self.config["bucket"]) if self.snapshot else None
        credits = bucket.get("resetCredits") if bucket else None
        english = self.config["language"] == "en"
        title = "Reset credits" if english else "重置机会"
        if credits is None:
            body = "The current account has not returned reset credit information." if english else "当前账号未返回重置机会信息。"
        else:
            body = (f"Available: {credits['availableCount']}" if english else f"可用重置机会：{credits['availableCount']} 次")
            for index, expiry in enumerate(credits["expires"], 1):
                date = time.strftime("%Y/%m/%d %H:%M", time.localtime(expiry))
                body += "\n" + (f"{index}. Expires {date}" if english else f"第 {index} 次 · {date} 到期")
            body += "\n\n" + ("Use the Codex client to redeem a reset credit." if english else "需要使用时，请在 Codex 客户端中操作。")
        QMessageBox.information(None, title, body)

    @pyqtSlot()
    def hideWindow(self):
        self.glide.stop()
        self.cancel_interaction()
        self.save_position()
        self.life.hide()
        self.view.hide()

    def reveal(self):
        self.life.reveal()
        self.view.show()
        self.view.requestActivate()
        self.view.sync_material()
        if not self.snapshot:
            self.refresh()

    def toggle_visible(self):
        self.hideWindow() if self.view.isVisible() else self.reveal()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def show_settings(self):
        self.reveal()
        self.openMenu()

    def export(self):
        image = self.view.grabWindow()
        if not image.save(str(Path(self.args.export).resolve())):
            print("Could not save preview", file=sys.stderr)
        self.quit()

    @pyqtSlot()
    def quit(self):
        if self.closing:
            return
        self.closing = True
        self.glide.stop()
        self.cancel_interaction()
        self.save_position()
        self.timer.stop()
        self.clock.stop()
        self.provider.close()
        self.tray.hide()
        self.view.hide()
        self.app.quit()


def make_icon():
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#edf2f7"))
    painter.drawRoundedRect(1, 1, 30, 30, 9, 9)
    painter.setPen(QPen(QColor("#6aaa97"), 3))
    painter.drawArc(7, 7, 18, 18, 90*16, 275*16)
    painter.setPen(QPen(QColor("#9c9bcc"), 2.5))
    painter.drawArc(12, 12, 8, 8, 90*16, 245*16)
    painter.end()
    return QIcon(pix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--bubble", action="store_true")
    parser.add_argument("--card", action="store_true")
    parser.add_argument("--language", choices=("zh", "en"))
    parser.add_argument("--demo-remaining", type=float, default=36)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--export")
    parser.add_argument("--enable-startup", action="store_true")
    parser.add_argument("--disable-startup", action="store_true")
    parser.add_argument("--diagnostic")
    parser.add_argument("--quit", action="store_true")
    parser.add_argument("--quit-if-owned", action="store_true", help="Close only this installation (used by Setup)")
    parser.add_argument("--renderer", choices=("software", "hardware"), default="software")
    args = parser.parse_args()
    if args.quit_if_owned:
        # Run before startup migration or GUI creation. Uninstalling another
        # copy must not change preferences, startup registration or its window.
        core = QCoreApplication(sys.argv)
        socket = QLocalSocket()
        socket.connectToServer("QuotaGlass2-" + os.environ.get("USERNAME", "local"))
        if socket.waitForConnected(250):
            socket.write(quit_message(sys.executable))
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        return 0
    if not args.demo and not args.export:
        try:
            settings.migrate_startup()
        except OSError:
            # Keep the app usable if the optional startup migration fails.
            # The existing Run value stays recoverable in the backup file.
            if sys.stderr:
                print("Codex-Glass: 登录启动项迁移失败，请从菜单重新设置。", file=sys.stderr)
    if args.disable_startup:
        settings.set_startup(False)
        return 0
    if args.enable_startup:
        settings.set_startup(True)
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    # This small, mostly static card needs no 3D driver or offscreen MSAA
    # buffers. QPainter still antialiases the analytic outline at monitor DPI.
    os.environ.setdefault("QT_QUICK_BACKEND", "software" if args.renderer == "software" else "rhi")
    QSurfaceFormat.setDefaultFormat(fmt)
    QQuickWindow.setDefaultAlphaBuffer(True)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Codex-Glass")
    app.setOrganizationName("Codex-Glass")
    app.setWindowIcon(make_icon())
    # Keep the legacy pipe name to prevent old and renamed builds from
    # creating two live instances in the same Windows user session.
    name = "QuotaGlass2-" + os.environ.get("USERNAME", "local")
    server = None
    if not args.demo and not args.export:
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(250):
            if not args.watch or args.quit:
                socket.write(b"quit" if args.quit else b"show")
                socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return 0
        if args.quit:
            return 0
        server = QLocalServer()
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(name):
            QLocalServer.removeServer(name)
            if not server.listen(name):
                return 1
    view = GlassView(args.inspect)
    controller = Controller(app, view, args)
    view.controller = controller
    view.rootContext().setContextProperty("bridge", controller)
    source = Path(__file__).with_name("Widget.qml")
    view.setSource(QUrl.fromLocalFile(str(source.resolve())))
    if view.status() == QQuickView.Status.Error:
        errors = [error.toString() for error in view.errors()]
        if args.diagnostic:
            Path(args.diagnostic).write_text(json.dumps({"startupErrors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
        elif not args.export:
            QMessageBox.critical(None, "Codex-Glass 无法启动", "界面组件无法加载，请保持 app 文件夹完整。\n\n" + "\n".join(errors))
        if sys.stderr:
            print("\n".join(errors), file=sys.stderr)
        return 1
    if server:
        clients = []
        def on_connection():
            client = server.nextPendingConnection()
            clients.append(client)
            buffer = bytearray()
            def read():
                buffer.extend(bytes(client.readAll()))
                message = bytes(buffer)
                if message not in (b"show", b"quit") and not message.endswith(b"\n") and len(message) <= 4096:
                    return
                if message == b"show":
                    controller.reveal()
                elif message == b"quit" or owns_quit(message, sys.executable):
                    controller.quit()
                client.disconnectFromServer()
            client.readyRead.connect(read)
            client.disconnected.connect(lambda: (clients.remove(client) if client in clients else None, client.deleteLater()))
            if client.bytesAvailable():
                read()
        server.newConnection.connect(on_connection)
    app.aboutToQuit.connect(controller.provider.close)
    QTimer.singleShot(0, controller.start)
    if args.diagnostic:
        def diagnostic():
            payload = {"renderer": str(view.rendererInterface().graphicsApi()), "blur": controller.state["blur"],
                       "visible": view.isVisible(), "width": view.width(), "height": view.height(),
                       "card": controller.cardSize, "position": [view.x(), view.y()], "state": controller.state,
                       "screen": view.screen().name(), "dpr": view.devicePixelRatio(),
                       **window_metrics(view.native_id)}
            Path(args.diagnostic).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        QTimer.singleShot(4000, diagnostic)
    result = app.exec()
    # Release the QML object tree while its Python context object is alive.
    view.setSource(QUrl())
    if server:
        server.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
