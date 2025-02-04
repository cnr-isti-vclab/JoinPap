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

import os

from PyQt5.QtCore import Qt, QSettings, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QValidator, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QWidget, QColorDialog, QListWidget, QStackedWidget, QComboBox, QSizePolicy, QLineEdit, \
    QLabel, QSpinBox, QCheckBox, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QFileDialog

from .utils import centimetersToPixels, pixelsToCentimeters

class waSettingsWidget(QWidget):

    workingAreaBackgroundChanged = pyqtSignal(str)
    workingAreaPenChanged = pyqtSignal(str, int)
    workingAreaSizeChanged = pyqtSignal(int, int)
    dpisChanged = pyqtSignal(int)

    def __init__(self, settings, taglab_dir, parent=None):
        super(waSettingsWidget, self).__init__(parent)

        self.taglab_dir = taglab_dir

        self.settings = settings

        lbl_dpi = QLabel("Fragments DPI: ")
        self.edit_dpi = QLineEdit()
        self.edit_dpi.setFixedWidth(65)
        self.edit_dpi.setValidator(QIntValidator(50, 32000))

        lbl_working_area = QLabel("Default size (cm): ")
        self.edit_wa_width = QLineEdit()
        self.edit_wa_width.setFixedWidth(65)
        self.edit_wa_width.setValidator(QDoubleValidator(0.0, 32000.0, 2))

        self.edit_wa_height = QLineEdit()
        self.edit_wa_height.setFixedWidth(65)
        self.edit_wa_height.setValidator(QDoubleValidator(0.0, 32000.0, 2))

        layoutH1 = QHBoxLayout()
        layoutH1.addWidget(lbl_working_area)
        layoutH1.addWidget(self.edit_wa_width)
        layoutH1.addWidget(QLabel("width"))
        layoutH1.addSpacing(10)
        layoutH1.addWidget(self.edit_wa_height)
        layoutH1.addWidget(QLabel("height"))

        layoutDPI = QHBoxLayout()
        layoutDPI.addWidget(lbl_dpi)
        layoutDPI.addWidget(self.edit_dpi)
        layoutDPI.addStretch()

        self.workingarea_background_color = "255-255-255"
        self.workingarea_pen_color = "255-255-255"

        self.lbl_workingarea_background_color = QLabel("Background :  ")
        self.lbl_workingarea_border_color = QLabel("Border color :  ")
        self.lbl_workingarea_border_width = QLabel("Border width :  ")

        COLOR_SIZE = 40
        text = "QPushButton:flat {background-color: rgb(255,255,255); border: 1px ;}"

        self.btn_workingarea_background_color = QPushButton()
        self.btn_workingarea_background_color.setFlat(True)
        self.btn_workingarea_background_color.setStyleSheet(text)
        self.btn_workingarea_background_color.setAutoFillBackground(True)
        self.btn_workingarea_background_color.setFixedWidth(COLOR_SIZE)
        self.btn_workingarea_background_color.setFixedHeight(COLOR_SIZE)

        self.btn_workingarea_border_color = QPushButton()
        self.btn_workingarea_border_color.setFlat(True)
        self.btn_workingarea_border_color.setStyleSheet(text)
        self.btn_workingarea_border_color.setAutoFillBackground(True)
        self.btn_workingarea_border_color.setFixedWidth(COLOR_SIZE)
        self.btn_workingarea_border_color.setFixedHeight(COLOR_SIZE)

        self.spinbox_workingarea_border_width = QSpinBox()
        self.spinbox_workingarea_border_width.setFixedWidth(50)
        self.spinbox_workingarea_border_width.setRange(2, 6)
        self.spinbox_workingarea_border_width.setValue(3)

        layout_H2 = QHBoxLayout()
        layout_H2.addWidget(self.lbl_workingarea_background_color)
        layout_H2.addWidget(self.btn_workingarea_background_color)

        layout_H3 = QHBoxLayout()
        layout_H3.addWidget(self.lbl_workingarea_border_color)
        layout_H3.addWidget(self.btn_workingarea_border_color)

        layout_H4 = QHBoxLayout()
        layout_H4.addWidget(self.lbl_workingarea_border_width)
        layout_H4.addWidget(self.spinbox_workingarea_border_width)

        gridlayout = QGridLayout()
        gridlayout.addLayout(layout_H2, 0, 0)
        gridlayout.addLayout(layout_H3, 1, 0)
        gridlayout.addLayout(layout_H4, 1, 1)

        layout = QVBoxLayout()
        layout.addLayout(layoutDPI)
        layout.addLayout(layoutH1)
        layout.addLayout(gridlayout)
        self.setLayout(layout)

        self.btn_workingarea_background_color.clicked.connect(self.chooseWorkingAreaBackgroundColor)
        self.btn_workingarea_border_color.clicked.connect(self.chooseWorkingAreaBorderColor)
        self.spinbox_workingarea_border_width.valueChanged.connect(self.workingAreaBorderWidthChanged)

        self.edit_dpi.textChanged.connect(self.dpiChanged)
        self.edit_wa_width.textChanged.connect(self.widthChanged)
        self.edit_wa_height.textChanged.connect(self.heightChanged)

    @pyqtSlot(str)
    def widthChanged(self, txt):
        if self.edit_wa_width.validator().validate(txt, 0)[0] == QValidator.Acceptable:
            cms = float(txt)
            dpis = self.settings.value("default-dpi", type=int)
            width = centimetersToPixels(cms, dpis)
            self.settings.setValue("default-wa-width", width)
            height = self.settings.value("default-wa-height", type=int)
            self.workingAreaSizeChanged.emit(width, height)

    @pyqtSlot(str)
    def heightChanged(self, txt):
        if self.edit_wa_height.validator().validate(txt, 0)[0] == QValidator.Acceptable:
            cms = float(txt)
            dpis = self.settings.value("default-dpi", type=int)
            height = centimetersToPixels(cms, dpis)
            self.settings.setValue("default-wa-height", height)
            width = self.settings.value("default-wa-width", type=int)
            self.workingAreaSizeChanged.emit(width, height)

    @pyqtSlot(str)
    def dpiChanged(self, txt):
        if self.edit_dpi.validator().validate(txt, 0)[0] == QValidator.Acceptable:
            old_dpi = self.settings.value("default-dpi", type=int)
            new_dpi = int(txt)
            self.settings.setValue("default-dpi", new_dpi)
            width = self.settings.value("default-wa-width", type=int)
            height = self.settings.value("default-wa-height", type=int)
            new_width = width * new_dpi // old_dpi
            new_height = height * new_dpi // old_dpi
            self.workingAreaSizeChanged.emit(new_width, new_height)
            self.dpisChanged.emit(new_dpi)

            self.settings.setValue("default-wa-width", new_width)
            self.settings.setValue("default-wa-height", new_height)

    def setDefaultWAWidth(self, width):
        self.edit_wa_width.blockSignals(True)
        dpis = self.settings.value("default-dpi", type=int)
        cm = pixelsToCentimeters(width, dpis)
        self.edit_wa_width.setText(f"{cm:.2f}")
        self.edit_wa_width.blockSignals(False)
        self.settings.setValue("default-wa-width", width)

    def setDefaultWAHeight(self, height):
        self.edit_wa_height.blockSignals(True)
        dpis = self.settings.value("default-dpi", type=int)
        cm = pixelsToCentimeters(height, dpis)
        self.edit_wa_height.setText(f"{cm:.2f}")
        self.edit_wa_height.blockSignals(False)
        self.settings.setValue("default-wa-height", height)

    def setDefaultDPI(self, dpi):
        self.edit_dpi.blockSignals(True)
        self.edit_dpi.setText(str(dpi))
        self.edit_dpi.blockSignals(False)
        self.settings.setValue("default-dpi", dpi)

    @pyqtSlot()
    def chooseWorkingAreaBackgroundColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setWorkingAreaBackgroundColor(newcolor)

    @pyqtSlot()
    def chooseWorkingAreaBorderColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setWorkingAreaBorderColor(newcolor)

    @pyqtSlot(int)
    def workingAreaBorderWidthChanged(self, value):
        self.setWorkingAreaBorderWidth(value)

    def setWorkingAreaBackgroundColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_workingarea_background_color.setStyleSheet(text)
            self.workingarea_background_color = color

            self.settings.setValue("workingarea-background-color", self.workingarea_background_color)

            self.workingAreaBackgroundChanged.emit(color)

    def workingAreaBackgroundColor(self):

        return self.workingarea_background_color

    def setWorkingAreaBorderColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_workingarea_border_color.setStyleSheet(text)
            self.workingarea_pen_color = color

            self.settings.setValue("workingarea-pen-color", self.workingarea_pen_color)

            workingarea_pen_width = self.spinbox_workingarea_border_width.value()
            self.workingAreaPenChanged.emit(self.workingarea_pen_color, workingarea_pen_width)

    def workingAreaBorderColor(self):

        return self.workingarea_pen_color

    def setWorkingAreaBorderWidth(self, width):

        if self.spinbox_workingarea_border_width.minimum() <= width <= self.spinbox_workingarea_border_width.maximum():
            self.spinbox_workingarea_border_width.setValue(width)
            self.settings.setValue("workingarea-pen-width", width)

            self.workingAreaPenChanged.emit(self.workingarea_pen_color, width)

    def workingAreaBorderWidth(self):

        return self.spinbox_workingarea_width.value()

