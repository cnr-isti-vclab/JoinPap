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