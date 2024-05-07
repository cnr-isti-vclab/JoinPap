# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2019
# Visual Computing Lab
# ISTI - Italian National Research Council
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.


from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMessageBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout


class QtWorkingAreaWidget(QWidget):

    areaChanged = pyqtSignal(int, int)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super(QtWorkingAreaWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        label_W = QLabel("Width:")
        label_W.setFixedWidth(70)
        label_W.setAlignment(Qt.AlignLeft)

        label_H = QLabel("Height:")
        label_H.setFixedWidth(70)
        label_H.setAlignment(Qt.AlignLeft)

        self.edit_W = QLineEdit()
        self.edit_W.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_W.setFixedWidth(100)

        self.edit_H = QLineEdit()
        self.edit_H.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_H.setFixedWidth(100)

        layout_h2 = QHBoxLayout()
        layout_h2.addWidget(label_W)
        layout_h2.addWidget(self.edit_W)
        layout_h2.addWidget(label_H)
        layout_h2.addWidget(self.edit_H)

        layout_edits = QVBoxLayout()
        layout_edits.addWidget(QLabel("Working area size (in pixel):"))
        layout_edits.addSpacing(10)
        layout_edits.addLayout(layout_h2)

        layout_main_horiz = QHBoxLayout()
        layout_main_horiz.setAlignment(Qt.AlignTop)
        layout_main_horiz.addLayout(layout_edits)

        # Cancel / Apply buttons
        buttons_layout = QHBoxLayout()
        self.btnCancel = QPushButton("Cancel")
        self.btnApply = QPushButton("Apply")
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnApply)
        buttons_layout.addWidget(self.btnCancel)
        self.btnCancel.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(layout_main_horiz)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.setWindowTitle("Working area")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):

        self.closed.emit()
        super(QtWorkingAreaWidget, self).closeEvent(event)

    def setWorkingArea(self, working_area):

        self.edit_W.setText(str(working_area[0]))
        self.edit_H.setText(str(working_area[1]))

    def workingArea(self):

        try:
            w = int(self.edit_W.text())
            h = int(self.edit_H.text())
        except:
            msgBox = QMessageBox()
            msgBox.setText("Invalid values!! Working area not set")
            msgBox.exec()

        return [w, h]
