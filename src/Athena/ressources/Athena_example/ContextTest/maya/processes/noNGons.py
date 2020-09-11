from Athena import AtCore, AtConstants
from . import polygonShape

from maya import cmds
from maya.api import OpenMaya as om

__all__ = ('NoNGons',)


class NoNGons(polygonShape.PolygonShape):

    def __init__(self):
        pass

    def check(self, mode='nGons'):
    	raise Exception
        super(NoNGons, self).check(mode=mode)
