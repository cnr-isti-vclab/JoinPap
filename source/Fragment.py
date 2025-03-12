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
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import numpy as np
import os
import skimage.morphology

from skimage import measure
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QImage, QPixmap, QTransform, QFont, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsSimpleTextItem

from source.utils import qimageToNumpyArray, maskToQImage, maskToQImageWTrasparency

class TextItem(QGraphicsSimpleTextItem):
    def __init__(self, text, font, background_color=QColor(80, 80, 80)):
        QGraphicsSimpleTextItem.__init__(self)
        self.setText(text)
        self.setFont(font)
        self.background_color = background_color
        # self.setTransformOriginPoint(self.boundingRect().center())

    def paint(self, painter, option, widget):
        painter.save()
        painter.translate(self.boundingRect().topLeft())
        
        # Draw the background rectangle
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(super().boundingRect())
        
        super().paint(painter, option, widget)
        painter.restore()

    def boundingRect(self):
        b = super().boundingRect()
        return QRectF(b.x()-b.width()/2.0, b.y()-b.height()/2.0, b.width(), b.height())

"""
compute the bounding box of a set of points in format [[x0, y0], [x1, y1]... ]
padding is used, since when painting we draw a 'fat' line
"""
def pointsBox(points, pad = 0):
    box = [points[:, 1].min()-pad,
           points[:, 0].min()-pad,
           points[:, 0].max() + pad,
           points[:, 1].max() + pad]
    box[2] -= box[1]
    box[3] -= box[0]
    return np.array(box).astype(int)

