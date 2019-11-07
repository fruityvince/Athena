from Athena import AtCore, AtConstants

from maya import cmds
from maya.api import OpenMaya as om

import random

@AtCore.automatic
class BestModelEver(AtCore.Process):
    """
    Check:
        Check wheter the 3D models of the scene are the best evers seen or not.

    Fix:
        Nope

    Notes:
        - color is {color}
    """

    name = 'Not Best Model Ever'

    def __init__(self, color='Blue'):
        self.color = color
        self._docFormat_['color'] = color

        #print color
        
    def check(self, nodesToCheck='transform', toPrint=''):
        
        self.toCheck = cmds.ls(type=nodesToCheck)
        print self.toCheck
        rng = 100.0/5000
        for i in range(5000):
            print i
            self.setProgressValue(i*rng)
        print self.name, 'check'

        self.addFeedback('This is the second error that this check could handle', [x for x in range(10000)])

        self.isChecked = True

    def fix(self):
        if not self.isChecked:
            self.check('mesh')
        
        rng = 100.0/5000
        for i in range(5000):
            self.setProgressValue(i*rng)
        print self.name, 'fix'

        cmds.select(self.toCheck, r=True)

class ThisCheckIsBad(AtCore.Process):
    """This check is a demo to get name and docstring.
    
    Check:
        Voici le detail du check.
        
    fix:
        Voici le detail du fix.
        
    ui:
        L'ui lance tel script
        
    features:
        - numero 1
        - Have a realtime check
    
    """
    
    def __init__(self):
        pass
        
    def check(self):
        self.clearFeedback()

        rng = 100.0/2000
        for i in range(1000):
            print i
            self.setProgressValue(i*rng, 'gtfo please.')

        for i in range(1000):
            print i
            self.setProgressValue((1000+i)*rng, 'Test debug to see display change.')

        print self.name, 'check'

        self.addFeedback('This result is a test', Ellipsis, documentation='The best way to remove this error is to delete the maya preference folder.')

        self.addFeedback('This is the Second Error', Ellipsis if random.randint(False, True) else None, documentation=AtConstants.PROCESS_TEMPLATE)

    def tool(self):
        
        from gpdev.tools.checker import ui

        checker = ui.SChecker()
        # checker.show()

        return checker


class JustAnotherNonBlockingCheck(AtCore.Process):
    """This check is a demo to get name and docstring.
    
    Check:
        Voici le detail du check.
        
    fix:
        Voici le detail du fix.
        
    ui:
        L'ui lance tel script
        
    features:
        - numero 1
        - Have a realtime check
        - tamer
    
    """
    
    def __init__(self):
        pass
        
    def check(self):
        self.clearFeedback()
        
        rng = 100.0/1000
        for i in range(1000):
            self.setProgressValue(i*rng)
        print self.name, 'check'

        self.toFix = cmds.ls(type='mesh')

        self.addFeedback('This is the second error that this check could handle', self.toFix)
        self.addFeedback('This result is a test', None)

    def fix(self):
        print self.name, 'fix'
        cmds.delete(self.toFix)


@AtCore.automatic
class PolygonShape(AtCore.Process):
    """ chekc for polygons"""

    def __init__(self):
        pass

    def check(self, mode='nGons'):
        """
        args :
            mesh (str): Te mesh to search the topology anomaly.
        kwargs :
            polygon (str): the polygon type to search ("tris", "quad", "nGon", "custom")
                default "nGon".
            edges (int) : the number of edge to get the face.
                default 5.
        """

        self.toFix = []

        mIt_kMesh = om.MItDependencyNodes(om.MFn.kMesh)

        meshesCount = len(cmds.ls(type='mesh'))
        if not meshesCount:
            return 
            
        baseProgressValue = 100.0 / meshesCount
        progress = 0
        while not mIt_kMesh.isDone():
            progress += baseProgressValue
            self.setProgressValue(progress)
            mObject = mIt_kMesh.thisNode()

            dagPath = om.MDagPath.getAPathTo(mObject)

            mFnMesh = om.MFnMesh(dagPath)
            mObject_numFaces = mFnMesh.numPolygons

            for faceID in range(0, mObject_numFaces):

                vertexCount = mFnMesh.getPolygonVertices(faceID)

                # tris
                if mode == 'tris':
                    if len(vertexCount) == 3:
                        self.toFix.append('%s.f[%d]' % (dagPath.fullPathName(), faceID))

                # Quad
                if mode == 'quads':
                    if len(vertexCount) == 4:
                        self.toFix.append('%s.f[%d]' % (dagPath.fullPathName(), faceID))

                # nGons
                if mode == 'nGons':
                    if len(vertexCount) > 4:
                        self.toFix.append('%s.f[%d]' % (dagPath.fullPathName(), faceID))

            mIt_kMesh.next()

        self.addFeedback('You should not have {0}'.format(mode), 
                         toDisplay=[cmds.ls(face, shortNames=True)[0] for face in self.toFix],
                         toSelect=self.toFix)

        return self.toFix



#FIXME: The module seems to be loaded multiple time
class NoNGons(PolygonShape):

    name = 'No nGons'

    def __init__(self):
        pass

    def check(self, mode='nGons'):
        print self.name, 'check'
        super(NoNGons, self).check(mode=mode)


class NoTris(PolygonShape):
    """
    Check the scene to ensure there is no triangle.
    """

    def __init__(self):
        pass

    def check(self, mode='tris'):
        print self.name, 'check'
        super(NoTris, self).check(mode=mode)
        # super(NoTris.inherit, self).check(mode='tris')


@AtCore.automatic
class NoConstructionHistory(AtCore.Process):

    def check(self):

        self.toCheck = cmds.ls(dag=True, type='transform', long=True)

        baseProgressValue = 100. / (len(self.toCheck) or 1)
        for i, each in enumerate(self.toCheck):
            self.setProgressValue(baseProgressValue * i, text='Checking: {0}'.format(each))

            history = cmds.listHistory(each, future=False, pruneDagObjects=True)

            if history:
                self.toFix.append(each)

        self.addFeedback(
                title='These nodes have construction history',
                toDisplay=[cmds.ls(node, shortNames=True)[0] for node in self.toFix],
                toSelect=self.toFix
            )

    def fix(self):

        if not self.isChecked:
            self.check()

        for each in self.toFix:
            cmds.delete(each, constructionHistory=True)