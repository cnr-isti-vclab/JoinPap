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
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)          
# for more details.                                               

# THIS FILE CONTAINS UTILITY FUNCTIONS, E.G. CONVERSION BETWEEN DATA TYPES, BASIC OPERATIONS, ETC.

import io
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, qRgb, qRgba
import numpy as np
from PIL import Image

def jointBox(boxes):
    """
    It returns the joint bounding box given a list of bounding box.
    """
    box = boxes[0]
    for b in boxes:
        box = np.array([
            min(box[0], b[0]),
            min(box[1], b[1]),
            max(box[1] + box[2], b[1] + b[2]),
            max(box[0] + box[3], b[0] + b[3])
        ])
        box[2] -= box[1]
        box[3] -= box[0]
    return box.astype(int)

def checkIntersection(bbox1, bbox2):
    """
    Check if bbox1 and bbox intersects.
    """

    # range is [minx, miny, maxx, maxy], absolute ranges
    range1 = [bbox1[0], bbox1[1], bbox1[0] + bbox1[3], bbox1[1] + bbox1[2]]
    range2 = [bbox2[0], bbox2[1], bbox2[0] + bbox2[3], bbox2[1] + bbox2[2]]

    # intersection
    range = [max(range1[0], range2[0]), max(range1[1], range2[1]), min(range1[2], range2[2]), min(range1[3], range2[3])]

    # check for intersection
    if range[2] <= range[0] or range[3] <= range[1]:
        return False
    else:
        return True

def maskToQImage(mask):

    maskrgb = np.zeros((mask.shape[0], mask.shape[1], 3))
    maskrgb[:,:,0] = mask
    maskrgb[:,:,1] = mask
    maskrgb[:,:,2] = mask
    maskrgb = maskrgb * 255
    maskrgb = maskrgb.astype(np.uint8)

    qimg = rgbToQImage(maskrgb)
    return qimg


def maskToQImageWTrasparency(mask):

    maskrgb = np.zeros((mask.shape[0], mask.shape[1], 4))
    maskrgb[:,:,0] = mask
    maskrgb[:,:,1] = mask
    maskrgb[:,:,2] = mask
    maskrgb = maskrgb * 255
    maskrgb[:,:,3] = 255
    maskrgb = maskrgb.astype(np.uint8)

    qimg = rgbToQImage(maskrgb)
    return qimg


def floatmapToQImage(floatmap, nodata = float('NaN')):

    h = floatmap.shape[0]
    w = floatmap.shape[1]

    fmap = floatmap.copy()
    max_value = np.max(fmap)
    fmap[fmap == nodata] = max_value
    min_value = np.min(fmap)

    fmap = (fmap - min_value) / (max_value - min_value)
    fmap = 255.0 * fmap
    fmap = fmap.astype(np.uint8)

    img = np.zeros([h, w, 3], dtype=np.uint8)
    img[:,:,0] = fmap
    img[:,:,1] = fmap
    img[:,:,2] = fmap

    qimg = rgbToQImage(img)

    del fmap

    return qimg

def rgbToQImage(image):

    h = image.shape[0]
    w = image.shape[1]
    ch = image.shape[2]

    imgdata = np.zeros([h, w, 4], dtype=np.uint8)

    if ch == 3:
        imgdata[:, :, 2] = image[:, :, 0]
        imgdata[:, :, 1] = image[:, :, 1]
        imgdata[:, :, 0] = image[:, :, 2]
        imgdata[:, :, 3] = 255
        qimg = QImage(imgdata.data, w, h, QImage.Format_RGB32)

    elif ch == 4:
        imgdata[:, :, 3] = image[:, :, 0]
        imgdata[:, :, 2] = image[:, :, 1]
        imgdata[:, :, 1] = image[:, :, 2]
        imgdata[:, :, 0] = image[:, :, 3]
        qimg = QImage(imgdata.data, w, h, QImage.Format_ARGB32)

    return qimg.copy()

def figureToQPixmap(fig, dpi, width, height):

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    buf.seek(0)
    img_arr = np.frombuffer(buf.getvalue(), dtype=np.uint8)
    buf.close()
    im = Image.open(buf)
    im = np.array(im)

    # numpy array to QPixmap
    qimg = rgbToQImage(im)
    qimg = qimg.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pxmap = QPixmap.fromImage(qimg)

    return pxmap

def cropQImage(qimage_map, bbox):

    left = bbox[1]
    top = bbox[0]
    h = bbox[3]
    w = bbox[2]

    qimage_cropped = qimage_map.copy(left, top, w, h)

    return qimage_cropped

def cropImage(img, bbox):
    """
    Copy the given mask inside the box used to crop the plot.
    Both joint_box and bbox are n map coordinates.
    """

    w_img = img.shape[1]
    h_img = img.shape[0]

    w = bbox[2]
    h = bbox[3]
    crop = np.zeros((h, w, 3), dtype=np.uint8)

    dest_offx = 0
    dest_offy = 0
    source_offx = bbox[1]
    source_offy = bbox[0]
    source_w = w
    source_h = h

    if bbox[0] < 0:
        source_offy = 0
        dest_offy = -bbox[0]
        source_h = h - dest_offy

    if bbox[1] < 0:
        source_offx = 0
        dest_offx = -bbox[1]
        source_w = w - dest_offx

    if bbox[1] + bbox[2] >= w_img:
        dest_offx = 0
        source_w = w_img - source_offx

    if bbox[0] + bbox[3] >= h_img:
        dest_offy = 0
        source_h = h_img - source_offy

    crop[dest_offy:dest_offy+source_h, dest_offx:dest_offx+source_w, :] = \
        img[source_offy:source_offy+source_h, source_offx:source_offx+source_w, :]

    return crop

def qimageToNumpyArray(qimg):

    w = qimg.width()
    h = qimg.height()

    arr = np.zeros((h, w, 4), dtype=np.uint8)

    bits = qimg.bits()
    bits.setsize(int(h * w * 4))
    arrtemp = np.frombuffer(bits, np.uint8).copy()
    arrtemp = np.reshape(arrtemp, [h, w, 4])
    arr[:, :, 0] = arrtemp[:, :, 2]
    arr[:, :, 1] = arrtemp[:, :, 1]
    arr[:, :, 2] = arrtemp[:, :, 0]
    arr[:, :, 3] = arrtemp[:, :, 3]

    return arr

def centimetersToPixels(cm, dpi):
    return int(cm * dpi / 2.54)

def pixelsToCentimeters(px, dpi):
    return px * 2.54 / dpi