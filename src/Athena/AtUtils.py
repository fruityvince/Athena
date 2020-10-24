import os
import re
import sys
import pkgutil
import logging
import importlib

import types

try:
    reload  # Python 2.7
except NameError:
    try:
        from importlib import reload  # Python 3.4+
    except ImportError:
        from imp import reload  # Python 3.0 - 3.3

from Athena import AtConstants

LOGGER = logging.getLogger(AtConstants.PROGRAM_NAME)


def iterBlueprintsPath(package, software='standalone', verbose=False):
    """Retrieve available envs from imported packages.

    Retrieve the currently imported packages path that match the pattern to works with this tool: {program}_{prod}
    Then, generate the usual path to the env using the package, the current software for the first sub package and env to the 
    desired package.

    parameters
    -----------
    package: str
        This is the string path to a python package.
    software: str, optional
        The software for which to get envs. (default: 'standalone')
    verbose: bool
        Define if the function should log informations about its process.

    Returns
    --------
    dict
        Return a dict containing all envs for the given package and software.
        The key is the env and the value is a dict containing the imported module object for the env and its str path.
    """

    packagePath = os.path.dirname(package.__file__)
    for loader, moduleName, _ in pkgutil.iter_modules(package.__path__):
        yield os.path.join(packagePath, '{}.py'.format(moduleName))


def getPackages():
    """Get all packages that match the tool convention pattern.

    Loop through all modules in sys.modules.keys() and package those who match the tool convention pattern
    that is {PROGRAM_NAME}_???

    parameters
    -----------
    verbose: bool
        Define if the function should log informations about its process. (default: False)

    Returns
    --------
    dict
        Return a dict containing all package that match the pattern of the tool
        The key is the prod and the value is a dict containing the module object and its str path.
    """

    packages = []

    rules = []
    # Append the rules list with all rules used to get package that end with {PROGRAM_NAME}_?_???
    rules.append(r'.*?')  # Non-greedy match on filler
    rules.append(r'({}_(?:[A-Za-z0-9_]+))'.format(AtConstants.PROGRAM_NAME))  # Match {PROGRAM_NAME}_? pattern.
    rules.append(r'.*?')  # Non-greedy match on filler
    rules.append(r'([A-Za-z0-9_]+)')  # Word that match alpha and/or numerics, allowing '_' character.

    regex = re.compile(''.join(rules), re.IGNORECASE|re.DOTALL)

    for loadedPackage in sys.modules.keys():

        # Ignore all module unrelated to this tool.
        if AtConstants.PROGRAM_NAME not in loadedPackage:
            continue

        search = regex.search(loadedPackage)
        if not search:
            continue

        groups = search.groups()
        if not loadedPackage.endswith('.'.join(groups)):
            continue
        
        packages.append(loadedPackage)

        LOGGER.debug('Package "{}" found'.format(loadedPackage))

    return tuple(packages)


def importProcessModuleFromPath(processStrPath):

    moduleStrPath, _, processName = processStrPath.rpartition('.')
    module = importFromStr(moduleStrPath)

    if not hasattr(module, processName):
        raise ImportError('Module {0} have no class named {1}'.format(module.__name__, processName))
    
    return module


def getSoftware(default='standalone'):
    """Get the current software from which the tool is executed.

    Fallback on different instruction an try to get the current running software.
    If no software are retrieved, return the default value.

    parameters
    -----------
    default: str
        The default value to return if no software was retrieved. (default: 'standalone')
    verbose: bool
        Define if the function should log informations about its process. (default: False)

    Returns
    --------
    str
        Return the current software if any are find else the default value.
    """

    # First, try to get the current application Name
    # applicationName  = QtWidgets.QApplication.applicationName()
    # if applicationName:
    #     software = formatSoftware(softwarePath=applicationName, verbose=verbose)
    #     print 'Software = ', software
    #     if software:
    #         return software
        
    # Fallback on the most efficient solution if psutil package is available

    if 'psutil' in sys.modules:
        import psutil
        process = psutil.Process(os.getpid())
        if process:
            software = _formatSoftware(softwarePath=process.name())
            if software:
                return software
                
    # Fallback on sys.argv[0] or sys.executable (This depends on the current interpreter)
    pythonInterpreter = sys.argv[0] or sys.executable
    if pythonInterpreter:
        software = _formatSoftware(softwarePath=pythonInterpreter)
        if software:
            return software
    
    # Fallback on PYTHONHOME or _ environment variable
    pythonHome = os.environ.get('PYTHONHOME', os.environ.get('_', ''))
    if pythonHome:
        software = _formatSoftware(softwarePath=pythonHome)
        if software:
            return software

    return default

