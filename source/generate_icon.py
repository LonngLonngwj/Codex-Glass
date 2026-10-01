"""Build-time only: export the application mark as a multi-resolution ICO."""
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtCore import Qt
from PIL import Image

app = QApplication([])
pix = QPixmap(256, 256)
pix.fill(Qt.GlobalColor.transparent)
painter = QPainter(pix)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.scale(8, 8)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(QColor('#edf2f7'))
painter.drawRoundedRect(1, 1, 30, 30, 9, 9)
painter.setPen(QPen(QColor('#6aaa97'), 3))
painter.drawArc(7, 7, 18, 18, 90*16, 275*16)
painter.setPen(QPen(QColor('#9c9bcc'), 2.5))
painter.drawArc(12, 12, 8, 8, 90*16, 245*16)
painter.end()
target = Path(__file__).with_name('assets') / 'Codex-Glass.ico'
temporary = target.with_suffix('.icon.png')
pix.save(str(temporary))
with Image.open(temporary) as image:
    image.save(target, sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
temporary.unlink()
