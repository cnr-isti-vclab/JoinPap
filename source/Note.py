from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem
from PyQt5.QtGui import QFont, QBrush, QColor, QPen

from .Movable import Movable

class NoteItem(QGraphicsRectItem):
    def __init__(self, text="Double-click to edit", padding=50, parent=None):
        super().__init__(parent)

        self.padding = padding
        self.text_item = QGraphicsTextItem(text, self)
        # Set font size to 70
        font = QFont("Arial", 70)
        self.text_item.setFont(font)

        # Enable text interaction
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        # Connect text change signal to auto-resize
        self.text_item.document().contentsChanged.connect(self.update_rect)

        # Define the background rectangle
        self.update_rect()

        # Make the item selectable and movable
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)

        # Style the background
        self.setBrush(QBrush(QColor(255, 255, 180, 150)))  # Light yellow
        self.setPen(QPen(Qt.black, 1))

    def update_rect(self):
        """Update the background rectangle size and ensure text is properly positioned."""
        text_rect = self.text_item.boundingRect()

        # Set outer rectangle size
        self.setRect(QRectF(
            0, 0,  # Ensure the rectangle starts at (0,0) for proper positioning
            text_rect.width() + 2 * self.padding,
            text_rect.height() + 2 * self.padding
        ))

        # Align the text inside the rectangle
        self.text_item.setPos(self.padding, self.padding)

class Note(Movable):
    def __init__(self, x, y, id):
        note = NoteItem()
        note.setPos(x, y)
        self.note = note
        self.id = id
        self.group_id = -1

    @property
    def bbox(self):
        note_bbox = self.note.boundingRect()
        note_pos = self.note.pos()
        return [note_bbox.y() + note_pos.y(), note_bbox.x() + note_pos.x(), note_bbox.width(), note_bbox.height()]
    
    @bbox.setter
    def bbox(self, bbox):
        self.note.setPos(bbox[1], bbox[0])

    @property
    def center(self):
        note_pos = self.note.pos()
        return [note_pos.x(), note_pos.y()]
    
    @center.setter
    def center(self, center):
        self.note.setPos(center[0], center[1])

    @property
    def filename(self):
        return None
    
    def displace(self, dx, dy, back=False):
        self.note.moveBy(dx, dy)

    def draw(self, scene, **kwargs):
        self.note.setZValue(scene.views()[0].Z_VALUE_NOTE)
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

    def save(self):
        return self.toDict()

    def toDict(self):
        """
        Put the fragment information in a dictionary.
        """

        dict = {}

        # dict["filename"] = self.filename
        # dict["name"] = self.name
        dict["id"] = self.id
        dict["group id"] = self.group_id
        dict["note"] = self.note.text_item.toPlainText()
        dict["bbox"] = self.bbox
        dict["center"] = self.center
        dict["class"] = "note"

        return dict
    
    def fromDict(self, dict):
        """
        Set the blob information given it represented as a dictionary.
        """

        self.id = int(dict["id"])
        self.group_id = int(dict["group id"])
        note_text = dict["note"]
        self.bbox = dict["bbox"]
        self.center = dict["center"]

        self.note.text_item.setPlainText(note_text)
    def save(self):
        return self.toDict()