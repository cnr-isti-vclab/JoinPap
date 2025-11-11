#
# PIUI
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

""" PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.
    The viewer has also drawing capabilities (differently from QTimage viewer).
"""

from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QPlainTextEdit,QSizePolicy

from source.Fragment import Fragment
from source.Project import Project
from source.Tools import Tools


#circular dependency. create a viewer and a derived class which also deals with the rest.
class QtImageViewerPlus(QGraphicsView):
    """
    PyQt image viewer widget with annotation capabilities.
    QGraphicsView handles a scene composed by an image plus shapes (rectangles, polygons, blobs).
    The input image (it must be a QImage) is internally converted into a QPixmap.
    """

    # Mouse button signals emit image scene (x, y) coordinates.
    leftMouseButtonPressed = pyqtSignal(float, float)
    rightMouseButtonPressed = pyqtSignal(float, float)
    leftMouseButtonReleased = pyqtSignal(float, float)
    rightMouseButtonReleased = pyqtSignal(float, float)
    #leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)
    mouseMoveLeftPressed = pyqtSignal(float, float)
    mouseMoved = pyqtSignal(float, float)
    selectionChanged = pyqtSignal()
    selectionReset = pyqtSignal()
    viewUpdated = pyqtSignal(QRectF)                    # region visible in percentage
    viewHasChanged = pyqtSignal(float, float, float)    # posx, posy, posz

    # custom signal
    updateInfoPanel = pyqtSignal(Fragment)

    activated = pyqtSignal()
    newSelection = pyqtSignal()

    updateAllViewers = pyqtSignal()

    def __init__(self, piui_dir, parent=None):
        QGraphicsView.__init__(self)

        self.project = None
        self.selected_fragments = []

        self.piui_dir = piui_dir

        # MAIN SCENE
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.dragSelectionStart = None
        self.dragSelectionRect = None
        self.dragSelectionStyle = QPen(Qt.white, 1, Qt.DashLine)
        self.dragSelectionStyle.setCosmetic(True)

        # Set scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # DRAWING SETTINGS
        self.border_enabled = True
        self.ids_enabled = True
        self.back_vis = False

        self.show_grid = False

        self.border_pen = QPen(Qt.black, 3)
        self.border_pen.setCosmetic(True)
        self.border_selected_pen = QPen(Qt.white, 3)
        self.border_selected_pen.setCosmetic(True)

        self.sampling_pen = QPen(Qt.yellow, 3)
        self.sampling_pen.setCosmetic(True)
        self.sampling_brush = QBrush(Qt.yellow)
        self.sampling_brush.setStyle(Qt.CrossPattern)

        self.markers_pen = QPen(Qt.cyan, 3)
        self.markers_pen.setCosmetic(True)
        self.markers_brush = QBrush(Qt.cyan)
        self.markers_brush.setStyle(Qt.SolidPattern)

        self.working_area_pen = QPen(Qt.lightGray, 3, Qt.SolidLine)
        self.working_area_brush = QBrush(Qt.SolidPattern)
        self.working_area_brush.setColor(Qt.darkGray)
        self.working_area_pen.setCosmetic(True)

        self.mouseCoords = QPointF(0, 0)
        self.crackWidget = None
        self.bricksWidget = None

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.transparency_value = 0.5

        # Z values (for drawing the scene correctly)
        self.Z_VALUE_WORKING_AREA = -1
        self.Z_VALUE_FRAGMENTS = 2
        self.Z_VALUE_BORDERS = 3
        self.Z_VALUE_IDS = 4
        self.Z_VALUE_TEXT = 5
        self.Z_VALUE_NOTE = 6
        self.Z_VALUE_SELECTION_RECT = 10

        # working area
        self.working_area_rect = None

        self.verticalScrollBar().valueChanged.connect(self.viewChanged)
        self.horizontalScrollBar().valueChanged.connect(self.viewChanged)

        # Panning is enabled if and only if the image is greater than the viewport.
        self.panEnabled = True
        self.zoomEnabled = True

        # zoom is always active
        self.zoom_factor = 1.0
        self.ZOOM_FACTOR_MIN = 0.05
        self.ZOOM_FACTOR_MAX = 8.0

        MIN_SIZE = 250
        self.viewport().setMinimumWidth(MIN_SIZE)
        self.viewport().setMinimumHeight(MIN_SIZE)

        self.resetTransform()
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.tools = Tools(self)
        self.tools.createTools()

        self.parent = parent
        self.rotated = False

    def setProject(self, project):

        self.project = project

        self.drawWorkingArea()
        self.drawAllFragments()
        self.showGrid()

        self.scene.invalidate()

    def fitContentInViewport(self):

        w = self.scene.width()
        h = self.scene.height()

        # calculate zoom factor
        pixels_of_border = 1
        zf1 = (self.viewport().width() - pixels_of_border) / w
        zf2 = (self.viewport().height() - pixels_of_border) / h

        zf = min(zf1, zf2)
        self.zoom_factor = zf

        self.scene.invalidate()

    def clear(self):

        # clear selection
        self.selected_fragments = []
        self.selectionChanged.emit()

        # undraw all fragments
        if self.project is not None:
            for fragment in self.project.fragments:
                self.undrawFragment(fragment)
                del fragment

        # clear working area
        if self.working_area_rect is not None:
            self.scene.removeItem(self.working_area_rect)
            self.working_area_rect = None

        self.hideGrid()

        # no project is set
        self.project = None

    @pyqtSlot()
    def viewChanged(self):

        if self.scene is None:
            return

        rect = self.viewportToScenePercent()
        self.viewUpdated.emit(rect)
        posx = self.horizontalScrollBar().value()
        posy = self.verticalScrollBar().value()
        zoom = self.zoom_factor
        self.viewHasChanged.emit(posx, posy, zoom)

    def setZoomFactor(self, zoomfactor):

        if zoomfactor < self.ZOOM_FACTOR_MIN:
            zoomfactor = self.ZOOM_FACTOR_MIN

        if zoomfactor > self.ZOOM_FACTOR_MAX:
            zoomfactor = self.ZOOM_FACTOR_MAX

            # immagino che questo sia necessario nel caso ci sia il mirroring sull'altra vista
            #self.reapplyTransforms()

            # credo che questo sia necessario per zoomare la scena in modo centrato
            #delta = self.mapToScene(view_pos) - self.mapToScene(self.viewport().rect().center())
            #self.centerOn(scene_pos - delta)

        self.blockSignals(True)
        self.zoom_factor = zoomfactor
        self.updateViewer()
        self.blockSignals(False)

    def setViewParameters(self, posx, posy, zoomfactor):

        self.blockSignals(True)
        self.horizontalScrollBar().setValue(int(posx))
        self.verticalScrollBar().setValue(int(posy))
        self.zoom_factor = zoomfactor
        self.updateViewer()
        self.blockSignals(False)

    def reapplyTransforms(self):
        self.resetTransform()
        scale_x_mul = -1 if self.back_vis else 1
        self.scale(scale_x_mul * self.zoom_factor, self.zoom_factor)
        if self.rotated:
            self.rotate(180)

        if self.project is not None and self.project.fragments is not None and self.back_vis:
            for fragment in self.project.fragments:
                fragment.reapplyTransformsOnVerso(rotated=self.rotated)

        for tool in self.tools.tools.values():
            tool.handleTransform()

    def updateViewer(self):
        """
        Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        self.reapplyTransforms()
        self.invalidateScene()

    def drawWorkingArea(self):

        if self.project is not None:

            wa = self.project.working_area  # width, height

            if wa is not None:
              if len(wa) == 2 and wa[0] > 0 and wa[1] > 0:
                    if self.working_area_rect is None:
                        self.working_area_rect = self.scene.addRect(0, 0, wa[0], wa[1], pen=self.working_area_pen,
                                                                    brush=self.working_area_brush)
                        self.working_area_rect.setZValue(self.Z_VALUE_WORKING_AREA)
                    else:
                        self.working_area_rect.setRect(0, 0, wa[0], wa[1])

    def undrawWorkingArea(self):

        if self.working_area_rect is not None:
            self.scene.removeItem(self.working_area_rect)
            self.working_area_rect = None

    def disableScrollBars(self):

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def enablePan(self):
        self.panEnabled = True

    def disablePan(self):
        self.panEnabled = False

    def enableZoom(self):
        self.zoomEnabled = True

    def disableZoom(self):
        self.zoomEnabled = False

    def enableBorders(self):
        if self.project is not None:
            for fragment in self.project.fragments:
                if isinstance(fragment, Fragment):
                    fragment.drawBorders(self.scene, back=self.back_vis, enabled=self.border_enabled, zvalue_borders=self.Z_VALUE_BORDERS)

        self.border_enabled = True

    def disableBorders(self):
        if self.project is not None:
            for fragment in self.project.fragments:
                if isinstance(fragment, Fragment):
                    fragment.undrawBorders(self.scene, back=self.back_vis)

        self.border_enabled = False

    def enableBackVisualization(self):

        self.back_vis = True

    def disableBackVisualization(self):

        self.back_vis = False

    @pyqtSlot(int)
    def toggleBorders(self, checked):

        if checked == 0:
            self.disableBorders()
        else:
            self.enableBorders()

    def showGrid(self):

        if self.project is not None:
            if self.project.grid is not None:
                self.parent.btnCreateGrid.setChecked(True)
                self.project.grid.setScene(self.scene)
                if self.back_vis:
                    pass    # TODO: work on this if we want grid to be drawn on the back
                    # self.project.grid.drawGrid(reverse=False)
                else:
                    self.project.grid.drawGrid(reverse=False)
                self.project.grid.setVisible(True)
                self.show_grid = True
            else:
                self.show_grid = False

    def hideGrid(self):

        if self.project.grid is not None:
            self.project.grid.setVisible(False)

        self.show_grid = False

    @pyqtSlot(int)
    def toggleGrid(self, check):

        if check == 0:
            self.hideGrid()
        else:
            self.showGrid()

    @pyqtSlot(int)
    def toggleRotate(self, check):
        self.rotated = check
        # super trick: if the whole scene is rotated 180 degrees, the text should be rotated as well so it always looks upright
        self.reapplyTransforms()

    def enableIds(self):
        if self.project is not None:
            for fragment in self.project.fragments:
                fragment.enableIds(True)
        self.ids_enabled = True

    def disableIds(self):
        if self.project is not None:
            for fragment in self.project.fragments:
                fragment.enableIds(False)
        self.ids_enabled = False

    @pyqtSlot(int)
    def toggleIds(self, checked):

        if checked == 0:
            self.disableIds()
        else:
            self.enableIds()

    def drawFragment(self, fragment):
        fragment.draw(
            self.scene, 
            back=self.back_vis, 
            selected=fragment in self.selected_fragments, 
            border_enabled=self.border_enabled)
        fragment.enableIds(self.ids_enabled)
        fragment.reapplyTransformsOnVerso(rotated=self.rotated)

    def undrawFragment(self, fragment):
        fragment.undraw(self.scene)

    def fragmentPositionChanged(self):

        self.updateAllViewers.emit()

    def applyTransparency(self, value):

        self.transparency_value = 1.0 - (value / 100.0)

        if self.project is not None:
            for fragment in self.project.fragments:
                fragment.qpixmap_item.setOpacity(self.transparency_value)

    def drawAllFragments(self):

        for fragment in self.project.fragments:
            self.drawFragment(fragment)

    def setTool(self, tool):

        # if not self.isVisible():
        #     return

        QApplication.setOverrideCursor(Qt.ArrowCursor)

        self.tools.setTool(tool)

        if tool in ["FREEHAND", "RULER"] or (tool in ["CUT", "EDITBORDER"] and len(self.selected_fragments) > 1):
            self.resetSelection()

        if tool == "SELECTAREA" or tool == "RITM":
            QApplication.setOverrideCursor(Qt.CrossCursor)

        # define when panning is active or not
        if tool == "PAN":
            self.enablePan()
        else:
            self.disablePan()  # in this case, it is possible to PAN only moving the mouse and pressing the CTRL key

    def resetTools(self):

        self.tools.resetTools()
        self.scene.invalidate(self.scene.sceneRect())
        self.setDragMode(QGraphicsView.NoDrag)

    @pyqtSlot(float, float)
    def selectOp(self, x, y):
        """
        Selection operation.
        """

        selected_fragment = self.project.fragmentClicked(x, y)

        if selected_fragment is not None:
            if selected_fragment.group_id >= 0:
                fragments = self.project.getFragmentsOfAGroup(selected_fragment)
                for fragment in fragments:
                    if fragment in self.selected_fragments:
                        self.removeFromSelectedList(fragment)
                    else:
                        self.addToSelectedList(fragment)
                        if isinstance(fragment, Fragment):
                            self.updateInfoPanel.emit(fragment)
            else:
                if selected_fragment:
                    if selected_fragment in self.selected_fragments:
                        self.removeFromSelectedList(selected_fragment)
                    else:
                        self.addToSelectedList(selected_fragment)
                        if isinstance(selected_fragment, Fragment):
                            self.updateInfoPanel.emit(selected_fragment)

            self.parent.image_set_widget.scrollToFragment(selected_fragment,verso=self.back_vis)
            self.newSelection.emit()
        else:
            self.resetSelection()

    def updateCellState(self, x, y, state):

        if self.project.grid is not None and self.show_grid is True:
            pos = self.mapFromGlobal(QPoint(x, y))
            scenePos = self.mapToScene(pos)
            self.project.grid.changeCellState(scenePos.x(), scenePos.y(), state)

    def paintEvent(self, event):

        # render the main scene (self.scene)
        super(QtImageViewerPlus, self).paintEvent(event)

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        self.activated.emit()

        scenePos = self.mapToScene(event.pos())

        mods = event.modifiers()

        if event.button() == Qt.LeftButton:
            self.hasBeenDragged = False
            (x, y) = [round(scenePos.x()), round(scenePos.y())] #self.clipScenePos(scenePos)
            selected_fragment = self.project.fragmentClicked(x, y)
            self.leftMouseButtonPressed.emit(x, y)

            multiple_selection_and_not_shift = not (mods & Qt.ShiftModifier) and selected_fragment is not None and len(self.selected_fragments) >= 2

            if not multiple_selection_and_not_shift and (self.tools.tool == "PAN" or self.tools.tool == "MOVE"):
                # used from area selection and pen drawing
                if not (mods & Qt.ShiftModifier):
                    if self.panEnabled:
                        self.setDragMode(QGraphicsView.ScrollHandDrag)
                    self.resetSelection()
                    self.selectOp(x, y)
                else:
                    self.dragSelectionStart = [x, y]

                    if mods & Qt.ShiftModifier:
                        self.selectOp(x, y)
                    else:
                        self.resetSelection()
                        self.selectOp(x, y)

            if self.tools.tool != "PAN":
                self.tools.leftPressed(x, y)

        if event.button() == Qt.RightButton:
            (x, y) = [round(scenePos.x()), round(scenePos.y())] # self.clipScenePos(scenePos)
            self.rightMouseButtonPressed.emit(x, y)

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        QGraphicsView.mouseReleaseEvent(self, event)
        mods = event.modifiers()

        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
            (x, y) = [round(scenePos.x()), round(scenePos.y())] # self.clipScenePos(scenePos)

            if self.hasBeenDragged and (mods & Qt.ShiftModifier) and self.dragSelectionStart:
                if abs(x - self.dragSelectionStart[0]) > 5 and abs(y - self.dragSelectionStart[1]) > 5:
                    self.dragSelection(x, y)
                    self.dragSelectionStart = None
                    if self.dragSelectionRect:
                        self.scene.removeItem(self.dragSelectionRect)
                        del self.dragSelectionRect
                        self.dragSelectionRect = None

            else:
                self.tools.leftReleased(x, y)

            self.hasBeenDragged = False

    def mouseMoveEvent(self, event):

        QGraphicsView.mouseMoveEvent(self, event)
        mods = event.modifiers()

        scenePos = self.mapToScene(event.pos())
        self.mouseMoved.emit(scenePos.x(), scenePos.y())

        if event.buttons() == Qt.LeftButton:
            self.hasBeenDragged = True
            (x, y) = [round(scenePos.x()), round(scenePos.y())] # self.clipScenePos(scenePos)

            if (mods & Qt.ShiftModifier) and self.dragSelectionStart:
                start = self.dragSelectionStart
                if not self.dragSelectionRect:
                    self.dragSelectionRect = self.scene.addRect(start[0], start[1], x - start[0],
                                                                           y - start[1], self.dragSelectionStyle)
                    self.dragSelectionRect.setZValue(self.Z_VALUE_SELECTION_RECT)

                xp = min(x, start[0])
                yp = min(y, start[1])

                self.dragSelectionRect.setRect(xp, yp, abs(x - start[0]), abs(y - start[1]))
                return

            if Qt.ControlModifier & QApplication.queryKeyboardModifiers():
                return

            self.tools.mouseMove(x, y)


    def keyPressEvent(self, event):

        # keys handling goes here..

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift and self.tools.tool == "RITM":
            QApplication.setOverrideCursor(Qt.ArrowCursor)
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """ Zoom in/zoom out.
        """

        mods = event.modifiers()

        if self.tools.tool == "WATERSHED" and mods & Qt.ShiftModifier:
            self.tools.tools["WATERSHED"].scribbles.setScaleFactor(self.zoom_factor)
            self.tools.wheel(event.angleDelta())
            return

        if self.zoomEnabled:

            view_pos = event.pos()
            scene_pos = self.mapToScene(view_pos)

            pt = event.angleDelta()

            # uniform zoom.
            self.zoom_factor = self.zoom_factor*pow(pow(2, 1/2), pt.y()/100);
            if self.zoom_factor < self.ZOOM_FACTOR_MIN:
                self.zoom_factor = self.ZOOM_FACTOR_MIN
            if self.zoom_factor > self.ZOOM_FACTOR_MAX:
                self.zoom_factor = self.ZOOM_FACTOR_MAX

            self.reapplyTransforms()

            delta = self.mapToScene(view_pos) - self.mapToScene(self.viewport().rect().center())
            self.centerOn(scene_pos - delta)

            self.invalidateScene()

    def dragSelection(self, x, y):
        left = min(x, self.dragSelectionStart[0])
        top = min(y, self.dragSelectionStart[1])
        right = left + abs(x - self.dragSelectionStart[0])
        bottom = top + abs(y - self.dragSelectionStart[1])
        self.resetSelection()
        for fragment in self.project.fragments:

            box = fragment.bbox

            if top > box[0] or left > box[1] or right < box[1] + box[2] or bottom < box[0] + box[3]:
                continue
            self.addToSelectedList(fragment)

    @pyqtSlot(str, int)
    def setBorderPen(self, color, thickness):

        self.border_pen = QPen(Qt.black, thickness)
        self.border_pen.setCosmetic(True)
        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.border_pen.setColor(QColor(r, g, b))

    @pyqtSlot(str, int)
    def setSelectionPen(self, color, thickness):

        self.border_selected_pen = QPen(Qt.white, thickness)
        self.border_selected_pen.setCosmetic(True)
        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.border_selected_pen.setColor(QColor(r, g, b))

    @pyqtSlot(str)
    def setWorkingAreaBackgroundColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.working_area_brush.setColor(QColor(r, g, b))

            if self.working_area_rect is not None:
                self.working_area_rect.setBrush(self.working_area_brush)

    @pyqtSlot(str, int)
    def setWorkingAreaPen(self, color, thickness):

        self.working_area_pen = QPen(Qt.white, thickness)
        self.working_area_pen.setCosmetic(True)
        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.working_area_pen.setColor(QColor(r, g, b))

            if self.working_area_rect is not None:
                self.working_area_rect.setPen(self.working_area_pen)

#SELECTED BLOBS MANAGEMENT

    def addToSelectedList(self, fragment):
        """
        Add the given fragment to the list of selected fragment.
        """

        if fragment in self.selected_fragments:
            pass
        else:
            self.selected_fragments.append(fragment)

        fragment.select(
            self.scene, 
            back=self.back_vis, 
            border_enabled=self.border_enabled, 
            zvalue_borders=self.Z_VALUE_BORDERS, 
            zvalue_ids=self.Z_VALUE_IDS
        )

        self.scene.invalidate()
        self.selectionChanged.emit()

    def removeFromSelectedList(self, fragment):
        try:
            # safer if iterating over selected_fragments and calling this function.
            self.selected_fragments = [x for x in self.selected_fragments if not x == fragment]

            fragment.deselect(self.scene, back=self.back_vis, zvalue_ids=self.Z_VALUE_IDS)

            self.scene.invalidate()

        except Exception as e:
            print("Exception: e", e)
            pass

        self.selectionChanged.emit()

    def resizeEvent(self, event):
        """
        Maintain current zoom on resize.
        """

        width = self.scene.width()
        height = self.scene.height()
        if width > 0 and height > 0:
            zoom_required = 0.25 * min(1.0 * self.width() / width, 1.0 * self.height() / height)
#            if zoom_required < self.ZOOM_FACTOR_MIN:
#                self.ZOOM_FACTOR_MIN = zoom_required

        self.updateViewer()

        event.accept()

    def resetSelection(self):

        for fragment in self.selected_fragments:
            fragment.deselect(self.scene, back=self.back_vis, zvalue_ids=self.Z_VALUE_IDS)

        self.selected_fragments.clear()
        self.scene.invalidate(self.scene.sceneRect())
        self.selectionChanged.emit()
        self.selectionReset.emit()

    def addFragment(self, fragment, selected = False):
        """
        The only function to add annotations. will take care of undo and QGraphicItems.
        """

        self.project.addFragment(fragment)
        self.drawFragment(fragment)

        if selected:
            self.addToSelectedList(fragment)

    def removeFragment(self, fragment):

        self.removeFromSelectedList(fragment)
        self.undrawFragment(fragment)
        self.project.removeFragment(fragment)

    def deleteSelectedFragments(self):

        for fragment in self.selected_fragments:
            self.removeFragment(fragment)

    def viewportToScene(self):

        topleft = self.mapToScene(self.viewport().rect().topLeft())
        bottomright = self.mapToScene(self.viewport().rect().bottomRight())
        return QRectF(topleft, bottomright)

    def viewportToScenePercent(self):

        view = self.viewportToScene()

        if self.scene is not None:
            width = self.scene.width()
            height = self.scene.height()
        else:
            width = view.width()
            height = view.height()

        view.setCoords(view.left() / width, view.top() / height, view.right() / width, view.bottom() / height)
        return view

    def clampCoords(self, x, y):

        if self.scene is not None:

            xc = max(0, min(int(x), self.scene.width()))
            yc = max(0, min(int(y), self.scene.height()))
        else:
            xc = 0
            yc = 0

        return (xc, yc)

    def clipScenePos(self, scenePosition):

        posx = scenePosition.x()
        posy = scenePosition.y()
        if posx < 0:
            posx = 0
        if posy < 0:
            posy = 0
        if posx > self.scene.width():
            posx = self.scene.width()
        if posy > self.scene.height():
            posy = self.scene.height()

        return [round(posx), round(posy)]

    @pyqtSlot(float, float)
    def center(self, x, y):

        zf = self.zoom_factor

        xmap = float(self.img_map.width()) * x
        ymap = float(self.img_map.height()) * y

        view = self.viewportToScene()
        (w, h) = (view.width(), view.height())

        posx = max(0, xmap - w / 2)
        posy = max(0, ymap - h / 2)

        posx = min(posx, self.img_map.width() - w / 2)
        posy = min(posy, self.img_map.height() - h / 2)

        self.horizontalScrollBar().setValue(posx * zf)
        self.verticalScrollBar().setValue(posy * zf)

