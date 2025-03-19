from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsTextItem
from PyQt5.QtGui import QFont

from .Movable import Movable

class Note(Movable):
    def __init__(self, x, y, id):
        note = QGraphicsTextItem()
        note.setTextInteractionFlags(Qt.TextEditorInteraction)
        note.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        note.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        # Create a QFont object
        font = QFont("Arial", 70, QFont.Bold)
        # Set the font for the QGraphicsTextItem
        note.setFont(font)
        note.setDefaultTextColor(Qt.black)
        note.setHtml('<div style="background-color: gray;">Note</div>')
        note.setPos(x, y)
        self.note = note
        self.id = id
        self.group_id = -1
        bounding_rect = self.note.boundingRect()
        self.center = [x, y]
        self.bbox = [y, x, bounding_rect.width(), bounding_rect.height()]

    @property
    def filename(self):
        return None
    
    def displace(self, dx, dy, back=False):
        self.note.moveBy(dx, dy)

    def draw(self, scene, **kwargs):
        if self.note.scene() is None:
            scene.addItem(self.note)
        else:
            self.note.setPos(self.center[0], self.center[1])

    def undraw(self, scene, **kwargs):
        scene.removeItem(self.note)

    def select(self, scene, **kwargs):
        self.note.setSelected(True)

    def deselect(self, scene, **kwargs):
        self.note.setSelected(False)

    def reapplyTransformsOnVerso(self, rotated=False):
        pass

    def enableIds(self, enable):
        pass