from .Tool import Tool
from PyQt5.QtWidgets import QGraphicsLineItem
from PyQt5.QtGui import QPen, QBrush
from PyQt5.QtCore import Qt

class DrawLine(Tool):
    def __init__(self, viewerplus):
        super().__init__(viewerplus)
        self.start_point = None
        self.end_point = None
        self.lines = []
        self.active_line = None

    def leftPressed(self, x, y, mods):
        if self.start_point is None:
            self.start_point = (x, y)
            pen = QPen(Qt.black, 15)
            self.active_line = self.viewerplus.scene.addLine(x, y, x+10, x+10, pen)
            self.active_line.setZValue(1)  # Bring the line on top of all other graphics elements

    def mouseMove(self, x, y):
        if self.start_point is not None:
            self.active_line.setLine(self.start_point[0], self.start_point[1], x, y)

    def leftReleased(self, x, y):
        if self.start_point is not None:
            self.end_point = (x, y)
            print("Line drawn from", self.start_point, "to", self.end_point)

            mid_x = (self.start_point[0] + self.end_point[0]) / 2
            mid_y = (self.start_point[1] + self.end_point[1]) / 2
            text_item = self.viewerplus.scene.addText("Text")
            font = text_item.font()
            font.setPointSize(30)
            text_item.setFont(font)
            text_item.setPos(mid_x + 50, mid_y + 100)
            text_item.setZValue(1)  # Bring the text on top of all other graphics elements
            text_item.setFlag(text_item.ItemIsMovable)
            text_item.setTextInteractionFlags(Qt.TextEditorInteraction)

            self.lines.append({"line": self.active_line, "text": text_item})
            self.start_point = None
            self.active_line = None


# Example usage:
# tool = DrawLine()
# tool.on_click(10, 10)
# tool.on_click(20, 20)