class drawingSettingsWidget(QWidget):

    borderPenChanged = pyqtSignal(str, int)
    selectionPenChanged = pyqtSignal(str, int)

    def __init__(self, settings, parent=None):
        super(drawingSettingsWidget, self).__init__(parent)

        self.settings = settings

        self.border_pen_color = "0-0-0"
        self.selection_pen_color = "255-255-255"

        self.lbl_border_color = QLabel("Border color :  ")
        self.lbl_selection_color = QLabel("Selection color :  ")

        COLOR_SIZE = 40
        text = "QPushButton:flat {background-color: rgb(255,255,255); border: 1px ;}"

        self.btn_border_color = QPushButton()
        self.btn_border_color.setFlat(True)
        self.btn_border_color.setStyleSheet(text)
        self.btn_border_color.setAutoFillBackground(True)
        self.btn_border_color.setFixedWidth(COLOR_SIZE)
        self.btn_border_color.setFixedHeight(COLOR_SIZE)

        self.btn_selection_color = QPushButton()
        self.btn_selection_color.setFlat(True)
        self.btn_selection_color.setStyleSheet(text)
        self.btn_selection_color.setAutoFillBackground(True)
        self.btn_selection_color.setFixedWidth(COLOR_SIZE)
        self.btn_selection_color.setFixedHeight(COLOR_SIZE)

        self.lblBorderWidth = QLabel("Border width :  ")
        self.lblSelectionWidth = QLabel("Selection width :  ")

        self.spinbox_border_width = QSpinBox()
        self.spinbox_border_width.setFixedWidth(50)
        self.spinbox_border_width.setRange(2, 6)
        self.spinbox_border_width.setValue(3)

        self.spinbox_selection_width = QSpinBox()
        self.spinbox_selection_width.setFixedWidth(50)
        self.spinbox_selection_width.setRange(2, 6)
        self.spinbox_selection_width.setValue(3)

        layout_H1 = QHBoxLayout()
        layout_H1.addWidget(self.lbl_border_color)
        layout_H1.addWidget(self.btn_border_color)

        layout_H2 = QHBoxLayout()
        layout_H2.addWidget(self.lbl_selection_color)
        layout_H2.addWidget(self.btn_selection_color)

        layout_H4 = QHBoxLayout()
        layout_H4.addWidget(self.lblBorderWidth)
        layout_H4.addWidget(self.spinbox_border_width)

        layout_H5 = QHBoxLayout()
        layout_H5.addWidget(self.lblSelectionWidth)
        layout_H5.addWidget(self.spinbox_selection_width)

        layout_V1 = QVBoxLayout()
        layout_V1.addLayout(layout_H1)
        layout_V1.addLayout(layout_H2)

        layout_V2 = QVBoxLayout()
        layout_V2.addLayout(layout_H4)
        layout_V2.addLayout(layout_H5)

        layout_H = QHBoxLayout()
        layout_H.addLayout(layout_V1)
        layout_H.addStretch()
        layout_H.addLayout(layout_V2)

        self.setLayout(layout_H)

        # connections
        self.btn_border_color.clicked.connect(self.chooseBorderColor)
        self.spinbox_border_width.valueChanged.connect(self.borderWidthChanged)
        self.btn_selection_color.clicked.connect(self.chooseSelectionColor)
        self.spinbox_selection_width.valueChanged.connect(self.selectionWidthChanged)

    @pyqtSlot()
    def chooseBorderColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setBorderColor(newcolor)

    @pyqtSlot()
    def chooseSelectionColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setSelectionColor(newcolor)

    @pyqtSlot(int)
    def borderWidthChanged(self, value):
        self.setBorderWidth(value)

    @pyqtSlot(int)
    def selectionWidthChanged(self, value):
        self.setSelectionWidth(value)

    def setBorderColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_border_color.setStyleSheet(text)
            self.border_pen_color = color

            self.settings.setValue("border-pen-color", self.border_pen_color)

            border_pen_width = self.spinbox_border_width.value()
            self.borderPenChanged.emit(self.border_pen_color, border_pen_width)

    def borderColor(self):

        return self.border_pen_color

    def setBorderWidth(self, width):

        if self.spinbox_border_width.minimum() <= width <= self.spinbox_border_width.maximum():
            self.spinbox_border_width.setValue(width)
            self.settings.setValue("border-pen-width", width)

            self.borderPenChanged.emit(self.border_pen_color, width)

    def borderWidth(self):

        return self.spinbox_border_width.value()

    def setSelectionColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_selection_color.setStyleSheet(text)
            self.selection_pen_color = color

            self.settings.setValue("selection-pen-color", self.selection_pen_color)

            selection_pen_width = self.spinbox_selection_width.value()
            self.selectionPenChanged.emit(self.selection_pen_color, selection_pen_width)

    def selectionColor(self):

        return self.selection_pen_color

    def setSelectionWidth(self, width):

        if self.spinbox_selection_width.minimum() <= width <= self.spinbox_selection_width.maximum():
            self.spinbox_selection_width.setValue(width)
            self.settings.setValue("selection-pen-width", width)

            self.selectionPenChanged.emit(self.selection_pen_color, width)

    def selectionWidth(self):

        return self.spinbox_selection_width.value()



