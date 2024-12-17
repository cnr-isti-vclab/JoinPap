import os
import json
import numpy as np

from PyQt5.QtCore import QDir
from PyQt5.QtGui import QImageReader
from PyQt5.QtWidgets import QMessageBox

from source.Fragment import Fragment
from source.Group import Group
from source.Grid import Grid
import source.utils as utils

from skimage import measure
import rpack

import random

class ProjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Fragment):
            return obj.save()
        elif isinstance(obj, Grid):
            return obj.save()
        return json.JSONEncoder.default(self, obj)

class Project(object):

    def __init__(self, width, height):

        self.filename = None                   # file containing this project
        self.working_area = [width, height]    # top, left, width, height
        self.fragments = []                    # list of fragments
        self.groups = []                       # list of groups
        self.grid = None

    def load(self, piui_working_dir, filename):

        dir = QDir(piui_working_dir)
        filename = dir.relativeFilePath(filename)
        f = open(filename, "r")
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise Exception(str(e))

        f.close()

        self.filename = filename

        self.working_area = data["working_area"]

        # create all fragments
        self.fragments = []
        for fragment_data in data["fragments"]:
            fragment = Fragment("", 0, 0, 0)
            fragment.fromDict(fragment_data)
            self.fragments.append(fragment)

        # create all groups
        self.groups = []
        for group in data["groups"]:
            gr = Group()
            gr.name = group.name
            gr.id = group.id
            self.groups.append(gr)

        # assign fragments to the groups
        for fragment in self.fragments:
            if fragment.group_id >= 0:
                assigned = False
                for group in self.groups:
                    if group.id == fragment.id:
                        group.append(fragment)
                        assigned = True

                if not assigned:
                    group = Group(fragment.group_id)
                    group.append(fragment)

        # load grid
        if "grid" in data:
            self.grid = Grid(0, 0)
            self.grid.fromDict(data["grid"])

        return True

    def createGroup(self):
        """
        Creates a new group.
        """

        group_id = self.getFreeGroupId()

        name = "Group " + str(id)
        group = Group(name, group_id)
        self.groups.append(group)

        return group

    def removeGroup(self, group):
        """
        Remove the given group and update the fragments of the group
        """

        for fragment in group.fragments:
            fragment.group_id = -1

        self.groups.remove(group)
        del group

    def removeGroupByFragment(self, fragment):
        """
        Remove a group given a fragment of the group.
        """

        group_to_remove = None
        for group in self.group:
            if fragment in group.fragments:
                group_to_remove = group
                break

        if group_to_remove is not None:
            self.removeGroup(group_to_remove)

    def removeGroupById(self, group_id):
        """
        Remove a group given its id.
        """

        group_to_remove = self.getGroupById(group_id)
        self.removeGroup(group_to_remove)

    def setWorkingArea(self, working_area):

        self.working_area = working_area

    def fragmentClicked(self, x, y):

        fragments_clicked = []

        # check if the click is inside a fragment using bbox tlwh
        for fragment in self.fragments:
            if x >= fragment.bbox[1] and x <= fragment.bbox[1] + fragment.bbox[2] and y >= fragment.bbox[0] and y <= fragment.bbox[0] + fragment.bbox[3]:
                fragments_clicked.append(fragment)

        if len(fragments_clicked) == 0:
            return None
        else:

            dist_min = 100000000.0
            fragment_smallest = fragments_clicked[0]
            for fragment in fragments_clicked:
                dx = (fragment.center[0] - x)
                dy = (fragment.center[1] - y)
                dist = dx*dx + dy*dy
                if dist < dist_min:
                    dist_min = dist
                    fragment_smallest = fragment

            return fragment_smallest

    def getFragmentsOfAGroup(self, fragment):
        """
        Returns the fragments of a group given a fragment of the group.
        If the fragment does not belong to a group, None is returned.
        """

        for group in self.groups:
            if group.id == fragment.group_id:
                return group.fragments

        return None

    def getGroupById(self, group_id):
        """
        Returns the group with the given id.
        If the group does not exist, None is returned.
        """

        for group in self.groups:
            if group_id == group.id:
                return group

        return None

    def save(self, filename = None):

        data = self.__dict__
        str = json.dumps(data, cls=ProjectEncoder, indent=1)

        if filename is None:
            filename = self.filename
        f = open(filename, "w")
        f.write(str)
        f.close()

    def getFreeFragmentId(self):

        used = []
        for fragment in self.fragments:
            used.append(fragment.id)

        for id in range(len(used)):
            if id not in used:
                return id

        return len(used)


    def getFreeGroupId(self):

        used = []
        for group in self.groups:
            used.append(group.id)

        for id in range(len(used)):
            if id not in used:
                return id

        return len(used)
    
    def fragmentPacking(self, sizes):
        try:
            positions = rpack.pack(sizes, max_width=self.working_area[0], max_height=self.working_area[1])
        except rpack.PackingImpossibleError:
            print("Packing impossible in the provided working area. Trying to pack in a bigger area.")
            max_sizes = np.max(np.array(sizes, dtype=int), axis=0)
            max_width, max_height = int(max_sizes[0]), int(max_sizes[1])
            if max_width > self.working_area[0]:
                new_width = sum([size[0] for size in sizes]) + 100
                new_height = max_height
            if max_height > self.working_area[1]:
                new_height = max_height + 100
                new_width = sum([size[0] for size in sizes]) + 100

            positions = rpack.pack(sizes, max_width=new_width, max_height=new_height)

        # subtract the height of the fragment to the y position, as we have to return the upper left coordinate, while positions return the lower left
        # positions = [(x, y - h) for (x, y), (w, h) in zip(positions, sizes)]   # TODO: check here!
        return positions

    def getFreePosition(self, filename):
        """
        Returns the free position on the document.
        """

        reader = QImageReader(filename)
        width = reader.size().width()
        height = reader.size().height()

        for i in range(50):
            posx = random.randint(0, self.working_area[0])
            posy = random.randint(0, self.working_area[1])
            bbox = [posy, posx, width, height]
            intersect = False
            for fragment in self.fragments:
                intersect = utils.checkIntersection(fragment.bbox, bbox)
                if intersect is True:
                    break

            if intersect is False:
                return posx, posy

        return posx, posy

    def addFragment(self, fragment):

        self.fragments.append(fragment)

    def removeFragment(self, fragment):

        if fragment in self.fragments:
            self.fragments.remove(fragment)

    def updateFragment(self, image, old_blob, new_blob):

        # update image annotations
        image.annotations.updateBlob(old_blob, new_blob)

        # update correspondences
        for corr in self.findCorrespondences(image):
            corr.updateBlob(image, old_blob, new_blob)

