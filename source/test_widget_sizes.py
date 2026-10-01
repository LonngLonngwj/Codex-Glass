"""GUI regression check: python -m unittest test_widget_sizes -v.

Uses temporary preferences and demo quota data. Opens only the widget under
test; checks every preset on the currently attached monitors.
"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QObject, QPoint, QRectF, QSize, QUrl
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtQuick import QQuickWindow
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from geometry import CARD, CARD_SIZES, MARGIN, BOTTOM
from main import Controller, GlassView
from native import window_metrics
import settings


class WidgetSizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        QSurfaceFormat.setDefaultFormat(fmt)
        QQuickWindow.setDefaultAlphaBuffer(True)
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_menu_presets_persistence_and_mixed_dpi(self):
        with tempfile.TemporaryDirectory(prefix="quota-size-test-") as directory:
            folder = Path(directory)
            with patch.multiple(settings, FOLDER=folder, FILE=folder/'settings-v2.json'):
                self.assertEqual(settings.load()['card_size'], CARD)
                for invalid in (None, True, '220', 210, 220.0):
                    settings.FILE.write_text(json.dumps({'card_size': invalid}), encoding='utf-8')
                    self.assertEqual(settings.load()['card_size'], CARD)
                settings.save({'card_size': CARD})
                args = SimpleNamespace(demo=True, demo_remaining=36, dark=False,
                                       bubble=False, card=True, language='zh',
                                       show=True, export=None)
                view = GlassView(True)
                bridge = Controller(self.app, view, args)
                view.controller = bridge
                view.rootContext().setContextProperty('bridge', bridge)
                view.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name('Widget.qml').resolve())))
                try:
                    self.assertFalse(view.errors())
                    bridge.start()
                    QTest.qWait(200)
                    # Exercise the real preference-writing path without
                    # starting a provider, follow timer, or real account read.
                    args.demo = False
                    bridge.openMenu()
                    submenu = next(a.menu() for a in bridge.menu.actions() if a.text() == '卡片大小')
                    actions = submenu.actions()
                    self.assertEqual(len(actions), len(CARD_SIZES))
                    self.assertEqual([a.isChecked() for a in actions], [s == CARD for s in CARD_SIZES])
                    screens = self.app.screens()
                    for size in CARD_SIZES:
                        if bridge.menu is None:
                            bridge.openMenu()
                            submenu = next(a.menu() for a in bridge.menu.actions() if a.text() == '卡片大小')
                            actions = submenu.actions()
                        action = actions[CARD_SIZES.index(size)]
                        action.trigger()
                        self.assertEqual(bridge.cardSize, size)
                        self.assertEqual(settings.load()['card_size'], size)
                        self.assertEqual(sum(a.isChecked() for a in actions), 1)
                        bridge.menu.hide()
                        QTest.qWait(200)
                        card = view.rootObject().findChild(QObject, 'fullCard')
                        rect = card.mapRectToScene(QRectF(0, 0, card.width(), card.height()))
                        self.assertAlmostEqual(rect.width(), size, places=3)
                        self.assertAlmostEqual(rect.height(), size, places=3)
                        self.assertEqual(view.rootObject().findChild(QObject, 'compactBubble').width(), 72)
                        for screen in screens + [self.app.primaryScreen()]:
                            point = screen.availableGeometry().center()-QPoint(view.width()//2, view.height()//2)
                            view.setPosition(point)
                            QTest.qWait(200)
                            expected = QSize(size+MARGIN*2, size+MARGIN+BOTTOM)
                            self.assertEqual(view.size(), expected)
                            self.assertEqual(view.minimumSize(), expected)
                            self.assertEqual(view.maximumSize(), expected)
                            self.assertEqual(view.screen(), screen)
                            metrics = window_metrics(view.native_id)
                            if metrics:
                                dpr = view.devicePixelRatio()
                                self.assertEqual(metrics['nativeRect'][2:], [round(expected.width()*dpr), round(expected.height()*dpr)])
                    # A fresh controller must restore the saved selection.
                    args.demo = True
                    restored_view = GlassView(True)
                    restored = Controller(self.app, restored_view, args)
                    restored_view.controller = restored
                    try:
                        self.assertEqual(restored.cardSize, CARD_SIZES[-1])
                        restored.start()
                        self.assertEqual(restored_view.size(), QSize(296, 308))
                    finally:
                        restored.quit()
                    bridge.set_option('card_size', CARD)
                    QTest.qWait(200)
                    self.assertEqual(view.size(), QSize(256, 268))
                finally:
                    bridge.quit()
                    view.setSource(QUrl())


if __name__ == '__main__':
    unittest.main()