def _formatSoftware(softwarePath):
    """Check if there is an available software str in the hiven Path

    parameters
    -----------
    softwarePath: str
        The path to a software executable is expected here, but this works with any str.
    verbose: bool
        Define if the function should log informations about its process. (default: False)

    Returns
    --------
    str
        Return the software found in softwarePath if there is one or an empty string.
    """

    path = str(softwarePath).lower()
    for soft in AtConstants.AVAILABLE_SOFTWARE:
        soft = soft.lower()
        
        if '{0}{1}{0}'.format(os.sep, soft) in path:
            return soft
        elif soft in path:
            return soft
            
    return ''


def pythonImportPathFromPath(path):
    if not os.path.exists(path):
        raise IOError('Path `{}` does not exists.'.format(path))

    path_, file_ = None, None    
    if os.path.isfile(path):
        path_, _, file_ = path.rpartition(os.sep)
    elif os.path.isdir(path):
        path_, file_ = path, None
    
    incrementalPath = ''
    pythonImportPath = ''
    for i, folder in enumerate(path_.split(os.sep)):
        if i == 0:
            incrementalPath = folder or os.sep
            continue
        else:
            incrementalPath += '{}{}'.format(os.sep, folder)

        if '__init__.py' in os.listdir(incrementalPath):
            pythonImportPath += '{}{}'.format('.' if pythonImportPath else '', folder)
    
    if file_:
        pythonImportPath += '.' + os.path.splitext(file_)[0]
    
    return pythonImportPath


def importFromStr(moduleStr, verbose=False):
    """Try to import the module from the given string

    parameters
    -----------
    moduleStr: str
        Path to a module to import.
    verbose: bool
        Define if the function should log informations about its process. (default: False)

    Returns
    --------
    str
        Return the loaded module or None if fail.
    """

    module = None  #Maybe QC Error ?
    try:
        # module = __import__(moduleStr, fromlist=[''])
        module = importlib.import_module(moduleStr) #TODO: if multiple checks come from same module try to load module multiple time
        if verbose: 
            LOGGER.info('import {} success'.format(moduleStr))
    except ImportError as exception:
        if verbose: 
            LOGGER.exception('load {} failed'.format(moduleStr))

        raise ImportError(exception) # AtEnvImportError - exception.args

    return module


def reloadModule(module):
    return reload(module)


def moduleFromStr(pythonCode, name='DummyAthenaModule'):
    # spec = importlib.util.spec_from_loader(name, loader=None)

    # module = importlib.util.module_from_spec(spec)

    # exec(pythonCode, module.__dict__)
    # sys.modules[name] = module

    # return module

    module = types.ModuleType(name)
    exec(pythonCode, module.__dict__)
    sys.modules[name] = module

    module.__file__ = ''

    return module


def importPathStrExist(moduleStr):
    return bool(pkgutil.find_loader(moduleStr))


# could be only with instance of class. (get inheritance and return dict with each one as key and list of overriden as value)
def getOverridedMethods(instance, cls):
    """Detect all methods that have been overridden from a subclass of a class

    Parameters
    -----------
    instance: object
        An instance of a subclass of cls.
    cls: object
        An object type to compare the instance to.

    Returns
    --------
    list
        Return a list containing all method that have been overridden from the instance in the given class.
    """

    res = {}
    for key, value in instance.__dict__.items():

        if isinstance(value, classmethod):
            value = callable(getattr(instance, key))

        if isinstance(value, (types.FunctionType, classmethod)):
            method = getattr(cls, key, None)
            if method is not None and callable(method) is not value:
                res[key] = value

    return res


