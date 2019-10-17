import os
import re
import sys
import pkgutil
import logging
import importlib

from types import FunctionType

from Athena import AtConstants

LOGGER = logging.getLogger(AtConstants.PROGRAM_NAME)


def getEnvs(package, software='standalone', verbose=False):
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

    availableEnvs = {}
    packagePath, athenaPackage = package.rsplit('.', 1)

    # {path}.{program}_{prod}.{software}.env
    envPackageStr = AtConstants.ENV_TEMPLATE.format(
        package=packagePath, 
        athenaPackage=athenaPackage,
        software=software
    )

    envPackage = importFromStr(envPackageStr)
    if not envPackage:
        return

    for importer, name, _ in pkgutil.iter_modules(envPackage.__path__):
        env = '{0}.{1}'.format(envPackageStr, name)
        path = importer.path
        icon = os.path.join(path, '{0}.png'.format(name))
        envModule = importFromStr(env)

        availableEnvs[name] = {
            'import': env,
            'module': envModule,
            'path': path,
            'icon': icon if os.path.isfile(icon) else None,
            'parameters': getattr(envModule, 'parameters', {})
        }

    return availableEnvs


def getPackages(verbose=False):
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

    packages = {}

    rules = []
    # Append the rules list with all rules used to get package that end with {PROGRAM_NAME}_?_???
    rules.append('.*?')  # Non-greedy match on filler
    rules.append('({}_(?:[A-Za-z0-9_]+))'.format(AtConstants.PROGRAM_NAME))  # Match {PROGRAM_NAME}_? pattern.
    rules.append('.*?')  # Non-greedy match on filler
    rules.append('([A-Za-z0-9_]+)')    # Word that match alpha and/or numerics, allowing '_' character.

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
            
        module = importFromStr(loadedPackage)

        path = os.path.dirname(module.__file__)
        icon = os.path.join(path, 'icon.png')
        
        packages[groups[-1]] = {
            'path': path,
            'import': loadedPackage,
            'module': module,
            'icon': icon if os.path.isfile(icon) else None
        }

        if verbose:
            log('Package "{}" found'.format(loadedPackage), 'info')

    return packages


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
            software = formatSoftware(softwarePath=process.name())
            if software:
                return software
                
    # Fallback on sys.argv[0] or sys.executable (This depends on the current interpreter)
    pythonInterpreter = sys.argv[0] or sys.executable
    if pythonInterpreter:
        software = formatSoftware(softwarePath=pythonInterpreter)
        if software:
            return software
    
    # Fallback on PYTHONHOME or _ environment variable
    pythonHome = os.environ.get('PYTHONHOME', os.environ.get('_', ''))
    if pythonHome:
        software = formatSoftware(softwarePath=pythonHome)
        if software:
            return software

    return default

def formatSoftware(softwarePath):
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
    # verbose=True
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


# could be only with instance of class. (get inheritance and return dict with each one as key and list of overriden as value)
def getOverriddedMethods(instance, cls):
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

        if isinstance(value, (FunctionType, classmethod)):
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

'''
def log(message, level='info'):
    """
    0 = info
    1 = warning
    2 = error
    3 = critical
    4 = exception
    5 = log
    6 = biglog
    """

    if level not in ('info', 'warning', 'error', 'critical', 'exception'):
        return

    elif level == 'info':
        LOGGER.info(str(message))
    elif level == 'warning':
        LOGGER.warning(str(message))
    elif level == 'error':
        LOGGER.error(str(message))
    elif level == 'critical':
        LOGGER.critical(str(message))
    elif level == 'exception':
        LOGGER.exception(str(message))
        

def logHeader(message):

    message = str(message)

    lenForDisplay = ((len(message)+5)/2)
    block = '=-'*(lenForDisplay if 50 < lenForDisplay else 50) + '='
    box = '# {0} #'

    print('\n{0}\n{1}\n{2}'.format(
        box.format(block),
        box.format(message.center(len(block))),
        box.format(block)
    ))
'''

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