#
# PapyrLab
# Papyrus Intelligent User Interface for Assembling Fragments and Analysis
#
# Copyright(C) 2022
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
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

# Python MODULES
import sys
import os
import glob
import json
import time
import timeit
import datetime
import shutil
import json
import math
import numpy as np
import urllib
import platform

# Qt MODULES
from PyQt5.QtCore import Qt, QSize, QMargins, QDir, QPoint, QPointF, QRectF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo, QModelIndex
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QKeySequence, QPen, QImageReader, QImage
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog, QMenuBar, QMenu, QSizePolicy, QScrollArea, \
    QLabel, QToolButton, QPushButton, QSlider, QCheckBox, \
    QMessageBox, QGroupBox, QLayout, QHBoxLayout, QVBoxLayout, QFrame, QDockWidget, QTextEdit, QAction

# CUSTOM MODULES

from source.QtImageViewerPlus import QtImageViewerPlus
from source.QtSettingsWidget import QtSettingsWidget
from source.QtWorkingAreaWidget import QtWorkingAreaWidget
from source.QtHelpWidget import QtHelpWidget
from source.Fragment import Fragment
from source.Project import Project
from source.QtGridWidget import QtGridWidget
from source.QtPanelInfo import QtPanelInfo
from source.QtImageSetWidget import QtImageSetWidget

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        pass

    def closeEvent(self, event):

        papyrlab = self.centralWidget()
        box = QMessageBox()
        reply = box.question(self, papyrlab.PAPYRLAB_VERSION, "Do you want to save changes?",
                                QMessageBox.Cancel | QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if papyrlab.project.filename is not None:
                papyrlab.saveProject()
            else:
                papyrlab.saveAsProject()

        if reply == QMessageBox.Cancel:
            event.ignore()
            return

        super(MainWindow, self).closeEvent(event)

class PapyrLab(QMainWindow):

    def __init__(self, parent=None):
        super(PapyrLab, self).__init__(parent)

        ##### CUSTOM STYLE #####

        self.setStyleSheet("background-color: rgb(55,55,55); color: white")

        ##### DATA INITIALIZATION AND SETUP #####

        self.papyrlab_dir = os.getcwd()

        current_version = "0.2"
        self.PAPYRLAB_VERSION = "PapyrLab " + current_version

        print(self.PAPYRLAB_VERSION)

        # SETTINGS
        self.settings_widget = QtSettingsWidget(self.papyrlab_dir)

        self.settings_widget.loadSettings()
        default_width = self.settings_widget.default_wa_width
        default_height = self.settings_widget.default_wa_height

        # create a new empty project
        self.project = Project(default_width, default_height)

        self.recentFileActs = []
        self.maxRecentFiles = 4
        self.separatorRecentFilesAct = None

        ##### INTERFACE #####
        #####################

        self.working_area_widget = None

        self.progress_bar = None
        self.gridWidget = None
        self.contextMenuPosition = None

        ##### LAYOUT EDITING TOOLS (VERTICAL)

        flatbuttonstyle1 = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid darkgray;         }
        QToolTip { background-color: white; color: rgb(100,100,100); }
        """

        flatbuttonstyle2 = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid rgb(255,100,100); }
        QToolTip { background-color: white; color: rgb(100,100,100); }
        """


        self.btnPan                = self.newButton("hand.png",    "Pan/Zoom",              flatbuttonstyle1, self.pan)
        self.btnMove               = self.newButton("move.png",    "Move/Rotate fragment",  flatbuttonstyle1, self.move)
        self.btnFreehand           = self.newButton("pencil.png",  "Freehand border",       flatbuttonstyle1, self.freehand)
        self.btnEditBorder         = self.newButton("edit.png",    "Edit border",           flatbuttonstyle1, self.editBorder)
        self.btnEvaluation         = self.newButton("auto.png",    "Evaluate/suggest",      flatbuttonstyle2, self.evaluation)

        # Split Screen operation removed from the toolbar
        self.pxmapSeparator = QPixmap("icons/separator.png")
        self.labelSeparator = QLabel()
        self.labelSeparator.setPixmap(self.pxmapSeparator.scaled(QSize(35, 30)))
        self.btnCreateGrid = self.newButton("grid.png", "Create grid",  flatbuttonstyle1, self.createGrid)
        self.btnGrid = self.newButton("grid-edit.png", "Active/disactive grid operations", flatbuttonstyle1, self.toggleGrid)
        self.pxmapSeparator2 = QPixmap("icons/separator.png")
        self.labelSeparator2 = QLabel()
        self.labelSeparator2.setPixmap(self.pxmapSeparator2.scaled(QSize(35, 30)))

        self.btnSplitScreen = self.newButton("split.png", "Split screen", flatbuttonstyle1, self.toggleSplitScreen)

        layout_tools = QVBoxLayout()
        layout_tools.setSpacing(0)
        layout_tools.addWidget(self.btnPan)
        layout_tools.addWidget(self.btnMove)
        layout_tools.addWidget(self.btnFreehand)
        layout_tools.addWidget(self.btnEditBorder)
        layout_tools.addWidget(self.btnEvaluation)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.labelSeparator)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.btnCreateGrid)
        layout_tools.addWidget(self.btnGrid)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.labelSeparator2)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.btnSplitScreen)

        layout_tools.addStretch()

        # CONTEXT MENU ACTIONS

        self.markEmpty = self.newAction("Mark cell as empty",  "",   self.markEmptyOperation)
        self.markIncomplete = self.newAction("Mark cell as incomplete", "",   self.markIncompleteOperation)
        self.markComplete = self.newAction("Mark cell as complete", "",   self.markCompleteOperation)
        self.addNote = self.newAction("Add/edit note", "",   self.addNoteOperation)

        self.groupAction        = self.newAction("Group",    "G",  self.groupOperation)
        self.ungroupAction      = self.newAction("Ungroup",  "U",  self.ungroupOperation)

        # VIEWERPLUS

        # main viewer
        self.viewerplus = QtImageViewerPlus(self.papyrlab_dir, self)
        self.viewerplus.viewUpdated.connect(self.updateViewInfo)
        self.viewerplus.activated.connect(self.setActiveViewer)
        self.viewerplus.updateInfoPanel[Fragment].connect(self.updatePanelInfo)
        self.viewerplus.mouseMoved[float, float].connect(self.updateMousePos)
        self.viewerplus.selectionChanged.connect(self.updateEditActions)
        self.viewerplus.selectionReset.connect(self.resetPanelInfo)
        self.viewerplus.updateAllViewers.connect(self.updateAllViewers)

        # secondary viewer in SPLIT MODE
        self.viewerplus2 = QtImageViewerPlus(self.papyrlab_dir, self)
        self.viewerplus2.viewUpdated.connect(self.updateViewInfo)
        self.viewerplus2.activated.connect(self.setActiveViewer)
        self.viewerplus2.updateInfoPanel[Fragment].connect(self.updatePanelInfo)
        self.viewerplus2.mouseMoved[float, float].connect(self.updateMousePos)
        self.viewerplus2.selectionChanged.connect(self.updateEditActions)
        self.viewerplus2.selectionReset.connect(self.resetPanelInfo)
        self.viewerplus2.updateAllViewers.connect(self.updateAllViewers)

        self.activeviewer = None

        ###### LAYOUT MAIN VIEW

        self.lblSlider = QLabel("Transparency: 0%")
        self.sliderTransparency = QSlider(Qt.Horizontal)
        self.sliderTransparency.setFocusPolicy(Qt.StrongFocus)
        self.sliderTransparency.setMinimumWidth(200)
        self.sliderTransparency.setStyleSheet(slider_style2)
        self.sliderTransparency.setMinimum(0)
        self.sliderTransparency.setMaximum(100)
        self.sliderTransparency.setValue(0)
        self.sliderTransparency.setTickInterval(10)
        self.sliderTransparency.valueChanged[int].connect(self.sliderTransparencyChanged)

        self.checkBoxBorders = QCheckBox("Boundaries")
        self.checkBoxBorders.setChecked(True)
        self.checkBoxBorders.setFocusPolicy(Qt.NoFocus)
        self.checkBoxBorders.setMinimumWidth(40)
        self.checkBoxBorders.stateChanged[int].connect(self.viewerplus.toggleBorders)
        self.checkBoxBorders.stateChanged[int].connect(self.viewerplus2.toggleBorders)
        self.checkBoxBorders.stateChanged[int].connect(self.saveGuiPreferences)

        self.checkBoxIds = QCheckBox("Ids")
        self.checkBoxIds.setChecked(True)
        self.checkBoxIds.setFocusPolicy(Qt.NoFocus)
        self.checkBoxIds.setMinimumWidth(40)
        self.checkBoxIds.stateChanged[int].connect(self.viewerplus.toggleIds)
        self.checkBoxIds.stateChanged[int].connect(self.viewerplus2.toggleIds)
        self.checkBoxIds.stateChanged[int].connect(self.saveGuiPreferences)

        self.checkBoxGrid = QCheckBox("Grid")
        self.checkBoxGrid.setMinimumWidth(40)
        self.checkBoxGrid.setFocusPolicy(Qt.NoFocus)
        self.checkBoxGrid.stateChanged[int].connect(self.viewerplus.toggleGrid)
        self.checkBoxGrid.stateChanged[int].connect(self.viewerplus2.toggleGrid)
        self.checkBoxGrid.stateChanged[int].connect(self.saveGuiPreferences)

        self.labelZoom = QLabel("Zoom:")
        self.labelMouseLeft = QLabel("x:")
        self.labelMouseTop = QLabel("y:")

        self.labelZoomInfo = QLabel("100%")
        self.labelMouseLeftInfo = QLabel("0")
        self.labelMouseTopInfo = QLabel("0")
        self.labelZoomInfo.setMinimumWidth(70)
        self.labelMouseLeftInfo.setMinimumWidth(70)
        self.labelMouseTopInfo.setMinimumWidth(70)


        layout_header = QHBoxLayout()
        layout_header.addStretch()
        layout_header.addWidget(self.checkBoxBorders)
        layout_header.addWidget(self.checkBoxIds)
        layout_header.addWidget(self.checkBoxGrid)
        layout_header.addStretch()
        layout_header.addWidget(self.labelZoom)
        layout_header.addWidget(self.labelZoomInfo)
        layout_header.addWidget(self.labelMouseLeft)
        layout_header.addWidget(self.labelMouseLeftInfo)
        layout_header.addWidget(self.labelMouseTop)
        layout_header.addWidget(self.labelMouseTopInfo)


        layout_viewers = QHBoxLayout()
        layout_viewers.addWidget(self.viewerplus)
        layout_viewers.addWidget(self.viewerplus2)
        layout_viewers.setStretchFactor(self.viewerplus, 1)
        layout_viewers.setStretchFactor(self.viewerplus2, 1)

        layout_main_view = QVBoxLayout()
        layout_main_view.setSpacing(1)
        layout_main_view.addLayout(layout_header)
        layout_main_view.addLayout(layout_viewers)

        ##### LAYOUT - labels + blob info

        groupbox_style = "QGroupBox\
          {\
              border: 2px solid rgb(40,40,40);\
              border-radius: 0px;\
              margin-top: 10px;\
              margin-left: 0px;\
              margin-right: 0px;\
              padding-top: 5px;\
              padding-left: 5px;\
              padding-bottom: 5px;\
              padding-right: 5px;\
          }\
          \
          QGroupBox::title\
          {\
              subcontrol-origin: margin;\
              subcontrol-position: top center;\
              padding: 0 0px;\
          }"


        # IMAGE SET WIDGET
        self.image_set_widget = QtImageSetWidget(self.project, self)

        # BLOB INFO
        self.groupbox_panelinfo = QtPanelInfo()

        # DOCKS

        self.imagesetdock = QDockWidget("Fragments", self)
        self.imagesetdock.setWidget(self.image_set_widget)
        self.imagesetdock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.imagesetdock)

        self.infodock = QDockWidget("Region Info", self)
        self.infodock.setWidget(self.groupbox_panelinfo)
        self.infodock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.infodock)

        self.setDockOptions(self.AnimatedDocks)

        ##### MAIN LAYOUT

        central_widget_layout = QHBoxLayout()
        central_widget_layout.addLayout(layout_tools)
        central_widget_layout.addLayout(layout_main_view)

        #main_view_splitter = QSplitter()
        central_widget = QWidget()
        central_widget.setLayout(central_widget_layout)
        self.setCentralWidget(central_widget)

        self.filemenu = None
        self.submenuWorkingArea = None
        self.submenuExport = None
        self.submenuImport = None
        self.helpmenu = None

        self.setMenuBar(self.createMenuBar())

        self.setProjectTitle("NONE")

        ##### FURTHER INITIALIZAION #####
        #################################

        # set default opacity
        self.sliderTransparency.setValue(50)
        self.transparency_value = 0.5

        # EVENTS-CONNECTIONS

        self.settings_widget.drawing_settings.borderPenChanged[str, int].connect(self.viewerplus.setBorderPen)
        self.settings_widget.drawing_settings.selectionPenChanged[str, int].connect(self.viewerplus.setSelectionPen)
        self.settings_widget.working_area_settings.workingAreaBackgroundChanged[str].connect(
            self.viewerplus.setWorkingAreaBackgroundColor)
        self.settings_widget.working_area_settings.workingAreaPenChanged[str, int].connect(self.viewerplus.setWorkingAreaPen)

        self.settings_widget.drawing_settings.borderPenChanged[str, int].connect(self.viewerplus2.setBorderPen)
        self.settings_widget.drawing_settings.selectionPenChanged[str, int].connect(self.viewerplus2.setSelectionPen)
        self.settings_widget.working_area_settings.workingAreaBackgroundChanged[str].connect(
            self.viewerplus2.setWorkingAreaBackgroundColor)
        self.settings_widget.working_area_settings.workingAreaPenChanged[str, int].connect(self.viewerplus2.setWorkingAreaPen)

        # views synchronization
        #self.viewerplus.viewHasChanged[float, float, float].connect(self.viewerplus2.setViewParameters)
        #self.viewerplus2.viewHasChanged[float, float, float].connect(self.viewerplus.setViewParameters)

        self.viewerplus.customContextMenuRequested.connect(self.openContextMenu)
        self.viewerplus2.customContextMenuRequested.connect(self.openContextMenu)

        # re-load settings to setup the viewers
        self.settings_widget.loadSettings()

        # SWITCH IMAGES
        self.current_image_index = 0

        # menu options
        self.mapActionList = []
        self.image2update = None

        # a dirty trick to adjust all the size..
        self.showMinimized()
        self.showMaximized()

        # autosave timer
        self.timer = QTimer(self)

        self.updateToolStatus()

        self.split_screen_flag = False
        self.update_panels_flag = True
        self.counter = 0
        self.disableSplitScreen()

        self.setGuiPreferences()

        self.viewerplus.disableBackVisualization()
        self.viewerplus2.enableBackVisualization()
        self.viewerplus.setProject(self.project)
        self.viewerplus2.setProject(self.project)
        self.pan()

        #self.viewerplus.autoZoom()

    def setGuiPreferences(self):

        settings = QSettings("VCLAB-AIMH", "PapyrLab")
        value = settings.value("gui-checkbox-borders", type=bool, defaultValue=True)
        self.checkBoxBorders.setChecked(value)
        value = settings.value("gui-checkbox-ids", type=bool, defaultValue=True)
        self.checkBoxGrid.setChecked(value)
        value = settings.value("gui-checkbox-grid", type=bool, defaultValue=False)
        self.checkBoxIds.setChecked(value)

    @pyqtSlot()
    def saveGuiPreferences(self):

        settings = QSettings("VCLAB-AIMH", "PapyrLab")
        settings.setValue("gui-checkbox-borders", self.checkBoxBorders.isChecked())
        settings.setValue("gui-checkbox-ids", self.checkBoxIds.isChecked())
        settings.setValue("gui-checkbox-grid", self.checkBoxGrid.isChecked())


    #just to make the code less verbose
    def newAction(self, text, shortcut, callback):
        action  = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        #compatibility with Qt < 5.10
        if hasattr(action, 'setShortcutVisibleInContextMenu'):
            action.setShortcutVisibleInContextMenu(True)
        action.triggered.connect(callback)
        return action

    def newButton(self, icon, tooltip, style, callback):
        #ICON_SIZE = 48
        ICON_SIZE = 35
        BUTTON_SIZE = 35

        button = QPushButton()
        button.setEnabled(True)
        button.setCheckable(True)
        button.setFlat(True)
        button.setStyleSheet(style)
        button.setMinimumWidth(ICON_SIZE)
        button.setMinimumHeight(ICON_SIZE)
        button.setIcon(QIcon(os.path.join("icons", icon)))
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setMaximumWidth(BUTTON_SIZE)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

    @pyqtSlot()
    def updateEditActions(self):

        if self.btnGrid.isChecked():
            self.markEmpty.setVisible(True)
            self.markComplete.setVisible(True)
            self.markIncomplete.setVisible(True)
            self.addNote.setVisible(True)
        else:
            self.markEmpty.setVisible(False)
            self.markComplete.setVisible(False)
            self.markIncomplete.setVisible(False)
            self.addNote.setVisible(False)

        nSelected = len(self.viewerplus.selected_fragments) + len(self.viewerplus2.selected_fragments)
        self.groupAction.setEnabled(nSelected > 1)
        self.ungroupAction.setEnabled(nSelected > 1)

    @pyqtSlot()
    def markEmptyOperation(self):
        if self.contextMenuPosition is not None:
            self.activeviewer.updateCellState(self.contextMenuPosition.x(),self.contextMenuPosition.y(), 0)

    @pyqtSlot()
    def markIncompleteOperation(self):
        if self.contextMenuPosition is not None:
            self.activeviewer.updateCellState(self.contextMenuPosition.x(),self.contextMenuPosition.y(), 1)

    @pyqtSlot()
    def markCompleteOperation(self):
        if self.contextMenuPosition is not None:
            self.activeviewer.updateCellState(self.contextMenuPosition.x(), self.contextMenuPosition.y(), 2)

    @pyqtSlot()
    def addNoteOperation(self):

        if self.contextMenuPosition is not None and self.btnGrid.isChecked():
            self.activeviewer.addNote(self.contextMenuPosition.x(), self.contextMenuPosition.y())

    # call by pressing right button
    def openContextMenu(self, position):

        if len(self.project.fragments) == 0:
            return

        menu = QMenu(self)
        menu.setAutoFillBackground(True)

        str = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            } QMenu::item:disabled { color:rgb(150, 150, 150); }"

        menu.setStyleSheet(str)

        menu.addAction(self.markEmpty)
        menu.addAction(self.markIncomplete)
        menu.addAction(self.markComplete)
        menu.addAction(self.addNote)
        menu.addSeparator()
        menu.addAction(self.groupAction)
        menu.addAction(self.ungroupAction)

        viewer = self.sender()
        self.contextMenuPosition = viewer.mapToGlobal(position)
        action = menu.exec_(self.contextMenuPosition)

    def setProjectTitle(self, project_name):

        title = self.PAPYRLAB_VERSION + " [Project: " + project_name + "]"
        if self.parent() is not None:
            self.parent().setWindowTitle(title)
        else:
            self.setWindowTitle(title)

        if project_name != "NONE":

            settings = QSettings('VCLAB-AIMH', 'PapyrLab')
            files = settings.value('recentFileList')

            if files:

                try:
                    files.remove(project_name)
                except ValueError:
                    pass

                files.insert(0, project_name)
                del files[self.maxRecentFiles:]

                settings.setValue('recentFileList', files)
            else:
                files = []
                files.append(project_name)
                settings.setValue('recentFileList', files)

            self.updateRecentFileActions()

    def createMenuBar(self):

        ##### PROJECTS

        newAct = QAction("New Project", self)
        newAct.setShortcut('Ctrl+N')
        newAct.setStatusTip("Create A New Project")
        newAct.triggered.connect(self.newProject)

        openAct = QAction("Open Project", self)
        openAct.setShortcut('Ctrl+O')
        openAct.setStatusTip("Open An Existing Project")
        openAct.triggered.connect(self.openProject)

        saveAct = QAction("Save Project", self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.setStatusTip("Save Current Project")
        saveAct.triggered.connect(self.saveProject)

        saveAsAct = QAction("Save As", self)
        saveAsAct.setShortcut('Ctrl+Alt+S')
        saveAsAct.setStatusTip("Save Current Project")
        saveAsAct.triggered.connect(self.saveAsProject)

        for i in range(self.maxRecentFiles):
            self.recentFileActs.append(QAction(self, visible=False, triggered=self.openRecentProject))

        ### PROJECT

        setWorkingAreaAct = QAction("Set Working Area", self)
        setWorkingAreaAct.setStatusTip("Define the area where to assemble the fragments")
        setWorkingAreaAct.triggered.connect(self.openWorkingAreaWidget)

        addFolderAct = QAction("Add Image Folder", self)
        addFolderAct.setShortcut('Ctrl+F')
        addFolderAct.setStatusTip("Add the images contained in a given folder to the project")
        addFolderAct.triggered.connect(self.addFolder)

        addImagesAct = QAction("Add Images", self)
        addImagesAct.setShortcut('Ctrl+I')
        addImagesAct.setStatusTip("Add one or more images to the project")
        addImagesAct.triggered.connect(self.addImages)

        ### IMPORT

        appendAct = QAction("Import Fragments from Another Project", self)
        appendAct.setStatusTip("Add to the current project the fragments of another project")
        appendAct.triggered.connect(self.importFragments)


        ### EXPORT

        exportDataTableAct = QAction("Export Fragments As Data Table", self)
        exportDataTableAct.setStatusTip("Export current data as CSV table")
        exportDataTableAct.triggered.connect(self.exportAsDataTable)

        settingsAct = QAction("Settings..", self)
        settingsAct.setStatusTip("")
        settingsAct.triggered.connect(self.settings)

        helpAct = QAction("Help", self)
        helpAct.setShortcut('Ctrl+H')
        helpAct.setStatusTip("Help")
        helpAct.triggered.connect(self.help)

        aboutAct = QAction("About PapyrLab", self)
        aboutAct.triggered.connect(self.about)

        menubar = QMenuBar(self)
        menubar.setAutoFillBackground(True)

        styleMenuBar = "QMenuBar::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            }"

        styleMenu = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            }"

        menubar.setStyleSheet(styleMenuBar)

        self.filemenu = menubar.addMenu("&File")
        self.filemenu.setStyleSheet(styleMenu)
        self.filemenu.addAction(newAct)
        self.filemenu.addAction(openAct)
        self.filemenu.addAction(saveAct)
        self.filemenu.addAction(saveAsAct)
        self.filemenu.addSeparator()

        for i in range(self.maxRecentFiles):
            self.filemenu.addAction(self.recentFileActs[i])
        self.separatorRecentFilesAct = self.filemenu.addSeparator()
        self.updateRecentFileActions()

        self.submenuImport = self.filemenu.addMenu("Import")
        self.submenuImport.addAction(appendAct)
        self.filemenu.addSeparator()
        self.submenuExport = self.filemenu.addMenu("Export")
        self.submenuExport.addAction(exportDataTableAct)
        self.filemenu.addSeparator()
        self.filemenu.addSeparator()
        self.filemenu.addAction(settingsAct)

        #### PROJECT MENU

        self.projectmenu = menubar.addMenu("&Project")
        self.projectmenu.setStyleSheet(styleMenu)
        self.projectmenu.addAction(setWorkingAreaAct)
        self.projectmenu.addAction(addFolderAct)
        self.projectmenu.addAction(addImagesAct)

        splitScreenAction = QAction("Enable Split Screen", self)
        splitScreenAction.setShortcut('Alt+S')
        splitScreenAction.setStatusTip("Split screen")
        splitScreenAction.triggered.connect(self.toggleSplitScreen)


        self.viewmenu = menubar.addMenu("&View")
        self.viewmenu.addAction(self.infodock.toggleViewAction())

        self.helpmenu = menubar.addMenu("&Help")
        self.helpmenu.setStyleSheet(styleMenu)
        self.helpmenu.addAction(helpAct)
        self.helpmenu.addAction(aboutAct)

        return menubar

    @pyqtSlot()
    def settings(self):

        self.settings_widget.setWindowModality(Qt.WindowModal)
        self.settings_widget.show()

    def toggleFrontBack(self, viewerplus):
        pass

    @pyqtSlot()
    def switch(self):
        """
        Switch between the RGB and the DEM channel.
        """

        self.toggleFrontBack(self.viewerplus)
        if self.split_screen_flag:
            self.toggleFrontBack(self.viewerplus2)

    @pyqtSlot()
    def toggleGrid(self):

        if self.btnGrid.isChecked():
            self.activeviewer.showGrid()
            self.checkBoxGrid.setChecked(True)

        self.updateEditActions()

    @pyqtSlot()
    def createGrid(self):
        """
        Create a new grid. This special grid is used to better supervise the annotation work.
        """

        # if len(self.project.images) < 1:
        #     self.btnCreateGrid.setChecked(False)
        #     return

        if self.project.grid is not None:

            reply = QMessageBox.question(self, self.PAPYRLAB_VERSION,
                                         "Would you like to remove the existing <em>grid</em>?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                self.btnCreateGrid.setChecked(True)
                return
            else:
                self.project.grid.undrawGrid()
                self.activeviewer.hideGrid()
                self.btnGrid.setChecked(False)
                self.btnCreateGrid.setChecked(False)
                self.gridWidget = None
                self.project.grid = None
        else:
            self.gridWidget = QtGridWidget(self.activeviewer, self)
            self.gridWidget.show()
            self.gridWidget.accepted.connect(self.assignGrid)
            self.gridWidget.btnCancel.clicked.connect(self.cancelGrid)
            self.project.grid = self.gridWidget.grid


    @pyqtSlot()
    def cancelGrid(self):
        self.project.grid = None
        self.gridWidget.grid.undrawGrid()
        self.gridWidget.close()
        self.gridWidget = None
        self.resetToolbar()


    @pyqtSlot()
    def assignGrid(self):
        """
        Assign the grid created to the corresponding image.
        """
        # self.activeviewer.image.grid = self.gridWidget.grid
        self.resetToolbar()
        self.btnCreateGrid.setChecked(True)
        self.activeviewer.showGrid()
        self.checkBoxGrid.setChecked(True)
        # self.gridWidget = None

    def updateRecentFileActions(self):

        settings = QSettings('VCLAB-AIMH', 'PapyrLab')
        files = settings.value('recentFileList')

        if files:
            numRecentFiles = min(len(files), self.maxRecentFiles)

            for i in range(numRecentFiles):
                text = "&%d. %s" % (i + 1, QFileInfo(files[i]).fileName())
                self.recentFileActs[i].setText(text)
                self.recentFileActs[i].setData(files[i])
                self.recentFileActs[i].setVisible(True)

            for j in range(numRecentFiles, self.maxRecentFiles):
                self.recentFileActs[j].setVisible(False)

            self.separatorRecentFilesAct.setVisible((numRecentFiles > 0))


    def keyPressEvent(self, event):

        modifiers = QApplication.queryKeyboardModifiers()

        if event.key() == Qt.Key_Escape:
            key_pressed = 'ESC'
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            key_pressed = 'ENTER'
        else:
            if event.key() < 0xfffff:
                key_pressed = chr(event.key())
            else:
                key_pressed = event.text()

        if modifiers == Qt.ControlModifier:
            msg = "[KEYPRESS] Key CTRL + '" + key_pressed + "' has been pressed."
        elif modifiers == Qt.ShiftModifier:
            msg = "[KEYPRESS] Key ALT + '" + key_pressed + "' has been pressed."
        elif modifiers == Qt.AltModifier:
            msg = "[KEYPRESS] Key SHIFT + '" + key_pressed + "' has been pressed."
        else:
            msg = "[KEYPRESS] Key '" + key_pressed + "' has been pressed."

        if event.key() == Qt.Key_Escape:
            for viewer in (self.viewerplus, self.viewerplus2):

                # RESET CURRENT OPERATION
                viewer.resetSelection()
                viewer.resetTools()

        elif event.key() == Qt.Key_S and modifiers & Qt.ControlModifier:
            self.save()

        elif event.key() == Qt.Key_S and modifiers & Qt.AltModifier:

            if self.split_screen_flag is True:
                self.disableSplitScreen()
            else:
                self.enableSplitScreen()

        elif event.key() == Qt.Key_Delete:
            self.deleteSelectedFragments()

        elif event.key() == Qt.Key_X:

            print(self.viewerplus.viewport().xL.max() + xR - xR.min() - xL())
            print(self.viewerplus.viewport().height())


            pass

        elif event.key() == Qt.Key_C:
            # TOGGLE RGB/DEPTH CHANNELS
            self.switch()

        elif event.key() == Qt.Key_U:

            # update grid cell state
            if self.btnGrid.isChecked():
                pos = self.cursor().pos()
                self.activeviewer.updateCellState(pos.x(), pos.y(), None)

        elif event.key() == Qt.Key_1:
            # ACTIVATE "PAN/ZOOM" TOOL
            self.pan()

        elif event.key() == Qt.Key_2:
            # ACTIVATE "MOVE" TOOL
            self.move()

        elif event.key() == Qt.Key_3:
            # ACTIVATE "ROTATE" TOOL
            self.rotate()

        elif event.key() == Qt.Key_4:
            # ACTIVATE "FREEHAND" TOOL
            self.freehandSegmentation()

        elif event.key() == Qt.Key_5:
            # ACTIVATE "EDIT BORDER" TOOL
            self.editBorder()

        elif event.key() == Qt.Key_6:
            # ACTIVATE "EVALUATION" TOOL
            self.evaluation()

        elif event.key() == Qt.Key_Q:
            tool = self.viewerplus.tools.tool
            if tool == "MOVE":
                self.viewerplus.tools.tools[tool].rotate(-5)

        elif event.key() == Qt.Key_W:
            tool = self.viewerplus.tools.tool
            if tool == "MOVE":
                self.viewerplus.tools.tools[tool].rotate(5)

        elif event.key() == Qt.Key_A:
            # toggle boundaries
            if self.checkBoxBorders.isChecked():
               self.viewerplus.toggleBorders(1)
               self.viewerplus2.toggleBorders(1)
               self.checkBoxBorders.setChecked(False)
            else:
                self.viewerplus.toggleBorders(0)
                self.viewerplus2.toggleBorders(0)
                self.checkBoxBorders.setChecked(True)

        elif event.key() == Qt.Key_S:
            # toggle regions ids
            if self.checkBoxIds.isChecked():
                self.viewerplus.toggleIds(1)
                self.viewerplus2.toggleIds(1)
                self.checkBoxIds.setChecked(False)
            else:
                self.viewerplus.toggleIds(0)
                self.viewerplus2.toggleIds(0)
                self.checkBoxIds.setChecked(True)

        elif event.key() == Qt.Key_G:

            self.groupOperation()

        elif event.key() == Qt.Key_U:

            self.ungroupOperation()

        elif event.key() == Qt.Key_D:
            # toggle grid
            if self.checkBoxGrid.isChecked():
               self.viewerplus.toggleGrid(1)
               self.viewerplus2.toggleGrid(1)
               self.checkBoxGrid.setChecked(False)
            else:
                self.viewerplus.toggleGrid(0)
                self.viewerplus2.toggleGrid(0)
                self.checkBoxGrid.setChecked(True)

    def setFragmentsVisualization(self):

        if self.checkBoxBorders.isChecked():
            self.viewerplus.enableBorders()
            self.viewerplus2.enableBorders()
        else:
            self.viewerplus.disableBorders()
            self.viewerplus2.disableBorders()

        if self.checkBoxGrid.isChecked():
            self.viewerplus.showGrid()
        else:
            self.viewerplus.hideGrid()

    def disableSplitScreen(self):

        if self.activeviewer is not None:
            if self.activeviewer.tools.tool == "MATCH":
                self.setTool("MOVE")

        self.viewerplus2.hide()

        self.btnSplitScreen.setChecked(False)
        self.split_screen_flag = False

        self.activeviewer = self.viewerplus

    def enableSplitScreen(self):

        if self.working_area_widget is not None:
            self.btnSplitScreen.setChecked(False)
            return

        if len(self.project.fragments) > 0:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.viewerplus.clear()
            self.viewerplus.setProject(self.project)
            self.viewerplus2.clear()
            self.viewerplus2.setProject(self.project)
            self.setFragmentsVisualization()
            self.viewerplus.drawAllFragments()
            self.viewerplus2.drawAllFragments()

            QApplication.restoreOverrideCursor()

            self.viewerplus2.show()
            self.viewerplus.viewChanged()

            self.btnSplitScreen.setChecked(True)
            self.split_screen_flag = True

            self.activeviewer = self.viewerplus


    @pyqtSlot()
    def updateAllViewers(self):
        if self.split_screen_flag is True:
            self.viewerplus.drawAllFragments()
            self.viewerplus2.drawAllFragments()

    @pyqtSlot()
    def setActiveViewer(self):

        viewer = self.sender()

        if self.activeviewer != viewer:

            self.activeviewer = viewer

            if self.activeviewer is not self.viewerplus:
                self.inactiveviewer = self.viewerplus
            else:
                self.inactiveviewer = self.viewerplus2

            self.inactiveviewer.resetTools()


    @pyqtSlot()
    def sliderTransparencyChanged(self):
        #TODO should be (self, value) as the signal is supposed to send a value!
        value = self.sender().value()
        # update transparency value
        str1 = "Transparency {}%".format(value)
        self.lblSlider.setText(str1)
        self.viewerplus.applyTransparency(value)

        if self.viewerplus2.isVisible():
            self.viewerplus2.applyTransparency(value)


    @pyqtSlot()
    def updateViewInfo(self):

        topleft = self.viewerplus.mapToScene(QPoint(0, 0))
        bottomright = self.viewerplus.mapToScene(self.viewerplus.viewport().rect().bottomRight())
        (left, top) = self.viewerplus.clampCoords(topleft.x(), topleft.y())
        (right, bottom) = self.viewerplus.clampCoords(bottomright.x(), bottomright.y())
        zf = self.viewerplus.zoom_factor * 100.0
        zoom = "{:6.0f}%".format(zf)
        self.labelZoomInfo.setText(zoom)

    @pyqtSlot(float, float)
    def updateMousePos(self, x, y):
        zf = self.viewerplus.zoom_factor * 100.0
        zoom = "{:6.0f}%".format(zf)
        left = "{:5d}".format(int(round(x)))
        top = "{:5d}".format(int(round(y)))

        self.labelZoomInfo.setText(zoom)
        self.labelMouseLeftInfo.setText(left)
        self.labelMouseTopInfo.setText(top)


    def resetAll(self):

        if self.gridWidget is not None:
            self.gridWidget.close()
            self.gridWidget = None

        self.viewerplus.clear()
        self.viewerplus2.clear()
        self.viewerplus.resetTools()
        self.viewerplus2.resetTools()
        self.resetToolbar()

        # RE-INITIALIZATION

        self.working_area_widget = None
        self.progress_bar = None

        default_width = self.settings_widget.default_wa_width
        default_height = self.settings_widget.default_wa_height
        self.project = Project(default_width, default_height)

        self.activeviewer = None
        self.contextMenuPosition = None
        self.resetPanelInfo()
        self.disableSplitScreen()

        self.viewerplus.setProject(self.project)
        self.viewerplus2.setProject(self.project)

    def resetToolbar(self):

        self.btnPan.setChecked(False)
        self.btnMove.setChecked(False)
        self.btnEditBorder.setChecked(False)
        self.btnFreehand.setChecked(False)
        self.btnCreateGrid.setChecked(False)
        self.btnGrid.setChecked(False)
        self.btnEvaluation.setChecked(False)

    def setTool(self, tool):
        tools = {
            "PAN"          : ["Pan"          , self.btnPan],
            "MOVE"         : ["Move"       , self.btnMove],
            "EDITBORDER"   : ["Edit Border"  , self.btnEditBorder],
            "FREEHAND"     : ["Freehand"     , self.btnFreehand]
        }
        newtool = tools[tool]
        self.resetToolbar()
        self.viewerplus.setTool(tool)
        self.viewerplus2.setTool(tool)
        newtool[1].setChecked(True)

    @pyqtSlot()
    def pan(self):
        """
        Activate the "pan" tool.
        """
        self.setTool("PAN")

    @pyqtSlot()
    def move(self):
        """
        Activate the "move" tool.
        """
        self.setTool("MOVE")

    @pyqtSlot()
    def rotate(self):
        """
        Activate the "Rotate" tool.
        """
        self.setTool("ROTATE")

    @pyqtSlot()
    def freehand(self):
        """
        Activate the "FREEHAND" tool.
        """
        self.setTool("FREEHAND")

    @pyqtSlot()
    def editBorder(self):
        """
        Activate the "EDITBORDER" tool.
        """
        self.setTool("EDITBORDER")

    @pyqtSlot()
    def evaluation(self):
        """
        Run the evaluation / suggestion
        """
        print('evaluate!')

        if len(self.viewerplus.selected_fragments) != 2:
            print("Must have exactly 2 fragments selected", file=sys.stderr)
            return

        # this goes at top with imports
        from papyrus_matching import FragmentMatcher
        # this goes at init
        matcher = FragmentMatcher(min_availability=0.4)

        # evaluation start
        fragL, fragR = self.viewerplus.selected_fragments

        if fragL.center[0] > fragR.center[0]:
            fragL, fragR = fragR, fragL

        # WARNING: left and right are swapped when working in the back
        backR = fragL.getImageBack().copy()
        backL = fragR.getImageBack().copy()

        # posL and posR are array of (y,x) coordinates of top-left points of the analyzed patches
        posL, posR, scored_displacements, scoresLR = matcher.match(backL, backR)

        """ get the displacement with highest score """
        ranked_displacements = sorted(scored_displacements, key=lambda x: x[1], reverse=True)
        dy, score = ranked_displacements[0]

        """ get displacement with highest smoothed score
        # 3-deg polynomial approx. of matching score vs vertical displacement
        xs, ys = zip(*scored_displacements)
        z = np.polyfit(xs, ys, 3)
        smooth_score = np.poly1d(z)
        crit = smooth_score.deriv().r
        r_crit = crit[crit.imag == 0].real
        test = smooth_score.deriv(2)(r_crit)

        x_max = r_crit[test < 0]
        y_max = smooth_score(x_max)

        dy = x_max
        score = y_max
        """

        numL = len(posL)
        numR = len(posR)

        maxMatches = min(numL, numR, numL+dy, numR-dy)
        xL = posL[min(dy, 0):min(dy, 0) + maxMatches][1]
        xR = posR[max(dy, 0):max(dy, 0) + maxMatches][1]

        widthL = backL.shape[1]
        # dx estimated from patch positions and min_availability
        dx = (xR - xL).min() + xL.max() - xR.min() - 2 * (1 - matcher.min_availability) * matcher.patch_size
        dy *= matcher.stride

        print(f'Best match is dY = {dy}px with score {score}')
        print(f'{dx=}')

        # here we should visualize the output somehow
        # e.g., place the two fragments one next to the other with a vertical displacement of dy.
        top1, left1, width1, right1 = fragL.bbox
        top2, left2, width2, right2 = fragR.bbox

        newX = left1 + width1 + dx
        newY = top1 + dy

        fragR.setPosition(newX, newY)
        self.viewerplus.drawFragment(fragR)
        self.viewerplus2.drawFragment(fragR)


    @pyqtSlot()
    def toggleSplitScreen(self):
        if self.split_screen_flag is True:
            self.disableSplitScreen()
        else:
            self.enableSplitScreen()

    @pyqtSlot()
    def groupOperation(self):
        """
        Creates a group with the selected fragments.
        """

        if len(self.viewerplus.selected_fragments) > 1:

            # separate the fragments of the groups in use
            groups_in_use = set()
            for fragment in self.viewerplus.selected_fragments:
                if fragment.group_id >= 0:
                    groups_in_use.add(fragment.group_id)

            for group_id in groups_in_use:
                self.project.removeGroupById(group_id)

            # create a new group with all the selected fragments
            group = self.project.createGroup()
            group.addFragments(self.viewerplus.selected_fragments)

            self.image_set_widget.updateComboGroups()

    @pyqtSlot()
    def ungroupOperation(self):
        """
        Separate a group of fragments.
        """

        for fragment in self.viewerplus.selected_fragments:
            self.project.removeGroupByFragment(fragment)

        self.viewerplus.resetSelection()

        self.image_set_widget.updateComboGroups()

    @pyqtSlot()
    def noteChanged(self):

        if len(self.activeviewer.selected_blobs) > 0:
            for blob in self.activeviewer.selected_blobs:
                blob.note = self.editNote.toPlainText()
    #
    @pyqtSlot()
    def updatePanelInfoSelected(self):
        selected = self.data_panel.data_table.selectionModel().selectedRows()
        indexes = [self.data_panel.sortfilter.mapToSource(self.data_panel.sortfilter.index(index.row(), 0)) for index in selected]
        if len(indexes) == 0:
            self.resetPanelInfo()
            return
        index = indexes[0]
        row = self.data_panel.data.iloc[index.row()]
        blob_id = row['Id']
        if blob_id < 0:
            print("OOOPS!")
            return

        blob = self.viewerplus.annotations.blobById(blob_id)
        self.updatePanelInfo(blob)

    @pyqtSlot(Fragment)
    def updatePanelInfo(self, fragment):
        self.groupbox_panelinfo.update(fragment)

    @pyqtSlot()
    def resetPanelInfo(self):
        self.groupbox_panelinfo.clear()


    def deleteSelectedFragments(self):

        fragments = self.viewerplus.selected_fragments
        if fragments is not None:
            self.image_set_widget.removeImages(self.viewerplus.selected_fragments)
            for fragment in fragments:
                self.viewerplus.removeFragment(fragment)

    @pyqtSlot()
    def newProject(self):

        self.resetAll()
        self.setTool("PAN")
        self.updateToolStatus()
        self.setProjectTitle("NONE")

    @pyqtSlot()
    def updateToolStatus(self):

        for button in [self.btnPan, self.btnMove, self.btnFreehand,
                       self.btnEditBorder, self.btnCreateGrid, self.btnGrid]:
            button.setEnabled(len(self.project.fragments) > 0)

    @pyqtSlot()
    def openWorkingAreaWidget(self):

        if self.working_area_widget is None:
            self.working_area_widget = QtWorkingAreaWidget()
            self.working_area_widget.setWindowModality(Qt.WindowModal)
            self.working_area_widget.setWorkingArea(self.project.working_area)
            self.working_area_widget.btnApply.clicked.connect(self.setWorkingArea)
            self.working_area_widget.show()
        else:
            self.working_area_widget.show()

    def _setWorkingArea(self):
        self.viewerplus.drawWorkingArea()

        if self.viewerplus2.isVisible():
            self.viewerplus2.drawWorkingArea()

    @pyqtSlot()
    def setWorkingArea(self):

        self.project.setWorkingArea(self.working_area_widget.workingArea())
        self._setWorkingArea()

        self.working_area_widget.close()
        self.working_area_widget = None

    @pyqtSlot()
    def openProject(self):

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open a project", self.papyrlab_dir, filters)

        if filename:
            self.load(filename)

    @pyqtSlot()
    def openRecentProject(self):

        action = self.sender()
        if action:
            self.load(action.data())

    @pyqtSlot()
    def saveProject(self):
        if self.project.filename is None:
            self.saveAsProject()
        else:
            self.save()

    @pyqtSlot()
    def saveAsProject(self):

        filters = "PapyrLab PROJECT (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save project", self.papyrlab_dir, filters)

        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            dir = QDir(self.papyrlab_dir)
            self.project.filename = dir.relativeFilePath(filename)
            self.setProjectTitle(self.project.filename)
            self.save()


    def _addToWorkspace(self, images_names):
        
        QApplication.setOverrideCursor(Qt.WaitCursor)

        fragment_sizes = []
        valid_filenames = []
        for filename in images_names:
            if filename.find("back") < 0 and filename not in [fragment.filename for fragment in self.project.fragments]:
                valid_filenames.append(filename)
                reader = QImageReader(filename)
                width = reader.size().width()
                height = reader.size().height()
                fragment_sizes.append((width, height))

        positions = self.project.fragmentPacking(fragment_sizes)
        assert len(positions) == len(valid_filenames)

        y_offset = max([f.bbox[0] + f.bbox[3] for f in self.project.fragments]) if len(self.project.fragments) > 0 else 0

        for filename, (posx, posy) in zip(valid_filenames, positions):
            id = self.project.getFreeFragmentId()
            # posx, posy = self.project.getFreePosition(filename)
            fragment = Fragment(filename, posx, posy + y_offset, id)
            self.project.addFragment(fragment)
            self.image_set_widget.addImage(fragment)

        self.image_set_widget.updateScrollArea()
        self.image_set_widget.updateComboGroups()
        self.viewerplus.drawAllFragments()
        self.updateToolStatus()

        QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def addImages(self):

        filters = "Images (*.png *.jpg *.jpeg)"
        filenames, _ = QFileDialog.getOpenFileNames(self, "Open one or more images", self.papyrlab_dir, filters)

        if filenames:
            self._addToWorkspace(filenames)

    @pyqtSlot()
    def addFolder(self):

        folder_name = QFileDialog.getExistingDirectory(self, "Select a Folder", "")
        if folder_name:
            images_names = [x for x in glob.glob(os.path.join(folder_name, '*.png'))]
            self._addToWorkspace(images_names)

    @pyqtSlot()
    def importFragments(self):
        pass

    @pyqtSlot()
    def exportAsDataTable(self):
        pass

    @pyqtSlot()
    def help(self):

        help_widget = QtHelpWidget(self)
        help_widget.setWindowOpacity(0.8)
        help_widget.setWindowModality(Qt.WindowModal)
        help_widget.show()

    @pyqtSlot()
    def about(self):

        icon = QLabel()

        # BIG icon
        pxmap = QPixmap(os.path.join("icons", "piui200px.png"))
        pxmap = pxmap.scaledToWidth(160)
        icon.setPixmap(pxmap)
        icon.setStyleSheet("QLabel {padding: 5px; }");

        content = QLabel()
        content.setTextFormat(Qt.RichText)

        txt = "<b>PapyrLab</b> is an AI-empowered interactive fragments re-assembly tool, " \
              "specifically targeted to recompose papyrus' fragments.".format(self.PAPYRLAB_VERSION)

        content.setWordWrap(True)
        content.setMinimumWidth(500)
        content.setText(txt)
        content.setTextInteractionFlags(Qt.TextBrowserInteraction)
        content.setStyleSheet("QLabel {padding: 10px; }");
        content.setOpenExternalLinks(True)

        layout = QHBoxLayout()
        layout.addWidget(icon)
        layout.addWidget(content)

        widget = QWidget(self)
        widget.setAutoFillBackground(True)
        widget.setStyleSheet("background-color: rgba(40,40,40,100); color: white")
        widget.setLayout(layout)
        widget.setWindowTitle("About")
        widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        widget.show()

    def load(self, filename):
        """
        Load a previously saved projects.
        """

        self.resetAll()

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.project.load(self.papyrlab_dir, filename)
        except:
            box = QMessageBox()
            box.setWindowTitle('Failed loading the project')
            box.setText("Could not load the file " + filename)
            box.exec()
            return

        QApplication.restoreOverrideCursor()

        self.setProjectTitle(self.project.filename)
        self.image_set_widget.setProject(self.project)
        self.viewerplus.disableBackVisualization()
        self.viewerplus.setProject(self.project)
        self.viewerplus2.enableBackVisualization()
        self.viewerplus2.setProject(self.project)

        self.updateToolStatus()

    def appendProject(self, filename):
        """
        Append the annotated images of a previously saved project to the current one.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            project_to_append = loadProject(self.papyrlab_dir, filename, self.project.labels)

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
            msgBox.exec()
            return

        # append the annotated images to the current ones
        for annotated_image in project_to_append.images:
            self.project.addNewImage(annotated_image)

        QApplication.restoreOverrideCursor()

        msgBox = QMessageBox()
        msgBox.setWindowTitle(self.PAPYRLAB_VERSION)
        msgBox.setText("The fragments of the given project has been successfully added to this one.")
        msgBox.exec()

    def save(self):
        """
        Save the current project.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.project.save()
        QApplication.restoreOverrideCursor()

        msgBox = QMessageBox()
        msgBox.setWindowTitle(self.PAPYRLAB_VERSION)
        msgBox.setText("Current project has been successfully saved.")
        msgBox.exec()


