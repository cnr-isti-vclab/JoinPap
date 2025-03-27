# this is an abstract class that represents a movable object in the window

class Movable(object):
    def draw(self, scene, **kwargs):
        return NotImplementedError

    def undraw(self, scene, **kwargs):
        return NotImplementedError

    def select(self, scene, **kwargs):
        return NotImplementedError

    def deselect(self, scene, **kwargs):
        return NotImplementedError
    
    def enableIds(self, enable):
        return NotImplementedError

    def reapplyTransformsOnVerso(self, rotated=False):
        return NotImplementedError
    
    def displace(self, dx, dy, **kwargs):
        return NotImplementedError
    
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

    def save(self):
        return NotImplementedError
    
    def toDict(self):
        return NotImplementedError
    
    def fromDict(self, dict):
        return NotImplementedError