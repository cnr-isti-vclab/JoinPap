from PyQt5.QtCore import Qt

from source.tools.PickPoints import PickPoints
from source.tools.EditPoints import EditPoints
from source.tools.Scribbles import Scribbles
from source.tools.DrawLine import DrawLine

from source.tools.Move import Move

class Tools(object):
    def __init__(self, viewerplus):

        self.tool = "PAN"
        self.scene = viewerplus.scene
        self.viewerplus = viewerplus

        self.pick_points = PickPoints(self.scene)
        self.edit_points = EditPoints(self.scene)
        self.scribbles = Scribbles(self.scene)

        self.CROSS_LINE_WIDTH = 2
        self.extreme_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}

        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None

    def createTools(self):

        # create all the tools
        self.tools = {
            "MOVE": Move(self.viewerplus),
            "DRAWLINE": DrawLine(self.viewerplus),
        }

    def setTool(self, tool):
        self.resetTools()
        self.tool = tool

    def resetTools(self):

        self.pick_points.reset()
        self.edit_points.reset()
        self.scribbles.reset()

        self.scene.invalidate(self.scene.sceneRect())

    def leftPressed(self, x, y, mods = None):

        if self.tool == "PAN":
            return

        self.tools[self.tool].leftPressed(x, y, mods)

    def rightPressed(self, x, y, mods = None):

        self.tools[self.tool].rightPressed(x, y, mods)

    def mouseMove(self, x, y):

        if self.tool == "PAN":
            return

        self.tools[self.tool].mouseMove(x, y)

    def leftReleased(self, x, y):

        if self.tool == "PAN":
            return

        self.tools[self.tool].leftReleased(x, y)

    def wheel(self, delta):

        if self.tool == "PAN":
            return

        self.tools[self.tool].wheel(delta)

    def applyTool(self):

        if self.tool == "PAN":
            return

        self.tools[self.tool].apply()





