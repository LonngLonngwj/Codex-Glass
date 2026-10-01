"""Regression for live quota updates with a stuck native/QML pointer grab.

Only exercises our own Qt window, with temporary preferences and demo data.
"""
import os
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, Qt, QUrl
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtQuick import QQuickWindow
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from main import GlassView, Controller
import settings


class InteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        QSurfaceFormat.setDefaultFormat(fmt)
        QQuickWindow.setDefaultAlphaBuffer(True)
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='quota-pointer-')
        folder = Path(self.temp.name)
        self.preferences = patch.multiple(settings, FOLDER=folder, FILE=folder/'settings-v2.json')
        self.preferences.start()
        self.args = SimpleNamespace(demo=True, demo_remaining=36, dark=False,
                                    bubble=False, card=True, language='zh', show=True, export=None)
        self.view = GlassView(True)
        self.bridge = Controller(self.app, self.view, self.args)
        self.view.controller = self.bridge
        self.view.rootContext().setContextProperty('bridge', self.bridge)
        self.view.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name('Widget.qml').resolve())))
        self.assertFalse(self.view.errors())
        self.bridge.start()
        self.view.requestActivate()
        QTest.qWait(200)

    def tearDown(self):
        self.bridge.quit()
        self.view.setSource(QUrl())
        self.preferences.stop()
        self.temp.cleanup()

    def point(self, x, y):
        return QPoint(round(28+x*self.bridge.cardScale), round(28+y*self.bridge.cardScale))

    def deferred_deletes(self):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_lost_move_end_recovers_grab_and_buttons(self):
        for _ in range(12):
            QTest.mousePress(self.view, Qt.MouseButton.LeftButton, pos=self.point(110, 155))
            self.assertTrue(self.bridge.dragging)
            self.assertIsNotNone(self.view.mouseGrabberItem())
            # Simulate Windows transferring the grab, but omitting its end event.
            self.bridge.system_drag = True
            self.bridge.drag_started_at = time.monotonic()-.3
            with patch('main.left_button_down', return_value=True):
                self.bridge.recover_pointer()
                self.assertTrue(self.bridge.system_drag, 'Held drag must not be canceled')
            with patch('main.left_button_down', return_value=False):
                self.bridge.recover_pointer()
            self.assertFalse(self.bridge.dragging)
            self.assertFalse(self.bridge.system_drag)
            self.assertFalse(self.bridge.pointer_watch.isActive())
            self.assertIsNone(self.view.mouseGrabberItem())
            QTest.mouseRelease(self.view, Qt.MouseButton.LeftButton, pos=self.point(110, 155))
            before = self.bridge.config['language']
            QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=self.point(175, 30))
            self.assertNotEqual(before, self.bridge.config['language'])

    def test_menu_reuse_cleanup_and_clicks_after_close(self):
        for _ in range(20):
            QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=self.point(200, 215))
            menu = self.bridge.menu
            self.assertIsNotNone(menu)
            self.assertTrue(menu.isVisible())
            self.bridge.openMenu()
            self.assertIs(self.bridge.menu, menu)
            QTest.keyClick(menu, Qt.Key.Key_Escape)
            self.assertIsNone(self.bridge.menu)
            self.deferred_deletes()
            self.assertTrue(sip.isdeleted(menu))
            before = self.bridge.config['language']
            QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=self.point(175, 30))
            self.assertNotEqual(before, self.bridge.config['language'])

    def test_hide_during_drag_clears_interaction(self):
        QTest.mousePress(self.view, Qt.MouseButton.LeftButton, pos=self.point(110, 155))
        self.bridge.hideWindow()
        self.assertFalse(self.view.isVisible())
        self.assertFalse(self.bridge.dragging)
        self.assertFalse(self.bridge.pointer_watch.isActive())
        self.bridge.reveal()
        QTest.qWait(50)
        before = self.bridge.config['language']
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, pos=self.point(175, 30))
        self.assertNotEqual(before, self.bridge.config['language'])


if __name__ == '__main__':
    unittest.main()
