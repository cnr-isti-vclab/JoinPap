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

class Tool(QObject):

    def __init__(self, viewerplus):
        super(Tool, self).__init__()

        self.viewerplus = viewerplus

    def leftPressed(self, x, y, mods = None):
        pass

    def rightPressed(self, x, y, mods = None):
        pass

    def mouseMove(self, x, y):
        pass

    def leftReleased(self, x, y):
        pass

    def wheel(self, delta):
        pass

    def apply(self):
        pass

    def reset(self):
        pass

    def handleTransform(self):
        pass