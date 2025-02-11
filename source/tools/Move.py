from source.tools.Tool import Tool
from PyQt5.QtCore import QPoint, QPointF
import numpy as np

class Move(Tool):

    def __init__(self, viewerplus):
        super(Move, self).__init__(viewerplus)

        self.initial_point_clicked = []
        self.last_point_clicked = []

    def leftPressed(self, x, y, mods):
        self.initial_point_clicked = [x, y]
        self.last_point_clicked = [x, y]

    def mouseMove(self, x, y):

        if len(self.last_point_clicked) == 2:

            deltax = x - self.last_point_clicked[0]
            deltay = y - self.last_point_clicked[1]

            self.moveFragment(deltax, deltay)

            self.last_point_clicked[0] = x
            self.last_point_clicked[1] = y

    def moveFragment(self, dx, dy):

        for fragment in self.viewerplus.selected_fragments:

            if self.viewerplus.back_vis is not True:
                pt = fragment.qpixmap_item.pos()
                fragment.qpixmap_item.setPos(pt + QPoint(dx, dy))
                pt = fragment.id_item.pos()
                fragment.id_item.setPos(pt + QPoint(dx, dy))

                if fragment.qpixmap_contour_item is not None:
                    pt = fragment.qpixmap_contour_item.pos()
                    fragment.qpixmap_contour_item.setPos(pt + QPoint(dx, dy))
            else:
                pt = fragment.qpixmap_back_item.pos()
                fragment.qpixmap_back_item.setPos(pt + QPoint(dx,dy))
                pt = fragment.id_back_item.pos()
                fragment.id_back_item.setPos(pt + QPoint(dx,dy))

                if fragment.qpixmap_contour_back_item is not None:
                    pt = fragment.qpixmap_contour_back_item.pos()
                    fragment.qpixmap_contour_back_item.setPos(pt + QPoint(dx,dy))

    def rotate(self, angle):

        bboxes = []
        for fragment in self.viewerplus.selected_fragments:
            bboxes.append(fragment.bbox)

        bbox = jointBox(bboxes)

        for fragment in self.viewerplus.selected_fragments:
            cy = bbox[0] + (bbox[3] / 2.0)
            cx = bbox[1] + (bbox[2] / 2.0)
            fragment.qpath_item.setTransformOriginPoint(QPointF(cx, cy))
            angle0 = fragment.qpath_item.rotation()
            fragment.qpath_item.setRotation(angle0 + angle)
            cx = bbox[2] / 2.0
            cy = bbox[3] / 2.0
            fragment.qpixmap_item.setTransformOriginPoint(QPointF(cx, cy))
            angle0 = fragment.qpixmap_item.rotation()
            fragment.qpixmap_item.setRotation(angle0 + angle)

    def updateFragment(self):

        if len(self.initial_point_clicked) == 2 and len(self.last_point_clicked) == 2:
            for fragment in self.viewerplus.selected_fragments:
                deltax = self.last_point_clicked[0] - self.initial_point_clicked[0]
                deltay = self.last_point_clicked[1] - self.initial_point_clicked[1]
                fragment.updatePosition(deltax, deltay)
                self.viewerplus.drawFragment(fragment) 
                self.viewerplus.fragmentPositionChanged()         


    def leftReleased(self, x, y):

        self.updateFragment()

        self.initial_point_clicked = []
        self.last_point_clicked = []
