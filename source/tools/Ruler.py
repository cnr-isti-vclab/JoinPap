from .Tool import Tool
from PyQt5.QtWidgets import QGraphicsLineItem
from PyQt5.QtGui import QPen, QBrush, QImage, QPixmap, QTextCharFormat, QColor, QTextCursor
from PyQt5.QtCore import Qt
from ..utils import pixelsToCentimeters
from PyQt5.QtGui import QPixmap, QIcon

class Ruler(Tool):
    def __init__(self, viewerplus):
        super().__init__(viewerplus)
        self.start_point = None
        self.line = None
        self.endpoints = None
        self.text = None

    def applyTextBackground(self):
        # Modify the text format
        cursor = self.text.textCursor()
        format = QTextCharFormat()
        format.setBackground(QColor("yellow"))  # Set background color
        cursor.select(QTextCursor.Document)
        cursor.mergeCharFormat(format)

    def leftPressed(self, x, y, mods):
        if self.line is not None:
            self.viewerplus.scene.removeItem(self.line)
            self.viewerplus.scene.removeItem(self.text)
            for endpoint in self.endpoints:
                self.viewerplus.scene.removeItem(endpoint)

        if self.start_point is None:
            self.start_point = (x, y)

            # Create a dashed line
            pen = QPen(Qt.darkGray, 15)
            pen.setStyle(Qt.DashLine)
            self.line = self.viewerplus.scene.addLine(x, y, x, y, pen)
            self.line.setZValue(self.viewerplus.Z_VALUE_SELECTION_RECT)  # Bring the line on top of all other graphics elements

            # Create the text
            self.text = self.viewerplus.scene.addText("0.00 cm")
            font = self.text.font()
            font.setPointSize(70)
            self.text.setFont(font)
            self.text.setPos(x, y)
            self.text.setZValue(self.viewerplus.Z_VALUE_SELECTION_RECT)  # Bring the text on top of all other graphics elements
            self.applyTextBackground()

            # Create the two spherical endpoints
            cross = QPixmap("icons/cross.png")
            self.endpoints = [self.viewerplus.scene.addPixmap(cross) for _ in range(2)]
            for endpoint in self.endpoints:
                endpoint.setOffset(-cross.width() / 2, -cross.height() / 2)
                endpoint.setPos(x, y)
                endpoint.setZValue(self.viewerplus.Z_VALUE_SELECTION_RECT + 1)

    def mouseMove(self, x, y):
        if self.start_point is not None:
            self.line.setLine(self.start_point[0], self.start_point[1], x, y)
            self.text.setPos((x + self.start_point[0]) / 2, (y + self.start_point[1]) / 2)

            distance_px = ((x - self.start_point[0]) ** 2 + (y - self.start_point[1]) ** 2) ** 0.5
            distance_cm = pixelsToCentimeters(distance_px, self.viewerplus.project.dpis)
            self.text.setPlainText("{:.2f} cm".format(distance_cm))
            self.applyTextBackground()

            self.endpoints[1].setPos(x, y)

    def leftReleased(self, x, y):
        self.start_point = None

    def reset(self):
        if self.line is not None:
            self.viewerplus.scene.removeItem(self.line)
            self.viewerplus.scene.removeItem(self.text)
            for endpoint in self.endpoints:
                self.viewerplus.scene.removeItem(endpoint)
        self.start_point = None

# Example usage:
# tool = DrawLine()
# tool.on_click(10, 10)
# tool.on_click(20, 20)