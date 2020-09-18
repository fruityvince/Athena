import re
import os
import numbers
import six
import time
import inspect
import enum
import pkgutil
import tempfile

import cProfile
import pstats

from pprint import pprint

from Athena import AtConstants
from Athena import AtExceptions
from Athena import AtUtils


class ProcessDataDescriptor(object):

    def __init__(self):
        self.__DATA = {}

    def __get__(self, instance, cls):
        if cls in self.__DATA:
            return self.__DATA[cls]

        raise AttributeError('Object {0} does not have any data for attribute {1}', instance.__name__, self.__name)

    def __del__(self):
        raise NotImplementedError('Unable to delete Process Data')


class ProcessMeta(type):

    def __new__(self, className, bases, attrs):
        return super(ProcessMeta, self).__new__(className, bases, attrs)


class Process(object):
    """Abstract class from which any Athena User Process have to inherit.

    The Process object define default instance attributes for user to use and that are managed through the `automatic`
    decorator.
    It also comes with some methods to manage the internal feedback and the potentially connected QProgressbar.
    There is 3 not implemented methods to override if needed (`check`, `fix` and `tool`)
    """

    __NON_OVERRIDABLE_ATTRIBUTES = \
    {
        '_resetThreads',
        '_clearFeedback',
        'addFeedback',
        'DATA',
        'getFeedback',
        'getFeedbacks',
        'reset',
        'setFeedback',
        'setProgressValue',
    }

    DATA = {}

    _name_ = ''
    _doc_ = ''

    # __metaclass__ = ProcessMeta

    def __new__(cls, *args, **kwargs):
        """Generate a new class instance and setup its default attributes.
        
        The base class `Process` can't be instanciated because it is an abstract class made to be inherited
        and overrided by User Processes.
        """

        # Check if class to instanciate is Process. If True, raise an error because class is abstract.
        if cls is Process:
            raise NotImplementedError('Can not instantiate abstract class')

        # Create the instance
        instance = super(Process, cls).__new__(cls, *args, **kwargs)
        # instance.__initArgs = args
        # instance.__initKwargs = kwargs

        # Instance internal data (Must not be altered by user)
        instance.__threads = {}
        for memberName, member in inspect.getmembers(cls):
            if isinstance(member, Thread):
                processThread = ProcessThread(member)
                instance.__threads[memberName] = processThread
                instance.__dict__[memberName] = processThread

        instance.__feedbacks = {}
        instance.__progressbar = None
        instance.__setProgressValue = None

        instance.__stats = {}

        # Sunder instance attribute (Can be overrided user to custom the process)
        instance._name_ = cls._name_ or cls.__name__
        instance._doc_ = cls._doc_ or cls.__doc__

        # Public instance attribute (To be used by user to manage process data)
        instance.toCheck = []
        instance.toFix = []
        instance.isChecked = False

        # Sunder instance attribute (To be used by user to custom the process)
        instance._docFormat_ = {}  # The keys/values pair in this dict are retrieved to format the doc. To be used in __init__.

        return instance

    def __repr__(self):
        return '<Process `{0}` at {1}>'.format(self._name_, hex(id(self)))

    @property
    def data(self):
        return self.DATA

    @property
    def feedback(self):
        return self.__feedback

    @property
    def threads(self):
        return self.__threads
    
    def check(self, *args, **kwargs):
        raise NotImplementedError
        
    def fix(self, *args, **kwargs):
        raise NotImplementedError

    def tool(self, *args, **kwargs):
        raise NotImplementedError

    def setProgressbar(self, progressBar):
        self.__progressbar = progressBar

    def setProgressValue(self, value, text=None):
        """Set the progress value of the process progressBar if exist.
        
        Parameters
        -----------
        value: numbres.Number
            The value to set the progress to.
        text: str or None
            Text to display in the progressBar, if None, the Default is used.
        """

        if self.__progressbar is None:
            return

        #WATCHME: `numbers.Number` is an abstract base class that define operations progressively, the first call to
        # this method will define it for the first time, this is why the profiler can detect some more calls for the
        # first call of the first process to be run. --> We talk about insignifiant time but the displayed data will
        # be a bit different.  see: https://docs.python.org/2/library/numbers.html
        assert isinstance(value, numbers.Number), 'Argument `value` is not numeric'
        
        self.__progressbar.setValue(float(value))
        
        if text and text != self.__progressbar.text():
            self.__progressbar.setFormat(AtConstants.PROGRESSBAR_FORMAT.format(text))

    def reset(self):
        self._resetThreads()
        self._clearFeedback()

    def _resetThreads(self):
        for thread in self.__threads.values():
            thread.reset()

    def _clearFeedback(self):
        """Clear all feedback for this process"""
        self.__feedbacks.clear()

    def getFeedbacks(self):
        return self.__feedbacks

    def getFeedback(self, thread):
        return self.__feedbacks.get(thread, None)

    def addFeedback(self, thread, toDisplay, toSelect, selectMethod=None):
        feedback = self.getFeedback(thread)
        if feedback is None:
            self.setFeedback(thread, (toDisplay,), (toSelect,), selectMethod=selectMethod)
            return

        feedback.append(toDisplay, toSelect)

    def setFeedback(self, thread, toDisplay, toSelect, selectMethod=None):
        self.__feedbacks[thread] = Feedback(thread, toDisplay, toSelect, selectMethod=selectMethod)

    def addTrace(self, trace):
        raise NotImplementedError

    def breakpoint(self):
        raise NotImplementedError


