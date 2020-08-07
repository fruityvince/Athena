from Athena import AtCore, AtConstants

from maya import cmds
from maya.api import OpenMaya as om

__all__ = ('PolygonShape',)


@AtCore.automatic
class PolygonShape(AtCore.Process):
    """ chekc for polygons"""

    TRIS = AtCore.Thread(title='You should not have Tris in your models', defaulFailLevel=AtCore.Status.WARNING)
    NGONS = AtCore.Thread(title='You should not have NGons in your models')

    def __init__(self):
        pass

    def check(self, mode='nGons'):
        """
        args :
            mesh (str): Te mesh to search the topology anomaly.
        kwargs :
            polygon (str): the polygon type to search ("tris", "quad", "nGon")
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
                    continue

                # nGons
                if mode == 'nGons':
                    if len(vertexCount) > 4:
                        self.toFix.append('%s.f[%d]' % (dagPath.fullPathName(), faceID))

            mIt_kMesh.next()

        self.addFeedback(thread=self.TRIS if mode == 'tris' else self.NGONS, 
                         toDisplay=[cmds.ls(face, shortNames=True)[0] for face in self.toFix],
                         toSelect=self.toFix)

        return self.toFix