if __name__ == '__main__':

    # Create the QApplication.
    app = QApplication(sys.argv)

    # set application icon
    app.setWindowIcon(QIcon(os.path.join("icons", "piui50px.png")))

    slider_style1 = "\
    QSlider::groove::horizontal\
    {\
        border: 1px solid;\
        height: 8px;\
        color: rgb(100,100,100);\
    }"

    slider_style2 = "QSlider::handle::horizontal\
    {\
        background: white;\
        border: 1;\
        xL.max() + xR - xR.min() - xL: 18px;\
    }"

    app.setStyleSheet("QLabel {color: white}")
    app.setStyleSheet("QPushButton {background-color: rgb(49,51,53); color: white}")
    app.setStyleSheet(slider_style1)
    app.setStyleSheet(slider_style2)

    app.setStyleSheet("QToolTip {color: white; background-color: rgb(49,51,53); border: none; }")

    app.setStyleSheet("QMainWindow::separator { xL.max() + xR - xR.min() - xL:5px; height:5px; color: red; }" + 
        "QMainWindow::separator:hover { background: #888; }" + 
        "QDockWidget::close-button, QDockWidget::float-button { background:#fff; }")

    # set the application font
    if platform.system() != "Darwin":
        QFD = QFontDatabase()
        font_id1 = QFD.addApplicationFont("fonts/opensans/OpenSans-Regular.ttf")
        if font_id1 == -1:
            print("Failed to load application font..")
            sys.exit(-2)

        font_id2 = QFD.addApplicationFont("fonts/roboto/Roboto-Light.ttf")
        if font_id2 == -1:
            print("Failed to load application font..")
            sys.exit(-2)

        font_id3 = QFD.addApplicationFont("fonts/roboto/Roboto-Regular.ttf")
        if font_id3 == -1:
            print("Failed to load application font..")
            sys.exit(-2)

        font = QFont('Roboto')
        app.setFont(font)

    # Create the main user interface
    tool = PapyrLab()

    # create the main window - PapyrLab is the central widget
    mw = MainWindow()
    title = tool.PAPYRLAB_VERSION
    mw.setWindowTitle(title)
    mw.setCentralWidget(tool)
    mw.setStyleSheet("background-color: rgb(55,55,55); color: white")
    mw.showMaximized()

    # Show the viewer and run the application.
    mw.show()

    # update the size of all widgets
    tool.adjustSize()

    tool.viewerplus.fitContentInViewport()
    tool.viewerplus2.fitContentInViewport()

    #tool.viewerplus.fitContentInViewport()
    #tool.viewerplus2.fitContentInViewport()

    sys.exit(app.exec_())
