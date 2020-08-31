import sys
import unittest

from Athena import AtCore, AtUtils

# if big_O module is available, load it.
try:
    import big_O
except ImportError:
    big_O = None


# ---------------------------------------------------------------------------------------------------------- Test Process


class TestProcess(unittest.TestCase):

    PROCESS = None

    def setUp(self):
        pass

    def test_isProcessSubclass(self):
        self.assertTrue(issubclass(self.PROCESS.__class__, AtCore.Process))

    def test_nonOverridedCoreMethods(self):
        nonOverridableAttributesOverrided = self.PROCESS.__class__._Process__NON_OVERRIDABLE_ATTRIBUTES.intersection(set(self.PROCESS.__class__.__dict__.keys()))
        self.assertFalse(bool(nonOverridableAttributesOverrided))

    def test_checkIsImplemented(self):
        self.assertTrue(hasattr(self.PROCESS, 'check'))

    def test_hasAtLeastOneThread(self):
        self.assertTrue(bool(self.PROCESS.threads))

    def test_processIsDocumented(self):
        self.assertTrue(bool(self.PROCESS._doc_))


def __testProcess():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestProcess))
    unittest.TextTestRunner(verbosity=2).run(suite)


def testProcessFromPath(processStrPath, args=[], kwargs={}):
    """Method to process unit tests on a process str

    """
    module, process = AtUtils.importProcessPath(processStrPath)
    TestProcess.PROCESS = process(*args, **kwargs)
    __testProcess()

    
def testFromProcessInstance(processInstance):
    TestProcess.PROCESS = processInstance
    __testProcess()


# ---------------------------------------------------------------------------------------------------------- Test Env


class TestEnv(unittest.TestCase):

    ENV = None

    def setUp(self):
        pass

    # def test_isProcessSubclass(self):
    #     self.assertTrue(issubclass(self.PROCESS.__class__, AtCore.Process))

    def test_headerIsDefined(self):
        self.assertTrue(hasattr(self.ENV, 'header'))

    def test_registerIsDefined(self):
        self.assertTrue(hasattr(self.ENV, 'register'))

    def test_allRegisterKeysAreDefinedInHeader(self):
        header = getattr(self.ENV, 'header')
        register = getattr(self.ENV, 'register')

        self.assertTrue(all(key in header for key in register))


def __testEnv():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnv))
    unittest.TextTestRunner(verbosity=2).run(suite)


def testEnvFromPath(contextStrPath, envStr):
    """Method to process unit tests on a process instance

    """
    envs = AtUtils.getEnvs(contextStrPath, software=AtUtils.getSoftware())
    env = envs.get(envStr)

    TestEnv.ENV = AtUtils.importFromStr(env['import'])
    __testEnv()


# ---------------------------------------------------------------------------------------------------------- Test __main__


if __name__ == '__main__':
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestProcess))

    unittest.TextTestRunner(verbosity=1).run(suite)