class ProcessStackTrace(object):

    def __init__(self):
        pass


# Automatic Decorator
def automatic(cls):
    """ Utility decorator to automate a process behavior.

    It allow to reset the process attributes (toCheck, toFix, data), clear the feedback etc...
    This decorator is meant to take care of redondant manipulation within a process but to keep all
    control on the code behaviour you should better manage your data by yourself.

    Parameters
    ----------
    cls: ClassType
        A class object to Wrap and make automatic.
    """    

    # Get overriden methods from the class to decorate, it's needed to redefinned the methods.
    overriddenMethods = AtUtils.getOverridedMethods(cls, Process)

    check_ = overriddenMethods.get(AtConstants.CHECK, None)
    if check_ is not None:
        def check(self, *args, **kwargs):

            self.reset()

            self.toCheck = type(self.toCheck)()
            self.toFix = type(self.toFix)()

            result = check_(self, *args, **kwargs)

            self.isChecked = True

            return result

        setattr(cls, AtConstants.CHECK, check)  # Replace the check method in the process

    fix_ = overriddenMethods.get(AtConstants.FIX, None)
    if fix_ is not None:
        def fix(self, *args, **kwargs):

            result = fix_(self, *args, **kwargs)

            self.isChecked = False

            return result

        setattr(cls, AtConstants.FIX, fix)  # Replace the fix method in the process

    tool_ = overriddenMethods.get(AtConstants.TOOL, None)
    if tool_ is not None:
        def tool(self, *args, **kwargs):

            result = tool_(self, *args, **kwargs)

            return result

        setattr(cls, AtConstants.TOOL, tool)  # Replace the tool method in the process

    return cls


#TODO: Think about an implementation of a data feature (Share data between checks.)
class Data(object):

    def __init__(self):
        pass


#TODO: Should allow to load data not only from the env files but also `.json`, `.yaml`, shotgun etc...
class Register(object):
    """Register class that contain and manage all blueprints for all available environments.

    At initialization the register will get all data it found and store them. It will also give easy accessible data
    to work with like contexts and software.
    """

    def __init__(self):
        """Get the software and setup data.

        Parameters
        -----------
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """
        
        self._software = AtUtils.getSoftware()
        self.__blueprints = []

        self.modulesForReload = []

    def __repr__(self):
        """Return the representation of the Register"""

        return "<{0} {1}>".format(
            self.__class__.__name__,
            self._software.capitalize(),
        )

    def __bool__(self):
        return bool(self._blueprint)

    __nonzero__ = __bool__

    def __eq__(self, other):
        """Allow to use '==' for logical comparison.

        This will first check if the compared object is also a Register, then it will compare all the internal data
        except the blueprints instances.

        Parameters
        ----------
        other: object
            Object to compare to this instance, should be another Register

        Notes
        -----
        Will compare:
            - software
            - contexts
        """

        if not isinstance(other, Register):
            return False

        return all((
            self._software == other._software,
            self._contexts == other._contexts,
        ))

    #FIXME: The import system is not easy to use, find a better way to use them.
    #TODO: Find a way to implement this feature and clean the import process.
    # def loadBlueprintFromPythonStr(self, pythonCode, moduleName):
    #     module = AtUtils.moduleFromStr(pythonCode, name=moduleName)
    #     self.loadBlueprintFromModule(Blueprint(module))

    def loadBlueprintsFromPackageStr(self, package):
        self.loadBlueprintsFromPackage(AtUtils.importFromStr('{package}.blueprints'.format(package=package)))

    def loadBlueprintsFromPackage(self, package):
        for modulePath in AtUtils.iterBlueprintsPath(package):
            self.loadBlueprintFromModulePath(modulePath)

    def loadBlueprintFromModuleStr(self, moduleStr):
        self.loadBlueprintFromModule(AtUtils.importFromStr(moduleStr))

    def loadBlueprintFromModulePath(self, modulePath):
        module = AtUtils.importFromStr(AtUtils.pythonImportPathFromPath(modulePath))
        self.loadBlueprintFromModule(module)

    def loadBlueprintFromModule(self, module):
        self.__blueprints.append(Blueprint(module))

    def clear(self):
        del self.__blueprints[:]

    @property
    def software(self):
        """Get the Register software"""
        return self._software

    @property
    def blueprints(self):
        """Get all Register contexts"""
        return tuple(self.__blueprints)

    def blueprintByName(self, name):
        for blueprint in self._blueprints:
            if blueprint._name == name:
                return blueprint

    def reload(self):
        blueprints = self.__blueprints[:]
        self.clear()

        for blueprint in blueprints:
            for processor in blueprint.processors:
                AtUtils.reloadModule(processor.module)
            self.loadBlueprintFromModule(AtUtils.reloadModule(blueprint._module))


