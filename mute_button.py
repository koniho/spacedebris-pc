"""Mute button overlay rendered in pyqtgraph view coordinates."""

import pyqtgraph as pg
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainterPath, QPen


class MuteButton(pg.GraphicsObject):
    """Clickable speaker/mute icon at the bottom-left of the view."""

    SIZE = 28  # diameter in view units
    POS_X = -475
    POS_Y = -300

    COLOR_NORMAL = QColor(200, 200, 200, 160)
    COLOR_HOVER = QColor(255, 255, 255, 220)
    COLOR_MUTED = QColor(220, 80, 80, 200)

    def __init__(self, toggle_callback):
        super().__init__()
        self.toggle_callback = toggle_callback
        self.muted = False
        self._hovered = False
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

    # ------------------------------------------------------------------
    # GraphicsObject interface

    def boundingRect(self):
        s = self.SIZE
        return QRectF(self.POS_X - s / 2, self.POS_Y - s / 2, s, s)

    def paint(self, painter, option, widget=None):
        painter.save()

        cx = self.POS_X
        cy = self.POS_Y
        s = self.SIZE

        # pyqtgraph flips the y-axis; undo it so shapes are right-side-up
        painter.scale(1, -1)
        cy = -cy

        color = (
            self.COLOR_MUTED
            if self.muted
            else (self.COLOR_HOVER if self._hovered else self.COLOR_NORMAL)
        )

        unit = s / 28.0  # scale factor (design at 28 units)

        pen = QPen(color)
        pen.setWidthF(1.8 * unit)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Speaker body (pentagon shape pointing right)
        body = QPainterPath()
        bx = cx - 5 * unit
        body.moveTo(bx, cy + 4 * unit)
        body.lineTo(bx - 4 * unit, cy + 4 * unit)
        body.lineTo(bx - 4 * unit, cy - 4 * unit)
        body.lineTo(bx, cy - 4 * unit)
        body.lineTo(bx + 5 * unit, cy - 9 * unit)
        body.lineTo(bx + 5 * unit, cy + 9 * unit)
        body.closeSubpath()

        painter.fillPath(body, color)
        painter.drawPath(body)

        if not self.muted:
            # Sound waves
            for i, (r, span) in enumerate([(7, 50), (11, 70)]):
                arc_rect = QRectF(
                    (cx + 5) - 5 * unit - r * unit,
                    cy - r * unit,
                    2 * r * unit,
                    2 * r * unit,
                )
                painter.drawArc(arc_rect, -span * 16, span * 2 * 16)
        else:
            # X mark to the right of the speaker
            x0 = cx + 4 * unit
            painter.drawLine(
                int(x0),
                int(cy - 5 * unit),
                int(x0 + 7 * unit),
                int(cy + 5 * unit),
            )
            painter.drawLine(
                int(x0 + 7 * unit),
                int(cy - 5 * unit),
                int(x0),
                int(cy + 5 * unit),
            )

        painter.restore()

    # ------------------------------------------------------------------
    # Interaction

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle()
            event.accept()
        else:
            event.ignore()

    def _toggle(self):
        self.muted = not self.muted
        self.toggle_callback(self.muted)
        self.update()

    def set_muted(self, muted: bool):
        """Sync mute state (e.g. from keyboard shortcut)."""
        self.muted = muted
        self.update()
