from Athena import AtCore, AtConstants
from . import polygonShape

from maya import cmds
from maya.api import OpenMaya as om

__all__ = ('NoNGons',)


class NoTris(polygonShape.PolygonShape):
    """
    Check the scene to ensure there is no triangle.
    """

    def __init__(self):
        pass

    def check(self, mode='tris'):
    	raise
        super(NoTris, self).check(mode=mode)