class Importer(object):

    def __init__(self):
        pass


class Blueprint(object):

    def __init__(self, module):
        super(Blueprint, self).__init__()

        self._module = module

        self._name = os.path.splitext(os.path.basename(module.__file__))[0] or module.__name__

        self._data = {}

    def __bool__(self):
        return bool(self.processors)

    __nonzero__ = __bool__

    @property
    def name(self):
        return self._name

    @property
    def module(self):
        return self._module

    @AtUtils.lazyProperty
    def file(self):
        return os.path.dirname(self._module.__file__)

    @AtUtils.lazyProperty    
    def icon(self):
        return os.path.join(self.file, '{0}.png'.format(self._name))

    @AtUtils.lazyProperty  #FIXME: Due to the lazy property the old way to reload in runtime is no more available.
    def processors(self):

        # Load the env module from the string path stored.
        envModule = self._module
        if envModule is None:   #TODO: Need feedback, can't import module.
            return {}

        # Try to access the `blueprints` variable in the env module
        header = getattr(envModule, 'header', ())
        descriptions = getattr(envModule, 'register', {})
        ID.flush()  #TODO: Remove this crap

        # Generate a blueprint object for each process retrieved in the `blueprint` variable of the env module.
        processorObjects = [Processor(**descriptions[id_]) for id_ in header]
        
        # Default resolve for descriptions if available in batch, call the `resolveLinks` method from descriptions to change the targets functions.
        batchLinkResolveBlueprints = [processorObject if processorObject.inBatch else None for processorObject in processorObjects]
        for blueprint in processorObjects:
            blueprint.resolveLinks(batchLinkResolveBlueprints, check=Link.CHECK, fix=Link.FIX, tool=Link.TOOL)

        return processorObjects

    def processorByName(self, name):
        for processor in self.processors:
            if processor.name == name:
                return processor

    def setData(self, key, data):
        self._data[key] = data