def camelCaseSplit(toSplit):
    """Format a string write with camelCase convention into a string with space.

    Parameters
    -----------
    toSplit: str
        The string to split and format

    Returns
    --------
    str
        Return the given string with spaces.
    """

    matches = re.finditer('(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', toSplit)
    splitString = []

    # Index of beginning of slice
    previous = 0
    for match in matches:
        # get slice
        splitString.append(toSplit[previous:match.start()])

        # advance index
        previous = match.start()

    # get remaining string
    splitString.append(toSplit[previous:])

    return ' '.join(splitString)


class lazyProperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, cls):
        value = self.fget(instance)
        setattr(instance, self.fget.__name__, value)
        return value


class RessourcesManager(object):
    #TODO: Document this class

    INSTANCE = None

    class __RessourcesManager:
        """docstring for __RessourceManager"""

        PATH = '__path__'
        _ressources = {}

        def __init__(self):
            pass

        def __getitem__(self, value):

            if not isinstance(value, basestring):
                raise KeyError('{0} indices must be str, not {1}'.format(self.__class__, type(value)))

            for ressource in self.__ressources:
                if ressource.endswith(value):
                    self.__last_query = ressource
                    return ressource

        def get(self, toGet, key, asType=str, fallback=None, args=None, kwargs=None):
            """Get a specific ressource in the given reader and in the specified object type.

            If the item can't be retrieved in the specific type, return the given fallback (default: None).
            You can specify args and kwargs to cast you ressource in the desired object type with your parameters.

            Parameters
            -----------
            toGet: str
                Name of the ressource to get. (Should contain the file extension. e.g. icon.png)
            key: str
                Name of the reader to use, if the reader does not exists, return the fallback.
            asType: type, default: str
                The type in which cast the retrieved ressource. Instantiate it if it does not exists in the reader.
            fallback: default: None
                The value to return if nothing is found.
            args: list or NoneType, default: None
                List of arguments to use when cast the ressource in the given type.
            args: dict or NoneType, default: None
                Dict of keyword arguments to use when cast the ressource in the given type.

            Returns
            --------
            object
                Return the queried ressource in the given type or the fallback value.
            """

            keyData = self._ressources.get(key, None)
            if keyData is None:
                return fallback

            strData = keyData.get(str, None)
            if strData is None:
                return fallback
            
            dataAsStr = strData.get(toGet, None)
            if dataAsStr is None:
                return fallback

            if asType is str:
                return dataAsStr

            args = args or []
            kwargs = kwargs or {}

            dataAsType = fallback
            asTypeData = keyData.get(asType, None)

            # Data is not in the RessourceManager
            if asTypeData is None:
                try: 
                    dataAsType = asType(dataAsStr, *args, **kwargs)
                    keyData[asType] = {toGet: dataAsType}
                except:
                    return fallback

            # Data is in the RessourceManager
            else:
                dataAsType = asTypeData.get(toGet, None)
                if dataAsType is None:
                    dataAsType = asType(dataAsStr)
                    asTypeData[toGet] = dataAsType

            return dataAsType

        def _addReader(self, path, backPath='', key=None):

            key = key or path
            if path not in self._ressources:
                folderPath = self.__getFolderPath(path)

                folderPath = self.__searchFolder(folderPath, backPath=backPath)
                files = self.__getFiles(folderPath)

                self._ressources[key] = {}
                self._ressources[key][str] = files
                self._ressources[key][self.PATH] = folderPath

        def __getFolderPath(self, path):

            path = os.path.abspath(path)
            if os.path.isfile(path):
                path = os.path.dirname(path)

            return path

        def __searchFolder(self, path, backPath=''):

            return os.path.join(path, backPath)

        def __getFiles(self, path):

            files = {}
            for path_, _, files_ in os.walk(path):
                for file in files_:
                    file = os.path.abspath(os.path.join(path_, file))
                    if os.path.isfile(file):
                        files[os.path.basename(file)] = file
                        
            return files

    def __new__(cls, path=None, backPath='', key=None, reset=False):

        if reset:
            cls.INSTANCE = None
            
        if cls.INSTANCE is None:
            cls.INSTANCE = cls.__RessourcesManager()

        if key not in cls.INSTANCE._ressources:
            cls.INSTANCE._addReader(path, backPath=backPath, key=key)

        return cls.INSTANCE

    def __getattr__(self, name):
        return getattr(self.INSTANCE, name)

    def __setattr__(self, name):
        return setattr(self.INSTANCE, name)


