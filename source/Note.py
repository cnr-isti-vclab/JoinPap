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
        note.setPlainText('Note')
        note.setPos(x, y)
        self.note = note
        self.id = id

    @property
    def bbox(self):
        bounding_rect = self.note.boundingRect()
        return [bounding_rect.y(), bounding_rect.x(), bounding_rect.width(), bounding_rect.height()]
    
    @property
    def filename(self):
        return None

    def draw(self, scene, **kwargs):
        scene.addItem(self.note)

    def undraw(self, scene, **kwargs):
        scene.removeItem(self.note)

    def select(self, scene, **kwargs):
        pass

    def deselect(self, scene, **kwargs):
        pass

    def reapplyTransformsOnVerso(self, rotated=False):
        pass

    def enableIds(self, enable):
        pass