class Processor(object):
    """This object will manage a single process instance to be used through an ui.

    The blueprint will init all informations it need to wrap a process like the methods that have been overrided, 
    if it can run a check, a fix, if it has a ui, its name, docstring and a lot more.
    """

    def __init__(self, process, category=None, arguments=None, tags=None, links=None, statusOverrides=None, settings=None, **kwargs):
        """Get the software and setup data.

        Parameters
        -----------
        blueprint: dict
            Dict containing the process string and the object (optional).
        """

        self._processStrPath = process
        self._category = category or AtConstants.DEFAULT_CATEGORY
        self._arguments = arguments
        self._tags = tags
        self._links = links
        self._statusOverrides = statusOverrides
        self._settings = settings

        self.__linksData = {AtConstants.CHECK: [], AtConstants.FIX: [], AtConstants.TOOL: []}

        self.__isEnabled = True

        self.__isCheckable = False
        self.__isFixable = False
        self.__hasTool = False

        self.__isNonBlocking = False

        self.__inUi = True
        self.__inBatch = True

        # -- Declare a blueprint internal data, these data are directly retrieved from blueprint's non built-in keys.
        self._data = dict(**kwargs)
        self._processProfile = _ProcessProfile()

        # -- We setup the tags because this process is really fast and does not require to be lazy.
        # This also give access to more data without the need to build the process instance.
        self.setupTags()

    def __repr__(self):
        """Return the representation of the object."""
        return '<{0} `{1}` at {2}>'.format(self.__class__.__name__, self._processStrPath.rpartition('.')[2], hex(id(self)))

    @AtUtils.lazyProperty
    def module(self):
        return AtUtils.importProcessModuleFromPath(self._processStrPath)

    @AtUtils.lazyProperty
    def process(self):
        initArgs, initKwargs = self.getArguments('__init__')
        process = getattr(self.module, self._processStrPath.rpartition('.')[2])(*initArgs, **initKwargs)

        # We do the overrides only once, they require the process instance.
        self._overrideLevels(process, self._statusOverrides)
        return process

    @AtUtils.lazyProperty
    def overridedMethods(self):
        return AtUtils.getOverridedMethods(self.process.__class__, Process)

    @AtUtils.lazyProperty
    def isCheckable(self):
        """Get the Blueprint's checkable state"""
        return bool(self.overridedMethods.get(AtConstants.CHECK, self.__isCheckable))

    @AtUtils.lazyProperty
    def isFixable(self):
        """Get the Blueprint's fixable state"""
        return bool(self.overridedMethods.get(AtConstants.FIX, self.__isFixable))

    @AtUtils.lazyProperty
    def hasTool(self):
        """Get if the Blueprint's have a tool"""
        return bool(self.overridedMethods.get(AtConstants.TOOL, self.__hasTool))

    @AtUtils.lazyProperty
    def niceName(self):
        """Get the Blueprint's name"""
        return AtUtils.camelCaseSplit(self.process._name_)

    @AtUtils.lazyProperty
    def docstring(self):
        """Get the Blueprint's name"""
        return self._createDocstring()

    @property
    def name(self):
        return self.process._name_

    @property
    def isEnabled(self):
        """Get the Blueprint's enabled state"""
        return self.__isEnabled

    @property
    def inUi(self):
        """Get if the Blueprint should be run in ui"""
        return self.__inUi
    
    @property
    def inBatch(self):
        """Get if the Blueprint should be run in batch"""
        return self.__inBatch

    @property
    def isNonBlocking(self):
        """Get the Blueprint's non blocking state"""
        return self.__isNonBlocking

    @property
    def category(self):
        """Get the Blueprint's non blocking state"""
        return self._category

    def getParameter(parameter, default=None):
        return self._settings.get(parameter, default)

    def getLowestFailStatus(self):
        return next(iter(sorted((thread._failStatus for thread in self._threads.values()), key=lambda x: x._priority)), None)

    def getLowestSuccessStatus(self):
        return next(iter(sorted((thread._successStatus for thread in self._threads.values()), key=lambda x: x._priority)), None)
        
    def check(self, links=True, doProfiling=False):
        """This is a wrapper for the process check that will automatically execute it with the right parameters.

        Parameters
        ----------
        links: bool
            Should the wrapper launch the connected links or not.

        Returns
        -------
        type
            The check feedback.
        bool
            True if the check have any feedback, False otherwise.
        """

        if not self.isCheckable:
            return None, None
        
        args, kwargs = self.getArguments(AtConstants.CHECK)

        if doProfiling:
            returnValue = self._processProfile.profileMethod(self.process.check, *args, **kwargs)
        else:
            returnValue = self.process.check(*args, **kwargs)  #TODO: Not used !!

        if links:
            self.runLinks(AtConstants.CHECK)
        
        return self._filterFeedbacks()

    def fix(self, links=True, doProfiling=False):
        """This is a wrapper for the process fix that will automatically execute it with the right parameters.
        
        Parameters
        ----------
        links: bool
            Should the wrapper launch the connected links or not.

        Returns
        -------
        type
            The value returned by the fix.
        """

        if not self.isFixable:
            return None, None

        args, kwargs = self.getArguments(AtConstants.FIX)

        if doProfiling:
            returnValue = self._processProfile.profileMethod(self.process.fix, *args, **kwargs)
        else:
            returnValue = self.process.fix(*args, **kwargs)

        if links:
            self.runLinks(AtConstants.FIX)
        
        return self._filterFeedbacks()

    def tool(self, links=True, doProfiling=False):
        """This is a wrapper for the process tool that will automatically execute it with the right parameters.

        Parameters
        ----------
        links: bool
            Should the wrapper launch the connected links or not.

        Returns
        -------
        type
            The value returned by the tool method.
        """

        if not self.hasTool:
            return None

        args, kwargs = self.getArguments(AtConstants.TOOL)

        if doProfiling:
            returnValue = self._processProfile.profileMethod(self.process.tool, *args, **kwargs)
        else:
            returnValue = self.process.tool(*args, **kwargs)

        if links:
            self.runLinks(AtConstants.TOOL)

        return returnValue

    def runLinks(self, which):

        links = self.__linksData[which]

        for link in links:
            link()

    def getArguments(self, method):
        """Retrieve arguments for the given method of the process.
        
        Parameters
        ----------
        method: classmethod
            The method for which retrieve the arguments and keyword arguments.

        Notes
        -----
        This method will not raise any error, if no argument is found, return a tuple containing empty
        list and empty dict.

        Returns
        -------
        tuple
            Tuple containing a list of args and a dict of kwargs
            => tuple(list, dict)
        """

        arguments = self._arguments
        if arguments is None:
            return ([], {})

        arguments = arguments.get(method, None)
        if arguments is None:
            return ([], {})

        return arguments

    def setupTags(self):
        """Setup the tags used by this process

        This method will setup the tags from the Tags given in the env module to affect the process behaviour.
        """

        tags = self._tags

        if tags is None:
            return

        if tags & Tag.DISABLED:
            self._isEnabled = False

        if tags & Tag.NO_CHECK:
            self.__isCheckable = False

        if tags & Tag.NO_FIX:
            self.__isFixable = False

        if tags & Tag.NO_TOOL:
            self.__hasTool = False

        if tags & Tag.NON_BLOCKING:
            self.__isNonBlocking = True

        if tags & Tag.NO_BATCH:
            self.__inBatch = False

        if tags & Tag.NO_UI:
            self.__inUi = False

    def resolveLinks(self, linkedObjects, check=AtConstants.CHECK, fix=AtConstants.FIX, tool=AtConstants.TOOL):
        """Resolve the links between the given objects and the current Blueprint's Process.

        This need to be called with an ordered list of Objects (Blueprint or custom object) with None for blueprints to skip.
        (e.g. to skip those that should not be linked because they dont have to be run in batch or ui.)

        Parameters
        ----------
        linkedObjects: list(object, ...)
            List of all objects used to resolve the current Blueprint links. Objects to skip have to be replace with `None`.
        check: str
            Name of the method to use as check link on the given objects.
        fix: str
            Name of the method to use as fix link on the given objects.
        tool: str
            Name of the method to use as tool link on the given objects.
        """

        self.__linksData = linksData = {AtConstants.CHECK: [], AtConstants.FIX: [], AtConstants.TOOL: []}

        if not linkedObjects:
            return

        links = self._links
        if links is None:
            return

        for link in links:
            index, _driver, _driven = link
            if linkedObjects[index] is None:
                continue

            driven = _driven
            driven = check if _driven == Link.CHECK else driven
            driven = fix if _driven == Link.FIX else driven
            driven = tool if _driven == Link.TOOL else driven

            linksDatas[_driver].append(getattr(linkedObjects[index], driven))

    def _overrideLevels(self, process, overrides):
        """Override the arguments level of the Process Blueprint from the data in the env module."""

        if not overrides:
            return

        for threadName, overridesDict in overrides.items():
            if not hasattr(process, threadName):
                raise RuntimeError('Process {0} have not thread named {1}.'.format(process._name_, threadName))
            thread = getattr(process, threadName)
            
            # Get the fail overrides for the current name
            status = overridesDict.get(Status.FailStatus, None)
            if status is not None:
                if not isinstance(status, Status.FailStatus):
                    raise RuntimeError('Fail feedback status override for {0} "{1}" must be an instance or subclass of {2}'.format(
                        process._name_,
                        threadName,
                        Status.FailStatus
                    ))
                thread._failStatus = status
            
            # Get the success overrides for the current name
            status = overridesDict.get(Status.SuccessStatus, None)
            if status is not None:
                if not isinstance(status, Status.SuccessStatus):
                    raise RuntimeError('Success feedback status override for {0} "{1}" must be an instance or subclass of {2}'.format(
                        process._name_,
                        threadName,
                        Status.SuccessStatus
                    ))
                thread._successStatus = status

    def setProgressbar(self, progressbar):
        """ Called in the ui this method allow to give access to the progress bar for the user

        Parameters
        ----------
        progressbar: QtWidgets.QProgressBar
            QProgressBar object to connect to the process to display check and fix progression.
        """

        self.process.setProgressbar(progressbar)

    def _createDocstring(self):
        """Generate the Blueprint doc from Process docstring and data in the `_docFormat_` variable.

        Returns
        -------
        str
            Return the formatted docstring to be more readable and also display the path of the process.
        """

        docstring = self.process._doc_ or AtConstants.NO_DOCUMENTATION_AVAILABLE
        docstring += '\n {0} '.format(self._processStrPath)

        docFormat = {}
        for match in re.finditer(r'\{(\w+)\}', docstring):
            matchStr = match.group(1)
            docFormat[matchStr] = self.process._docFormat_.get(matchStr, '')

        return docstring.format(**docFormat)

    def getData(self, key, default=None):
        return self._data.get(key, default)

    def setData(self, key, value):
        self._data[key] = value

    def _filterFeedbacks(self):
        """ Filter the data outputed by a process to keep only these that is not empty.

        Parameters
        ----------
        result: tuple
            Tuple containing tuple with a str for title and list of errors.
            > tuple(tuple(str, list, `list`, `str`), ...)

        Returns
        -------
        list
            List of feedbacks that contain at least one error to log or only a title. 
        """

        # We always consider that the result should be the lowest success status.
        globalStatus = Status._DEFAULT

        feedbackContainer = []
        for processThreadName, processThread in self.process.threads.items():

            # Get the feedaback, if there is no feedback for this thread it is clean.
            feedback = self.process.getFeedback(processThread)
            if feedback:
                feedbackContainer.append(feedback)

            # If there is anything in the feedback we check if we need to increase the fail status and we add the feedback in
            # the container to return it.
            # if thread._state is Status.FailStatus:
            if processThread._status._priority > globalStatus._priority:
                globalStatus = processThread._status

            # If the feedback is empty this thread was succesfull, we increase success status if the status of this thread is
            # higher to the current one retrieved.
            # elif thread._state is Status.SuccessStatus:
            #     print thread._status._name, thread._status._priority, globalSuccessStatus._priority
            #     if thread._status._priority > globalSuccessStatus._priority:
            #         globalSuccessStatus = thread._status

        return feedbackContainer, globalStatus # if feedbackContainer else globalSuccessStatus