def softwareSelection(toSelect):
    """Select the given object from list in the software.

    parameters
    -----------
    toSelect: list
        List of objects to select.

    Raises
    ------
    NotImplementedError
        If the software is a software where the selection is not implemented.
    """
    software = getSoftware()

    if software == 'maya':
        from maya import cmds

        try:
            cmds.select(toSelect, noExpand=True)
        except:
            pass
        return

    elif software == 'katana':
        from Katana import NodegraphAPI

        try:
            NodegraphAPI.SetAllSelectedNodes(toSelect)
        except:
            pass
        return

    elif software == 'blender':
        import bpy

        try:
            bpy.ops.object.select_all(action='DESELECT')
            for each in toSelect:
                each.select_set(True)
        except:
            pass
        return


class SearchPattern(object):

    MATCH_NONE = '^$'

    TEXT_PATTERN = r'(?!#)(^.+?)(?:(?=\s(?:#)[a-zA-Z]+)|$|\s$)'
    TEXT_REGEX = re.compile(TEXT_PATTERN)

    HASH_PATTERN = r'(?:^|\s)?#([a-zA-Z\s]+)(?:\s|$)'
    HASH_REGEX = re.compile(HASH_PATTERN)

    def __init__(self, rawPattern=MATCH_NONE):

        self._rawPattern = rawPattern

        self._pattern = None
        self._regex = None
        self._isValid = False

        self.setPattern(rawPattern)

    @property
    def pattern(self):
        return self._pattern

    @property
    def regex(self):
        return self._regex      

    @property
    def isValid(self):
        return self._isValid

    def setPattern(self, pattern):
        match = self.TEXT_REGEX.match(pattern)
        self._pattern = pattern = '.*' if not match else match.group(0)

        try:
            self._regex = re.compile(pattern)
            self._isValid = True
        except Exception:
            self._regex = re.compile(self.MATCH_NONE)
            self._isValid = False

    def iterHashTags(self):
        for match in self.HASH_REGEX.finditer(self._rawPattern):
            yield match.group(1)

    def search(self, text):
        if not self._isValid:
            return False

        return self._regex.search(text)


def formatTraceback(traceback):
    return '# ' + '# '.join(traceback.rstrip().splitlines(True))


def createNewAthenaPackageHierarchy(rootDirectory):

    if os.path.exists(rootDirectory):
        raise OSError('`{}` already exists. Abort {0} package creation.'.format(AtConstants.PROGRAM_NAME))
    os.mkdir(rootDirectory)

    blueprintDirectory = os.path.join(rootDirectory, 'blueprints')
    os.mkdir(blueprintDirectory)
    processesDirectory = os.path.join(rootDirectory, 'processes')
    os.mkdir(processesDirectory)

    initPyFiles = (
        os.path.join(rootDirectory, '__init__.py'),
        os.path.join(blueprintDirectory, '__init__.py'),
        os.path.join(processesDirectory, '__init__.py')
        )
    
    header = '# Generated from {0} - Version {1}\n'.format(AtConstants.PROGRAM_NAME, AtConstants.VERSION)
    for file in initPyFiles:
        with open(file, 'w') as file:
            file.write(header)

    dummyProcessPath = os.path.join(processesDirectory, 'dummyProcess.py')
    with open(dummyProcessPath, 'w') as file:
        file.write(header + AtConstants.DUMMY_PROCESS_TEMPLATE)

    dummyBlueprintPath = os.path.join(blueprintDirectory, 'dummyBlueprint.py')
    with open(dummyBlueprintPath, 'w') as file:
        file.write(header + AtConstants.DUMMY_BLUEPRINT_TEMPLATE)

##########  IDEAS  ##########
"""

[Athena_{whatever}]
|___[prod]
    |___[software]
        |___[env]
            [processes]
"""

"""
class AbstractClass(object):
    
    def __new__(self):
        if self is AbstractClass:
            raise NotImplementedError('{}: cannot instantiate abstract class'.format(self.__name__))
        
        return super(AbstractClass, self).__new__(self)
        
    def hello(self, kwarg='hello world'):
        print kwarg
        
toto = AbstractClass()

class fffgt(AbstractClass):
    
    def __init__(self):
        self.hello()
        
ffff = fffgt()
"""