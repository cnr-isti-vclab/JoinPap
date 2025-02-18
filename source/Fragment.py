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
import skimage.morphology

from skimage import measure
from PyQt5.QtGui import QImage, QPixmap

from source.utils import qimageToNumpyArray, maskToQImage, maskToQImageWTrasparency

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

            filename_back = filename[:-4] + "_back" + filename[-4:]
            self.qimage_back = QImage(filename_back)
            self.qimage_back = self.qimage_back.mirrored(True, False)
            self.qimage_back = self.qimage_back.convertToFormat(QImage.Format_ARGB32)

            # BBOX FORMAT: top, left, width, height
            self.bbox = [offset_y, offset_x, self.qimage.width(), self.qimage.height()]

            # center is (x, y)
            self.center = np.array((offset_x + self.qimage.width()/2, offset_y + self.qimage.height()/2))

            self.prepareForDrawing()

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
            nparray = qimageToNumpyArray(self.qimage_back)
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

    def fromDict(self, dict):
        """
        Set the blob information given it represented as a dictionary.
        """

        self.filename = dict["filename"]
        self.id = int(dict["id"])
        self.group_id = int(dict["group id"])
        self.note = dict["note"]
        self.bbox = dict["bbox"]
        self.center = np.asarray(dict["center"])
        self.filename = dict["filename"]

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
        dict["id"] = self.id
        dict["group id"] = self.group_id
        dict["note"] = self.note
        dict["bbox"] = self.bbox
        dict["center"] = self.center.tolist()

        return dict