class Tag(object):
    """Tags are modifiers used by Athena to affect the way a process could be run, through or outside a ui.
    It Allow processes to be optional, non blocking, hide their checks and more.

    Attributes
    ----------
    DISABLED: str
        Define if a process should be disabled (by default it is enable)
    NO_CHECK: str
        This tag will remove the check of a process, it will force the isCheckable to False in blueprint.
    NO_FIX: str
        This tag will remove the fix of a process, it will force the isFixable to False in blueprint.
    NO_TOOL: str
        This tag will remove the tool of a process, it will force the hasTool to False in blueprint.
    NON_BLOCKING: str
        A non blocking process will raise a non blocking error, its error is ignored.
    NO_BATCH: str
        This process will only be executed in ui.
    NO_UI: str
        This process will only be executed in batch.
    OPTIONAL: str
       This tag will set a check optional, an optional process is not checked by default and will.
    DEPENDANT: str
        A dependent process need links to be run through another process.
    """

    NO_TAG          = 0

    DISABLED        = 1

    NO_CHECK        = 2
    NO_FIX          = 4
    NO_TOOL         = 8

    NON_BLOCKING    = 16
    
    NO_BATCH        = 32
    NO_UI           = 64
    
    OPTIONAL        = NON_BLOCKING | DISABLED
    DEPENDANT       = NO_CHECK | NO_FIX | NO_TOOL