class QtSettingsWidget(QWidget):

    accepted = pyqtSignal()

    def __init__(self, taglab_dir, parent=None):
        super(QtSettingsWidget, self).__init__(parent)

        self.settings = QSettings("VCLAB-AIMH", "PIUI")

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        ###### LEFT PART

        self.listwidget = QListWidget()
        self.listwidget.setMaximumWidth(150)
        self.listwidget.addItem("Working Area")
        self.listwidget.addItem("Drawing")

        ###### CENTRAL PART

        self.working_area_settings = waSettingsWidget(self.settings, taglab_dir)
        self.drawing_settings = drawingSettingsWidget(self.settings)

        self.stackedwidget = QStackedWidget()
        self.stackedwidget.addWidget(self.working_area_settings)
        self.stackedwidget.addWidget(self.drawing_settings)

        layoutH = QHBoxLayout()
        layoutH.addWidget(self.listwidget)
        layoutH.addWidget(self.stackedwidget)

        ###########################################################

        # OK button - to simplify exit from the settings

        self.btnOk = QPushButton("Ok")
        self.btnOk.clicked.connect(self.close)

        ###########################################################

        layout_buttons = QHBoxLayout()
        layout_buttons.setAlignment(Qt.AlignRight)
        layout_buttons.addWidget(self.btnOk)

        layout = QVBoxLayout()
        layout.addLayout(layoutH)
        layout.addLayout(layout_buttons)

        self.setLayout(layout)

        # connections
        self.listwidget.currentRowChanged.connect(self.display)

        self.setWindowTitle("Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    def loadSettings(self):

        self.default_dpi = self.settings.value("default-dpi", defaultValue=600, type=int)
        self.default_wa_width = self.settings.value("default-wa-width", defaultValue=20000, type=int)
        self.default_wa_height = self.settings.value("default-wa-height", defaultValue=5000, type=int)

        self.selection_pen_color = self.settings.value("selection-pen-color", defaultValue="255-255-255", type=str)
        self.selection_pen_width = self.settings.value("selection-pen-width", defaultValue=2, type=int)
        self.border_pen_color = self.settings.value("border-pen-color", defaultValue="0-0-0", type=str)
        self.border_pen_width = self.settings.value("border-pen-width", defaultValue=2, type=int)
        self.workingarea_background_color = self.settings.value("workingarea-background-color", defaultValue="160-160-160", type=str)
        self.workingarea_pen_color = self.settings.value("workingarea-pen-color", defaultValue="0-255-0", type=str)
        self.workingarea_pen_width = self.settings.value("workingarea-pen-width", defaultValue=3, type=int)

        self.working_area_settings.setDefaultDPI(self.default_dpi)
        self.working_area_settings.setDefaultWAWidth(self.default_wa_width)
        self.working_area_settings.setDefaultWAHeight(self.default_wa_height)

        self.working_area_settings.setWorkingAreaBackgroundColor(self.workingarea_background_color)
        self.working_area_settings.setWorkingAreaBorderColor(self.workingarea_pen_color)
        self.working_area_settings.setWorkingAreaBorderWidth(self.workingarea_pen_width)

        self.drawing_settings.setBorderColor(self.border_pen_color)
        self.drawing_settings.setBorderWidth(self.border_pen_width)
        self.drawing_settings.setSelectionColor(self.selection_pen_color)
        self.drawing_settings.setSelectionWidth(self.selection_pen_width)

    @pyqtSlot(int)
    def display(self, i):
        self.stackedwidget.setCurrentIndex(i)