class Fragment(object):
    """
    Fragment represents a fragment belonging to the papyrus.
    It can be tagged such that it belongs to a specific group and annotated.
    It is stored as an RGB image (typically of small size).
    The BACK of the fragment is also stored, if available.
    """

    def __init__(self, filename, offset_x, offset_y, id):

        self.id = int(id)
        self.filename = filename
        self.name, _ = os.path.splitext(os.path.basename(filename))
        self.bbox = [offset_y, offset_x, 0, 0]
        self.group_id = -1
        self.note = ""
        self.center = np.array((offset_x, offset_y))

        # custom user data - not used for now
        self.data = {}

        self.contour = None
        self.inner_contours = []

        self.qimage = None
        self.qimage_back = None
        self.qpixmap = None
        self.qpixmap_back = None
        self.qpixmap_contour = None
        self.qpixmap_contour_back = None
        self.qpixmap_item = None
        self.qpixmap_back_item = None
        self.qpixmap_contour_item = None
        self.qpixmap_contour_back_item = None
        self.id_item = None
        self.id_back_item = None

        # load image
        if filename != "":

            self.qimage = QImage(filename)
            self.qimage = self.qimage.convertToFormat(QImage.Format_ARGB32)

            if "verso" in filename:
                raise Exception("You are trying to load a verso fragment as a recto fragment: " + filename)

            filename_back = Fragment.searchBackFile(filename)
            self.qimage_back = QImage(filename_back)
            self.qimage_back = self.qimage_back.mirrored(True, False)
            self.qimage_back = self.qimage_back.convertToFormat(QImage.Format_ARGB32)

            # BBOX FORMAT: top, left, width, height
            self.bbox = [offset_y, offset_x, self.qimage.width(), self.qimage.height()]

            # center is (x, y)
            self.center = np.array((offset_x + self.qimage.width()/2, offset_y + self.qimage.height()/2))

            self.prepareForDrawing()

    @staticmethod
    def searchBackFile(filename):
        """
        Search for the back image of the fragment.
        """

        filename_back = filename[:-4] + "_back" + filename[-4:]
        if not os.path.isfile(filename_back) and 'recto' in filename:
            filename_back = filename.replace("recto", "verso")
        if not os.path.isfile(filename_back) and 'front' in filename:
            filename_back = filename.replace("front", "back")
        if not os.path.isfile(filename_back):
            return None
        
        return filename_back

    def setId(self, id):

        self.id = id

    def createMask(self, qimage):

        mask = np.zeros((qimage.height(), qimage.width()), dtype=np.uint8)
        img = qimageToNumpyArray(qimage)

        # turn on opaque pixels
        mask[img[:, :, 3] < 150] = 1

        return mask

    def getImage(self):

        if self.qimage is not None:
            nparray = qimageToNumpyArray(self.qimage)
        else:
            nparray = None
        return nparray

    def getImageBack(self):

        if self.qimage_back is not None:
            mirrored_back = self.qimage_back.mirrored(True, False)
            nparray = qimageToNumpyArray(mirrored_back)
        else:
            nparray = None
        return nparray

    def updatePosition(self, dx, dy):

        self.center[0] += dx
        self.center[1] += dy

        self.bbox[0] += dy
        self.bbox[1] += dx

    def setPosition(self, newX, newY):

        self.center[0] = newX + self.bbox[2] / 2
        self.center[1] = newY + self.bbox[3] / 2

        self.bbox[0] = newY
        self.bbox[1] = newX

    def prepareForDrawing(self):
        """
        Create the QPixmap and the mask to hhighlight the contour of the selected fragments.
        """

        if self.qimage is not None and self.qpixmap is None:
            self.qpixmap = QPixmap.fromImage(self.qimage)

        if self.qimage_back is not None and self.qpixmap_back is None:
            self.qpixmap_back = QPixmap.fromImage(self.qimage_back)

        if self.qimage is not None and self.qpixmap_contour is None:
            mask = self.createMask(self.qimage)
            m = measure.moments(mask)
            c = np.array((m[0, 1] / m[0, 0], m[1, 0] / m[0, 0]))
            self.center = np.array((c[0] + self.bbox[1], c[1] + self.bbox[0]))
            self.qpixmap_contour = self.createContourFromMask(mask)

        if self.qimage_back is not None and self.qpixmap_contour_back is None:
            mask = self.createMask(self.qimage_back)
            self.qpixmap_contour_back = self.createContourFromMask(mask)

    def createContourFromMask(self, mask):

        mask_eroded = skimage.morphology.binary_dilation(mask, skimage.morphology.disk(5))
        mask_dilated = skimage.morphology.binary_erosion(mask, skimage.morphology.disk(5))

        contour = (~mask & mask_eroded) | (~mask & mask_dilated)
        qimg = maskToQImageWTrasparency(contour)
        pxmap = QPixmap.fromImage(qimg)

        return pxmap
    
    def drawBorders(self, scene, back=False, enabled=True, zvalue_borders=0):
        if back is True:
            if self.qpixmap_contour_back is not None and enabled:
                self.qpixmap_contour_back_item = scene.addPixmap(self.qpixmap_contour_back)
                self.qpixmap_contour_back_item.setZValue(zvalue_borders)
                self.qpixmap_contour_back_item.setPos(self.bbox[1], self.bbox[0])
        else:
            if self.qpixmap_contour is not None and enabled:
                self.qpixmap_contour_item = scene.addPixmap(self.qpixmap_contour)
                self.qpixmap_contour_item.setZValue(zvalue_borders)
                self.qpixmap_contour_item.setPos(self.bbox[1], self.bbox[0])

    def undrawBorders(self, scene, back=False):
        if back is True:
            if self.qpixmap_contour_back_item is not None:
                scene.removeItem(self.qpixmap_contour_back_item)
                del self.qpixmap_contour_back_item
                self.qpixmap_contour_back_item = None
        else:
            if self.qpixmap_contour_item is not None:
                scene.removeItem(self.qpixmap_contour_item)
                del self.qpixmap_contour_item
                self.qpixmap_contour_item = None

    def enableIds(self, enabled):
        if self.id_item is not None:
            self.id_item.setVisible(enabled)
        if self.id_back_item is not None:
            self.id_back_item.setVisible(enabled)
    
    def reapplyTransformsOnVerso(self, rotated=False):
        if self.id_back_item is not None:
            self.id_back_item.resetTransform()
            transf = QTransform()
            transf.scale(-1, 1)  # Flip along the x-axis
            if rotated:
                transf.rotate(180)
            self.id_back_item.setTransform(transf)

    def drawFragment(self, scene, back=False, selected=False, zvalue_fragments=0, zvalue_ids=0, zvalue_borders=0, border_enabled=True):
        if back:
            # if it has just been created remove the current graphics item in order to set it again
            if self.qpixmap_back_item is not None:
                scene.removeItem(self.qpixmap_back_item)
                scene.removeItem(self.id_back_item)
                del self.qpixmap_back_item
                del self.id_back_item
                self.qpixmap_back_item = None
                self.id_back_item = None

                self.undrawBorders(scene, back=back)
                self.prepareForDrawing()

            self.qpixmap_back_item = scene.addPixmap(self.qpixmap_back)
            self.qpixmap_back_item.setZValue(zvalue_fragments)
            self.qpixmap_back_item.setPos(self.bbox[1], self.bbox[0])

            if selected:
                self.drawBorders(scene, back=True, enabled=border_enabled, zvalue_borders=zvalue_borders)

            font_size = 70
            self.id_back_item = TextItem(str(os.path.basename(self.filename)), QFont("Roboto", font_size, QFont.Bold))
            self.id_back_item.setPos(self.center[0], self.center[1])
            # super trick: if the whole scene is rotated 180 degrees, the text should be rotated as well so it always looks upright
            self.id_back_item.setZValue(zvalue_ids)
            self.id_back_item.setBrush(Qt.white)

            if selected:
                self.id_back_item.setOpacity(1.0)
            else:
                self.id_back_item.setOpacity(0.7)

            scene.addItem(self.id_back_item)

        else:
            # if it has just been created remove the current graphics item in order to set it again
            if self.qpixmap_item is not None:
                scene.removeItem(self.qpixmap_item)
                scene.removeItem(self.id_item)
                del self.qpixmap_item
                del self.id_item
                self.qpixmap_item = None
                self.id_item = None

                self.undrawBorders(scene, back=back)
                self.prepareForDrawing()

            self.qpixmap_item = scene.addPixmap(self.qpixmap)
            self.qpixmap_item.setZValue(zvalue_fragments)
            self.qpixmap_item.setPos(self.bbox[1], self.bbox[0])

            if selected:
                self.drawBorders(scene, enabled=border_enabled, zvalue_borders=zvalue_borders)

            font_size = 70
            self.id_item = TextItem(str(os.path.basename(self.filename)), QFont("Roboto", font_size, QFont.Bold))
            # bbox = fragment.bbox
            # fragment.id_item.setTransformOriginPoint(QPointF(fragment))
            self.id_item.setPos(self.center[0], self.center[1])
            self.id_item.setZValue(zvalue_ids)
            self.id_item.setBrush(Qt.white)

            if selected:
                self.id_item.setOpacity(1.0)
            else:
                self.id_item.setOpacity(0.7)

            scene.addItem(self.id_item)

    def undrawFragment(self, scene):
        scene.removeItem(self.qpixmap_back_item)

        if self.qpixmap_back_item is not None:
            scene.removeItem(self.qpixmap_back_item)
            del self.qpixmap_back_item
            self.qpixmap_back_item = None

        if self.qpixmap_contour_back_item is not None:
            scene.removeItem(self.qpixmap_contour_back_item)
            del self.qpixmap_contour_back_item
            self.qpixmap_contour_back_item = None

        if self.id_back_item is not None:
            scene.removeItem(self.id_back_item)
            del self.id_back_item
            self.id_back_item = None

        if self.qpixmap_item is not None:
            scene.removeItem(self.qpixmap_item)
            del self.qpixmap_item
            self.qpixmap_item = None

        if self.qpixmap_contour_item is not None:
            scene.removeItem(self.qpixmap_contour_item)
            del self.qpixmap_contour_item
            self.qpixmap_contour_item = None

        if self.id_item is not None:
            scene.removeItem(self.id_item)
            del self.id_item
            self.id_item = None

        scene.invalidate()

    def select(self, scene, back=False, border_enabled=True, zvalue_borders=0, zvalue_ids=0):
        self.undrawBorders(scene, back=back)
        self.prepareForDrawing()
        self.drawBorders(scene, back=back, enabled=border_enabled, zvalue_borders=zvalue_borders)

        self.id_item.setZValue(zvalue_ids)
        self.id_item.setOpacity(1.0)

    def deselect(self, scene, back=False, zvalue_ids=0):
        self.undrawBorders(scene, back=back)
        self.id_item.setZValue(zvalue_ids)
        self.id_item.setOpacity(0.7)

    def fromDict(self, dict):
        """
        Set the blob information given it represented as a dictionary.
        """

        self.id = int(dict["id"])
        self.group_id = int(dict["group id"])
        self.filename = dict["filename"]
        self.name = dict["name"]
        self.note = dict["note"]
        self.bbox = dict["bbox"]
        self.center = np.asarray(dict["center"])

        if self.filename != "":
            self.qimage = QImage(self.filename)
            filename_back = self.filename[:-4] + "_back" + self.filename[-4:]
            self.qimage_back = QImage(filename_back)

            self.prepareForDrawing()

    def save(self):
        return self.toDict()

    def toDict(self):
        """
        Put the fragment information in a dictionary.
        """

        dict = {}

        dict["filename"] = self.filename
        dict["name"] = self.name
        dict["id"] = self.id
        dict["group id"] = self.group_id
        dict["note"] = self.note
        dict["bbox"] = self.bbox
        dict["center"] = self.center.tolist()

        return dict