class Link(enum.Enum):
    """Give access to the AtConstants to simplify the use of the links."""

    CHECK = AtConstants.CHECK
    FIX = AtConstants.FIX
    TOOL = AtConstants.TOOL


class MetaID(type):
        
    def __getattr__(cls, value):
        # id_ = hex(hash(value))

        if value not in cls._DATA:
            setattr(cls, value, value)
            cls._DATA.add(value)

        return value

    def __getattribute__(cls, value):
        
        if value in type.__dict__:
            raise ValueError('Can not create ID: `{0}`, it will override python <type> inherited attribute of same name.'.format(value))

        return type.__getattribute__(cls, value)

#TODO: six is used to ensure compatibility between python 2.x and 3.x, replace by `object, metaclass=MetaID`
class ID(six.with_metaclass(MetaID, object)):
    
    _DATA = set()

    def __new__(cls):
        raise NotImplementedError('{0} is not meant to be instanciated.'.format(cls))

    @classmethod
    def flush(cls):
        cls._DATA.clear()


class Status(object):
    """The Status define the level of priority of a Thread Feedback as well as the state of a process.

    The process must be given an original name and a level of priority, the priority must be <0 for a fail status and 
    >0 for a success status. Other type does not use the priority.
    The color is an rgb value that will then allow to set the color in an interface.
    
    .. notes::
        The Status object can't be instanciated, instead, the __Status object will be instantiated and returned.
        The Status class already create some instances of the __Status class to define the bases Status to be Used by 
        default.
    """

    class __Status(object):
        
        _ALL_STATUS = {}

        def __new__(cls, *args, **kwargs):
            """Allow to store all new levels in the __ALL_LEVELS class variable to return singleton."""
            instance = super(cls.__class__, cls).__new__(cls)
            cls._ALL_STATUS.setdefault(instance.__class__, set()).add(instance)

            return instance
        
        def __init__(self, name, color, priority=0.0):

            self._name = name
            self._priority = priority
            self._color = color

    class FailStatus(__Status):
        
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

    class SuccessStatus(__Status):
        
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

    class FeedbackStatus(__Status):
        
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs) 

    class BuiltInStatus(__Status):
        
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

    _DEFAULT =  BuiltInStatus('Default', (60, 60, 60))

    # INFO =  FeedbackStatus('Info', (200, 200, 200))
    # PAUSED = FeedbackStatus('Paused', (255, 186, 0))

    CORRECT = SuccessStatus('Correct', (22, 194, 15), 0.1)
    SUCCESS = SuccessStatus('Success', (0, 128, 0), 0.2)

    WARNING = FailStatus('Warning', (196, 98, 16), 1.1)
    ERROR = FailStatus('Error', (102, 0, 0), 1.2)
    CRITICAL = FailStatus('Critical', (150, 0, 0), 1.3)

    _EXCEPTION = BuiltInStatus('Exception', (110, 110, 110))

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('Can\'t create new instance of type `{0}`.'.format(cls.__name__))

    @classmethod
    def getAllStatus(cls):
        return [status for statusTypeList in cls.__Status._ALL_STATUS.values() for status in statusTypeList]

    @classmethod
    def getStatusByName(cls, name):
        for status in cls.getAllStatus():
            if status._name == name:
                return status
        else:
            return None

    @classmethod
    def getAllFailStatus(cls):
        return cls.__Status._ALL_STATUS[cls.FailStatus]

    @classmethod
    def getAllSuccessStatus(cls):
        return cls.__Status._ALL_STATUS[cls.SuccessStatus]

    @classmethod
    def lowestFailStatus(cls):
        return sorted(cls.getAllFailStatus(), key=lambda x: x._priority)[0]

    @classmethod
    def highestFailStatus(cls):
        return sorted(cls.getAllFailStatus(), key=lambda x: x._priority)[-1]

    @classmethod
    def lowestSuccessStatus(cls):
        return sorted(cls.getAllSuccessStatus(), key=lambda x: x._priority)[0]

    @classmethod
    def highestSuccessStatus(cls):
        return sorted(cls.getAllSuccessStatus(), key=lambda x: x._priority)[-1]


