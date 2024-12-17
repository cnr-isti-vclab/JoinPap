

import numpy as np
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem


class MyGText(QGraphicsTextItem):

    focusOut = pyqtSignal()

    def __init__(self, parent=None, scene=None):
        super(QGraphicsTextItem, self).__init__(parent, scene)

    def focusOutEvent(self, event):
        self.focusOut.emit()
        QGraphicsTextItem.focusOutEvent(self,event)


class Grid(QObject):

    def __init__(self, width, height, parent=None):
        super(QObject, self).__init__(parent)

        self.width = width
        self.height = height
        self.nrow = 0
        self.ncol = 0
        self.offx = 0
        self.offy = 0
        self.intercolumn_space = 0
        self.column_width = 0

        self.scene = None
        self.cell_values = None
        self.text_items = {'front': [], 'back': []}
        self.notes = []
        self.grid_rects = {'front': [], 'back': []}


    def save(self):

        dict_to_save = {}

        dict_to_save["width"] = self.width
        dict_to_save["height"] = self.height
        dict_to_save["nrow"] = self.nrow
        dict_to_save["ncol"] = self.ncol
        dict_to_save["offx"] = self.offx
        dict_to_save["offy"] = self.offy
        dict_to_save["column_width"] = self.column_width
        dict_to_save["intercolumn_space"] = self.intercolumn_space
        dict_to_save["cell_values"] = self.cell_values.tolist()
        dict_to_save["notes"] = self.notes

        return dict_to_save

    def fromDict(self, dict):

        self.width = dict["width"]
        self.height = dict["height"]
        self.column_width = dict["column_width"]
        self.nrow = dict["nrow"]
        self.ncol = dict["ncol"]
        self.offx = dict["offx"]
        self.offy = dict["offy"]
        self.intercolumn_space = dict["intercolumn_space"]
        self.cell_values = np.asarray(dict["cell_values"])
        self.notes = dict["notes"]

    def setScene(self, scene):

        self.scene = scene

    def setGrid(self, column_width, ncol, margin_x, margin_y, intercolumn_space):

        self.column_width = column_width
        self.nrow = 1
        self.ncol = ncol
        self.offx = margin_x
        self.offy = margin_y
        self.intercolumn_space = intercolumn_space

        # cells values
        self.cell_values = np.zeros((self.nrow, self.ncol))

    def setGridPosition(self, posx, posy):
        raise NotImplementedError

        self.offx = posx
        self.offy = posy

        for rect in self.grid_rects:
            rect.setPos(self.offx, self.offy)

    def drawGrid(self, reverse=False):
        key = "front" if not reverse else "back"

        if self.scene is not None:

            self.undrawGrid()

            actual_width = self.width - 2 * self.offx
            actual_height = self.height - 2 * self.offy
        
            cell_width = self.column_width
            cell_height = actual_height / self.nrow

            pen_white = QPen(Qt.black, 2, Qt.DashLine)
            pen_white.setCosmetic(True)

            brush = QBrush(Qt.SolidPattern)
            brush.setColor(QColor(255, 255, 255, 0))

            brush25 = QBrush(Qt.DiagCrossPattern)
            brush25.setColor(QColor(255, 255, 255, 200))

            brush50 = QBrush(Qt.SolidPattern)
            brush50.setColor(QColor(255, 255, 255, 125))

            # create cells' rectangles
            for c in range(0, self.ncol):
                for r in range(0, self.nrow):
                    xc = c * (cell_width + self.intercolumn_space) if not reverse else self.width - cell_width - c * (cell_width + self.intercolumn_space)
                    yc = r * cell_height

                    value = self.cell_values[r, c]

                    if value == 0:
                        rect = self.scene.addRect(xc, yc, cell_width, cell_height, pen=pen_white, brush=brush)
                    elif value == 1:
                        rect = self.scene.addRect(xc, yc, cell_width, cell_height, pen=pen_white, brush=brush25)
                    elif value == 2:
                        rect = self.scene.addRect(xc, yc, cell_width, cell_height, pen=pen_white, brush=brush50)

                    rect.setPos(self.offx if not reverse else -self.offx, self.offy)
                    self.grid_rects[key].append(rect)

            # create text graphics item to visualize the notes
            font = QFont("Roboto", 15)
            for note in self.notes:

                x = note["x"]
                y = note["y"]
                txt = note["txt"]

                text_item = MyGText()
                self.scene.addItem(text_item)
                text_item.setPlainText(txt)
                text_item.setFont(font)
                text_item.setDefaultTextColor(Qt.black)
                text_item.setPos(x if not reverse else -x, y)   # TODO: check this if notes will ever be used
                text_item.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsFocusable)
                text_item.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextEditable)
                text_item.setZValue(10)
                text_item.focusOut.connect(self.updateNotes)
                self.text_items[key].append(text_item)


    def setVisible(self, visible=True):
        for key in ["front", "back"]:
            for rect in self.grid_rects[key]:
                rect.setVisible(visible)

            for note in self.text_items[key]:
                note.setVisible(visible)

    def undrawGrid(self):
        for key in ["front", "back"]:
            for rect in self.grid_rects[key]:
                self.scene.removeItem(rect)
            del self.grid_rects[key][:]

            for text_item in self.text_items[key]:
                self.scene.removeItem(text_item)
            del self.text_items[key][:]

    def setOpacity(self, opacity):

        for rect in self.grid_rects:
            rect.setOpacity(opacity)

    def changeCellState(self, x, y, state):
        """
        Assign the cell indexed by the x,y coordinates the given state.
        If state is None the cell cycles between the different states.
        """
        cell_width = self.width / self.ncol
        cell_height = self.height / self.nrow

        c = int((x - self.offx)/ cell_width)
        r = int((y - self.offy) / cell_height)

        if state is None:
            self.cell_values[r, c] = (self.cell_values[r, c] + 1) % 3
        else:
            self.cell_values[r, c] = state

        self.undrawGrid()
        self.drawGrid()

    def addNote(self, x, y, txt):

        note_dict = { "x": x, "y": y, "txt": txt}
        self.notes.append(note_dict)

        self.drawGrid()

    @pyqtSlot()
    def updateNotes(self):
        """
        When a text note is moved or edited the corresponding information are update here
        """

        text_item = self.sender()

        pos = text_item.pos()
        new_x = pos.x()
        new_y = pos.y()
        new_text = text_item.toPlainText()

        index = self.text_items.index(text_item)
        if new_text == "": # remove the note since no text has been inserted
            try:
                del self.notes[index]
            except:
                pass
        else:
            # get the corresponding note information and update it
            note = self.notes[index]
            note["x"] = new_x
            note["y"] = new_y
            note["txt"] = new_text







