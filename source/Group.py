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

from PyQt5.QtCore import QObject

class Group(QObject):

    def __init__(self, name="", id=0, parent=None):
        super(QObject, self).__init__(parent)

        self.fragments = []   # list of the fragments belonging to this group
        self.name = name      # group name
        self.id = id          # unique id of the group (int)

    def addFragments(self, fragments):
        """
        Assign to this group the given a list of fragments.
        """

        for fragment in fragments:
            if fragment in self.fragments:
                pass
            else:
                fragment.group_id = self.id
                self.fragments.append(fragment)