class Feedback(object):
    """This onbject contain all the data to describe one feedback that have. been checked in a Process."""

    def __init__(self, thread, toDisplay, toSelect, selectMethod=None, help=None):
        
        if len(toDisplay) != len(toSelect):
            raise ValueError('You must have the same amount of object to select and to display')

        self._thread = thread

        self._toDisplay = list(toDisplay)
        self._toSelect = list(toSelect) or self._toDisplay

        self._selectMethod = selectMethod or AtUtils.softwareSelection

    def selectAll(self):
        self._selectMethod(self._toSelect)

    def select(self, indexes):
        self._selectMethod([self._toSelect[i] for i in indexes])

    def hasFeedback(self):
        return bool(self._toDisplay)

    def append(self, toDisplay, toSelect, selectMethod=None):
        self._toDisplay.append(toDisplay)
        self._toSelect.append(toSelect)

        if selectMethod is not None and self._selectMethod is not AtUtils.softwareSelection:
            self._selectMethod = selectMethod

    def iterItems(self):
        for item in list(zip(self._toDisplay, self._toSelect)):
            yield item

    def __bool__(self):
        return bool(self._toSelect)

    __nonzero__ = __bool__


class Thread(object):

    def __init__(self, title, failStatus=Status.ERROR, successStatus=Status.SUCCESS, documentation=None):
        if not isinstance(failStatus, Status.FailStatus):
            raise AtExceptions.StatusException('`{}` is not a valid fail status.'.format(failStatus._name))
        if not isinstance(successStatus, Status.SuccessStatus):
            raise AtExceptions.StatusException('`{}` is not a valid success status.'.format(successStatus._name))

        self._title = title

        self._defaultFailStatus = failStatus
        self._failStatus = failStatus

        self._defaultSuccessStatus = successStatus
        self._successStatus = successStatus

        self._documentation = documentation

    @property
    def failStatus(self):
        return self._failStatus

    @property
    def successStatus(self):
        return self._successStatus


class ProcessThread(Thread):

    def __init__(self, thread):

        super(ProcessThread, self).__init__(
            title=thread._title, 
            failStatus=thread._defaultFailStatus,
            successStatus=thread._defaultSuccessStatus,
            documentation=thread._documentation
        )

        self._thread = thread
        self._enabled = True

        self._state = Status.SuccessStatus
        self._status = self._successStatus

    @property
    def thread(self):
        return self._thread
    
    @property
    def state(self):
        return self._state

    def reset(self):
        self._state = Status.SuccessStatus
        self._status = self._successStatus

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def setFail(self, overrideStatus=None):
        if overrideStatus is not None:
            if isinstance(overrideStatus, Status.FailStatus):
                self._status = overrideStatus
            else:
                raise TypeError('Fail Status can only be an instance or subtype of `{}`.'.format(type(Status.FailStatus)))
        else:
            self._status = self._failStatus

        self._state = Status.FailStatus

    def setSuccess(self, overrideStatus=None):
        if overrideStatus is not None:
            if isinstance(overrideStatus, Status.SuccessStatus):
                self._status = overrideStatus
            else:
                raise TypeError('Success Status can only be an instance or subtype of `{}`.'.format(type(Status.SuccessStatus)))
        else:
            self._status = self._successStatus

        self._state = Status.SuccessStatus


class Event(object):

    def __init__(self):
        self.callbacks = []

    def __call__(self):
        for callback in self.callbacks:
            callback()

    def register(self, callback):
        if not callable(callback):
            AtUtils.LOGGER.warning(
                'Event "{0}" failed to register callback: Object "{1}" is not callable.'.format(self.name, callback)
            )
            return False

        self.callbacks.append(callback)
        return True

    def unregister(self, callback):
        pass


class Callback(object):
    """ Warps a callable object to preserve its arguments and keyword arguments
    """

    def __init__(self, callableObject, *args, **kwargs):
        self.callable = callableObject
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.callable(*self.args, **self.kwargs)

class EventSystem(object):

    RegisterCreated = Event()

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('Can\'t create new instance of type `{0}`.'.format(cls.__name__))

    @classmethod
    def addEventCallback(cls, eventName, callbackFunction, *args, **kwargs):
        assert callable(callbackFunction), '`callbackFunction` must be passed a callable argument.'

        if not hasattr(cls, eventName):
            raise KeyError('Event `{0}` does not exists.'.format(eventName))

        callback = Callback(callbackFunction, *args, **kwargs)
        getattr(cls, eventName).register(callback)

        return callback


class _ProcessProfile(object):

    # Match integers, floats (comma or dot) and slash in case there is a separation for primitive calls.
    DIGIT_PATTERN = r'([0-9,.\/]+)'
    DIGIT_REGEX = re.compile(DIGIT_PATTERN)

    CATEGORIES = ('ncalls', 'tottime', 'percall', 'cumtime', 'percall', 'filename:lineno(function)')

    def __init__(self):
        self._profiles = {} 

    def get(self, key, default=None):
        return self._profiles.get(key, default)

    def _getCallDataList(self, callData):
        dataList = []
        for call in callData:
            callData = []

            filteredData = filter(lambda x: x, call.strip().split(' '))
            if not filteredData:
                continue
            callData.extend(filteredData[0:5])
            callData.append(' '.join(filteredData[5:len(filteredData)]))

            dataList.append(tuple(callData))

        return dataList

    def profileMethod(self, method, *args, **kwargs):
        assert callable(method), '`method` must be passed a callable argument.'

        profile = cProfile.Profile()

        # Run the method with `cProfile.Profile.runcall` to profile it's execution only. We define exception before
        # executing it, if an exception occur the except statement will be processed and `exception` will be updated
        # from `None` to the exception that should be raised.
        # At the end of this method exception must be raised in case it should be catch at upper leve in the code.
        # This allow to not skip the profiling even if an exception occurred. Of course the profiling will not be complete
        # But there should be all information from the beginning of the method to the exception. May be usefull for debugging.
        exception = None
        try:
            returnValue = profile.runcall(method, *args, **kwargs)
        except Exception as exception:
            pass

        # Create a temp file and use it as a stream for the `pstats.Stats` This will allow us to open the file
        # and retrieve the stats as a string. With regex it's now possible to retrieve all the data in a displayable format
        # for any user interface.
        fd, tmpFile = tempfile.mkstemp()
        try:
            with open(tmpFile, 'w') as statStream:
                stats = pstats.Stats(profile, stream=statStream)
                stats.sort_stats('cumulative')  # cumulative will use the `cumtime` to order stats, seems the most relevant.
                stats.print_stats()
            
            with open(tmpFile, 'r') as statStream:
                statsStr = statStream.read()

        except Exception as exception:
            # If an error occur it will not be silent, but the temp file will be removed anyway.
            raise exception
        finally:
            # No matter what happen, we want to delete the file.
            # It happen that the file is not closed here on Windows so we also call `os.close` to ensure it is really closed.
            # WindowsError: [Error 32] The process cannot access the file because it is being used by another process: ...
            os.close(fd)
            os.remove(tmpFile)

        split = statsStr.split('\n')
        methodProfile = {
            'time': time.time(),  # With this we will be able to not re-generate widget (for instance) if data have not been updated.
            'calls': self._getCallDataList(split[5:-1]),
            'rawStats': statsStr,
        }

        # Take care of possible primitive calls in the summary for `ncalls`.
        summary = self.DIGIT_REGEX.findall(split[0])
        methodProfile['tottime'] = summary[-1]
        if len(summary) == 3:
            methodProfile['ncalls'] = '{0}/{1}'.format(summary[0], summary[1])
        else:
            methodProfile['ncalls'] = summary[0]

        self._profiles[method.__name__] = methodProfile

        if exception is not None:
            raise exception

        return returnValue

        

# Setup
'''
import sys
sys.path.append('C:\Python27\Lib\site-packages')
sys.path.append('C:\Workspace\Athena\src')

import Athena.ressources.Athena_example.ContextExample

import Athena
Athena._reload(__name__)

Athena.launch(dev=True)
'''
