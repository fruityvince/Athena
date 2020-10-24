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


class Process(object):
    """Abstract class from which any Athena Processes must inherit.

    The Process object define default instance attributes for user to use and that are managed through the `automatic`
    decorator.
    When implementing a new Process you must defined at least one `Thread` object as a class attribute. When the Process
    will be instanciated the class Threads will be replaced with `_ProcessThreads` instances by the `Process` class constructor.
    You must use these Threads to manage the differents error the Process will have to check and maybe fix.
    It comes with methods to manage the internal feedback and the potentially connected QProgressbar.
    There is 3 non implemented methods that can or must be overrided to make a working Process.
        - `check`: This method is the only method that require to be overrided, it must allow to retrieve errors and
            set the success status of the process threads.
        - `fix`: Override this method to implement a way to automaticaly fix thread's errors found by the `check`.
        - `tool`: Allow to define a tool to allow a "semi-manual" fix by user.
    Also you can use the `setProgressValue` method to give feedback to the user on the current state of the check or fix
    progress, you can also give a str value to display on the progressbar. A progressBar must be linked for this feature to work.

    Some sunder attributes are also defined at the class level and allow to define some data to replace the class default one.
    For instance, defining `_name_` will give a name to the Process, different of the class name from `__name__`. This allow to define
    a nice name for users. There is the currently available sunder attributes:
        - `_name_`
        - `_doc_`

    You may want to create a custom base class for all your Process, if so, this base class must also inherit from `Process` to be
    recognized by the Athena's API. You should not override the `__new__` method without using super or the Process will not be
    setuped as it should.
    """

    __NON_OVERRIDABLE_ATTRIBUTES = \
    {
        '_resetThreads',
        'DATA',
        'reset',
        'setProgressValue',
        'addTrace',
        'breakpoint',
    }

    _name_ = ''
    _doc_ = ''


    def __new__(cls, *args, **kwargs):
        """Generate a new class instance and setup its default attributes.
        
        The base class `Process` can't be instanciated because it is an abstract class made to be inherited
        and overrided by User Processes.
        `__new__` will simply create you instance and retrieve all the `Thread` to replace them with `_ProcessThread`,
        all theses `_ProcessThread` instances will then be stored in a private instance attribute. They will be accesible
        with a property `threads`.
        The sunder method will be set to the class data `instance._name_ = cls._name_ or cls.__name__`, this allow to use
        the class raw data if no nice values was set.
        """

        # Check if class to instanciate is Process. If True, raise an error because class is abstract.
        if cls is Process:
            raise NotImplementedError('Can not instantiate abstract class')

        # Create the instance
        instance = super(Process, cls).__new__(cls, *args, **kwargs)

        # Instance internal data (Must not be altered by user)
        instance.__threads = {}
        for memberName, member in inspect.getmembers(cls):
            if isinstance(member, Thread):
                processThread = _ProcessThread(member)
                instance.__threads[memberName] = processThread
                instance.__dict__[memberName] = processThread

        instance.__progressbar = None

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
        """Give a nice representation of the Process with it's nice name."""
        return '<Process `{0}` at {1}>'.format(self._name_, hex(id(self)))

    @property
    def threads(self):
        """Property to access the process instance threads."""
        return self.__threads
    
    def check(self, *args, **kwargs):
        """This method must be implemented on all Process and must retrieve error to set Threads status and feedback."""
        raise NotImplementedError
        
    def fix(self, *args, **kwargs):
        """This method can be implemented to allow an automatic fix of the errors retrieved by the Process check."""
        raise NotImplementedError

    def tool(self, *args, **kwargs):
        """This method can be implemented to open a window that can allow the user to manually find or fix the errors."""
        raise NotImplementedError

    def setProgressbar(self, progressBar):
        """This method should be used to setup the Process progress bar

        Parameters
        ----------
        progressBar: QtWidgets.QProgressBar
            The new progress bar to link to The Process instance.
        """

        self.__progressbar = progressBar

    def setProgressValue(self, value, text=None):
        """Set the progress value of the Process progress bar if exist.
        
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
        """Reset all the Process internal data
        
        Will run all reset protected methods from Process base class.
        """

        self._resetThreads()

    def _resetThreads(self):
        """Iter through all Thread to reset them."""

        for thread in self.__threads.values():
            thread.reset()

    def addTrace(self, trace):
        raise NotImplementedError

    def breakpoint(self):
        raise NotImplementedError


# Automatic Decorator
def automatic(cls):
    """Utility decorator to automate a process behavior.

    It allow to reset the process attributes (toCheck, toFix, data), clear the feedback etc...
    This decorator is meant to take care of redondant manipulation within a process but to keep all
    control on the code behaviour you should better manage your data by yourself.
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


class Register(object):
    """The register is a container that allow the user to load and manager blueprints.

    After initialisation the register will not contain any data and you will need to manually load the data using the
    pyton import path of module path to load blueprints.
    It can be reloaded to simplify devellopment and magic methods like `__eq__` or `__bool__` are implemented.
    """

    def __init__(self):
        """Get the software and setup Register's blueprints list."""
        
        self._software = AtUtils.getSoftware()
        self.__blueprints = []

    def __repr__(self):
        """Return the representation of the Register"""

        return "<{0} {1}>".format(
            self.__class__.__name__,
            self._software.capitalize(),
        )

    def __bool__(self):
        """Allow to check if the register is empty or not based on the loaded blueprints."""
        return bool(self.__blueprint)

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
            - blueprints
        """

        if not isinstance(other, self.__class__):
            return False

        return all((
            self._software == other._software,
            self._blueprints == other._blueprints,
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
        """Remove all loaded blueprints from this register."""
        del self.__blueprints[:]

    @property
    def software(self):
        """Get the Register's software"""
        return self._software

    @property
    def blueprints(self):
        """Get all Register blueprints"""
        return tuple(self.__blueprints)

    def blueprintByName(self, name):
        """Get a blueprints based on it's name, if no blueprint match the name, `None` is returned.

        Parameters
        ----------
        name: str
            The name of the blueprint to find.

        Return:
        -------
        str:
            The blueprint that match the name, or None if no blueprint match the given name.
        """

        for blueprint in self._blueprints:
            if blueprint._name == name:
                return blueprint

    def reload(self):
        """Clear the blueprints and reload them to ensure all blueprints are up to data."""

        blueprints = self.__blueprints[:]
        self.clear()

        for blueprint in blueprints:
            for processor in blueprint.processors:
                AtUtils.reloadModule(processor.module)
            self.loadBlueprintFromModule(AtUtils.reloadModule(blueprint._module))


class Blueprint(object):
    """A blueprints refer to a python module that contain the required data to make Athena works.

    The module require at least two variables:
        - header: It contain a list of names ordered, this is the order of the checks.
        - descriptions: The description is a dict where each value in the header contain a dict of data to init a processor.
    Another variable called `settings` can also be added as a dict, these values will then allow to modify behaviour of a
    tool based on the current blueprint.

    The Blueprint is a lazy object that will load all it's data on demand to reduce the need of ressources, for example, no processors
    are created for a blueprints untils it's `processor` attribute is called.

    Notes:
        - The name of a processor is based on the name of it's module.
        - Data can be stored on a Blueprint using the `setData` method, this allow to store widgets if they are already
        created for example or any other kind of data.
    """

    def __init__(self, module):
        """Init the blueprint object by defining it's attributes"""

        self._module = module

        self._name = os.path.splitext(os.path.basename(module.__file__))[0] or module.__name__

        self._data = {}

    def __bool__(self):
        """Allow to deteremine if the blueprint contains processors or not.

        Return:
        -------
        bool:
            True if the blueprint contain at least one processor else False.
        """
        return bool(self.processors)

    __nonzero__ = __bool__

    @property
    def name(self):
        """Property to get the Blueprint's name."""

        return self._name

    @property
    def module(self):
        """Property to get the Blueprint's module"""

        return self._module

    @AtUtils.lazyProperty
    def file(self):
        """Lazy property to get the Blueprint's module file path."""

        return os.path.dirname(self._module.__file__)

    @AtUtils.lazyProperty    
    def icon(self):
        """Lazy property to get the Blueprint's icon path.

        Notes:
            - The icon must be a `.png` file in the same folder as the Blueprint's module.
        """

        return os.path.join(self.file, '{0}.png'.format(self._name))

    @AtUtils.lazyProperty
    def header(self):
        """Lazy property to get the Blueprint's header."""

        return getattr(self._module, 'header', ())

    @AtUtils.lazyProperty
    def descriptions(self):
        """Lazy property to get the Blueprint's descriptions."""

        return getattr(self._module, 'descriptions', {})

    @AtUtils.lazyProperty  #FIXME: Due to the lazy property the old way to reload in runtime is no more available.
    def processors(self):
        """Lazy property to get the Blueprint's descriptors.
        
        It will create all the processors from the Blueprint's decsriptions ordered based on the header.
        This will also automatically resolve the links for each description in case this is meant to be used in batch.
        """

        ID.flush()  #TODO: Remove this crap

        batchLinkResolve = {}
        processorObjects = []
        for id_ in self.header:
            processor = Processor(**self.descriptions[id_])

            processorObjects.append(processor)
            batchLinkResolve[id_] = processor if processor.inBatch else None
        
        # Default resolve for descriptions if available in batch, call the `resolveLinks` method from descriptions to change the targets functions.
        for blueprint in processorObjects:
            blueprint.resolveLinks(batchLinkResolve, check=AtConstants.CHECK, fix=AtConstants.FIX, tool=AtConstants.TOOL)

        return processorObjects

    def processorByName(self, name):
        """Find a processor from blueprint's processors based on it's name.
        
        Parameters:
        ----------
        name: str
            The name of the processor to find.

        Return:
        -------
        str
            The processor that match the name, or None if no processor match the given name.
        """

        for processor in self.processors:
            if processor.name == name:
                return processor

    #TODO: Maybe not used.
    def setData(self, key, data):
        """Allow to store data on the blueprint.

        Parameters:
        -----------
        key: typing.hashable
            The key used to access the data.
        data: object
            The data to save for the given key.
        """

        self._data[key] = data


class Processor(object):
    """The Processor is a wrapper for a process object, build from the description of a blueprints.

    The Processor will init all informations it need to wrap a process like the methods that have been overrided, 
    if it can run a check, a fix, if it is part of te ui/batch, its name, docstring and a lot more.
    It will also resolve some of it's data lazilly to speed up execution process.
    """

    def __init__(self, process, category=None, arguments=None, tags=None, links=None, statusOverrides=None, settings=None, **kwargs):
        """Init the Processor instances attributes and define all the default values. The tags will also be resolved.

        Parameters
        -----------
        process: str
            The python path to import the process from, it must be a full import path to the Process class.
        category: str
            The name of the category of the Processor, if no value are provided the category will be `AtConstants.DEFAULT_CATEGORY` (default: `None`)
        arguments: dict(str: tuple(tuple, dict))
            This dict must contain by method name ('__init__', 'check', ...) a tuple containing a tuple for the args and 
            a dict for the keyword arguments. (default: `None`)
        tags: int
            The tag is an integer where bytes refers to `Athena.AtCore.Tags`, it must be made of one or more tags. (default: `None`)
        links: tuple(tuple(str, Links, Links))
            The links must contain an ordered sequence of tuple with a str (ID) to another Process of the same blueprint, and two
            Links that are the source and the target methods to connect. (default: `None`)
        statusOverride: dict(str: dict(type: Status.__Status))
            Status overrides must be a dict with name of process Thread as key (str) and a dict with `Status.FailStatus` or
            `Status.SuccessStatus` as key (possibly both) and the status for the override as value. (default: `None`)
        settings: dict
            Setting is a dict that contain data as value for each setting name as key. (default: `None`)
        **kwargs:
            All remaining data passed at initialisation will automatically be used to init the Processor data.
        """

        self._processStrPath = process
        self._category = category or AtConstants.DEFAULT_CATEGORY
        self._arguments = arguments
        self._tags = tags
        self._links = links
        self._statusOverrides = statusOverrides
        self._settings = settings

        self.__linksData = {Link.CHECK: [], Link.FIX: [], Link.TOOL: []}

        self.__isEnabled = True

        self.__hasCheckMethod = bool(self.overridedMethods.get(AtConstants.CHECK, False))
        self.__hasFixMethod = bool(self.overridedMethods.get(AtConstants.FIX, False))
        self.__hasToolMethod = bool(self.overridedMethods.get(AtConstants.TOOL, False))

        self.__isCheckable = self.__hasCheckMethod
        self.__isFixable = self.__hasFixMethod
        self.__hasTool = self.__hasToolMethod

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
        """Return the representation of the Processor."""
        return '<{0} `{1}` at {2}>'.format(self.__class__.__name__, self._processStrPath.rpartition('.')[2], hex(id(self)))

    @AtUtils.lazyProperty
    def module(self):
        """Lazy property that import and hold the module object for the Processor's Process."""

        return AtUtils.importProcessModuleFromPath(self._processStrPath)

    @AtUtils.lazyProperty
    def process(self):
        """Lazy property to get the process class object of the Processor"""

        initArgs, initKwargs = self.getArguments('__init__')
        process = getattr(self.module, self._processStrPath.rpartition('.')[2])(*initArgs, **initKwargs)

        # We do the overrides only once, they require the process instance.
        self._overrideLevels(process, self._statusOverrides)
        return process

    @AtUtils.lazyProperty
    def overridedMethods(self):
        """Lazy property to get the overrided methods of the Processor's Process class."""

        return AtUtils.getOverridedMethods(self.process.__class__, Process)

    @AtUtils.lazyProperty
    def niceName(self):
        """Lazy property to get a nice name based on the Processor's Process name."""

        return AtUtils.camelCaseSplit(self.process._name_)

    @AtUtils.lazyProperty
    def docstring(self):
        """Lazy property to get the docstring of the Processor's process."""
        return self._createDocstring()

    @property
    def rawName(self):
        """Get the raw name of the Processor's Process."""
        return self.process._name_

    @property
    def isEnabled(self):
        """Get the Blueprint's enabled state."""
        return self.__isEnabled

    @property  #FIXME: Don't seems to work..
    def hasCheckMethod(self):
        """Get if the Processor's Process have a `check` method."""
        return self.__hasCheckMethod

    @property
    def hasFixMethod(self):
        """Get if the Processor's Process have a `fix` method."""
        return self.__hasFixMethod

    @property
    def hasToolMethod(self):
        """Get if the Processor's Process have a `tool` method."""
        return self.__hasToolMethod

    @property  #FIXME: Don't seems to work..
    def isCheckable(self):
        """Get the Blueprint's checkable state"""
        return self.__isCheckable

    @property
    def isFixable(self):
        """Get the Blueprint's fixable state"""
        return self.__isFixable

    @property
    def hasTool(self):
        """Get if the Blueprint's have a tool"""
        return self.__hasTool

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
        """Get the Blueprint's category"""
        return self._category

    def getSetting(setting, default=None):
        """Get the value for a specific setting if it exists, else None.

        Parameters:
        -----------
        setting: typing.hashable
            The setting to get from the Processor's settings.
        default: object
            The default value to return if the Processor does not have any value for this setting. (default: `None`)

        Return:
        -------
        object
            The value for the given setting or the default value if the given setting does not exists.
        """

        return self._settings.get(setting, default)

    def getLowestFailStatus(self):
        """Get the lowest Fail status from all Threads of the Processor's Process.

        Return:
        -------
        Status.FailStatus:
            The Lowest Fail Status of the Processor's Process
        """

        return next(iter(sorted((thread._failStatus for thread in self._threads.values()), key=lambda x: x._priority)), None)

    def getLowestSuccessStatus(self):
        """Get the lowest Success status from all Threads of the Processor's Process.

        Return:
        -------
        Status.SuccessStatus
            The Lowest Success Status of the Processor's Process
        """
        return next(iter(sorted((thread._successStatus for thread in self._threads.values()), key=lambda x: x._priority)), None)

    def _check(self, links=True, doProfiling=False):
        """This is a wrapper for the Processor's process's check that will automatically execute it with the right parameters.

        Parameters
        ----------
        links: bool
            Should the wrapper launch the connected links or not.
        doProfiling: bool
            Whether the check method will be runt with the Processor's Profiler and data retrieved or not. (default: `False`)

        Returns
        -------
        type
            The Processor's Process feedback.
        bool
            True if the Processor's Process have any feedback, False otherwise.
        """

        #FIXME: This makes Tag.DEPENDANT / TAG.NO_CHECK not working...
        
        args, kwargs = self.getArguments(AtConstants.CHECK)

        try:
            if doProfiling:
                returnValue = self._processProfile.profileMethod(self.process.check, *args, **kwargs)
            else:
                returnValue = self.process.check(*args, **kwargs)  #TODO: Not used !!
        except Exception as exception:
            raise
        finally:
            if links:
                self.runLinks(Link.CHECK)
        
        return self._filterFeedbacks()

    def _fix(self, links=True, doProfiling=False):
        """This is a wrapper for the Processor's process's fix that will automatically execute it with the right parameters.
        
        Parameters
        ----------
        links: bool
            Should the wrapper launch the connected links or not.
        doProfiling: bool
            Whether the fix method will be runt with the Processor's Profiler and data retrieved or not. (default: `False`)

        Returns
        -------
        type
            The Processor's Process feedback.
        bool
            True if the Processor's Process have any feedback, False otherwise.
        """

        args, kwargs = self.getArguments(AtConstants.FIX)

        try:
            if doProfiling:
                returnValue = self._processProfile.profileMethod(self.process.fix, *args, **kwargs)
            else:
                returnValue = self.process.fix(*args, **kwargs)
        except Exception:
            raise
        finally:
            if links:
                self.runLinks(Link.FIX)
        
        return self._filterFeedbacks()

    def _tool(self, links=True, doProfiling=False):
        """This is a wrapper for the Processor's process's tool that will automatically execute it with the right parameters.

        Parameters
        ----------
        links: bool
            Should the wrapper launch the connected links or not.
        doProfiling: bool
            Whether the tool method will be runt with the Processor's Profiler and data retrieved or not. (default: `False`)


        Returns
        -------
        type
            The value returned by the tool method.
        """

        args, kwargs = self.getArguments(AtConstants.TOOL)

        try:
            if doProfiling:
                returnValue = self._processProfile.profileMethod(self.process.tool, *args, **kwargs)
            else:
                returnValue = self.process.tool(*args, **kwargs)
        except Exception:
            raise
        finally:
            if links:
                self.runLinks(Link.TOOL)

        return returnValue

    def check(self, links=True, doProfiling=False):
        """Same as `_check` method but will check if the Processor is checkable and has a check method."""
        if not self.__hasCheckMethod or not self.__isCheckable:
            return [], Status._DEFAULT

        return self._check(links=links, doProfiling=doProfiling)

    def fix(self, links=True, doProfiling=False):
        """Same as `_fix` method but will check if the Processor is checkable and has a check method."""
        if not self.__hasFixMethod or not self.__isFixable:
            return [], Status._DEFAULT

        return self._fix(links=links, doProfiling=doProfiling)

    def tool(self, links=True, doProfiling=False):
        """Same as `_tool` method but will check if the Processor is checkable and has a check method."""
        if not self.__hasToolMethod or not self.__hasTool:
            return None

        return self._tool(links=links, doProfiling=doProfiling)

    def runLinks(self, which):
        """Run the Processor's links for the given method.
        
        Parameters:
        -----------
        which: Athena.AtCore.Link
            Which link we want to run.
        """

        for link in self.__linksData[which]:
            link()

    def getArguments(self, method):
        """Retrieve arguments for the given method of the Processor's Process.
        
        Parameters
        ----------
        method: types.FunctionType
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
        """Setup the tags used by this Processor to modify the Processor's behaviour."""

        tags = self._tags

        if tags is None:
            return

        if tags & Tag.DISABLED:
            self.__isEnabled = False

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
            List of all objects used to resolve the current Blueprint links. Objects to skip have to be replaced with `None`.
        check: str
            Name of the method to use as check link on the given objects.
        fix: str
            Name of the method to use as fix link on the given objects.
        tool: str
            Name of the method to use as tool link on the given objects.
        """

        self.__linksData = linksData = {Link.CHECK: [], Link.FIX: [], Link.TOOL: []}

        if not linkedObjects:
            return

        links = self._links
        if links is None:
            return

        for link in links:
            id_, _driver, _driven = link
            if linkedObjects[id_] is None:
                continue

            driven = _driven
            driven = check if _driven == Link.CHECK else driven
            driven = fix if _driven == Link.FIX else driven
            driven = tool if _driven == Link.TOOL else driven

            linksData[_driver].append(getattr(linkedObjects[id_], driven))

    def _overrideLevels(self, process, overrides):
        """Override the Processor's Process's Threads Statuses based on a dict of overrides.

        Will iter through all Processor's Process's Threads and do the overrides from the dict by replacing the Fail
        or Success Statuses.

        Parameters:
        -----------
        process: AtCore.Process
            The Processor's Process instance.
        overrides: dict(str: dict(Status.FailStatus|Status.SuccessStatus: Status.__Status))
            The data to do the Status Overrides from.
        """

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
        """Get the Processor's Data for the given key or default value if key does not exists.

        Parameters:
        -----------
        key: typing.hashable
            The key to get the data from.
        default: object
            The default value to return if the key does not exists.
        """

        return self._data.get(key, default)

    def setData(self, key, value):
        """Set the Processor's Data for the given key

        Parameters:
        -----------
        key: typing.hashable
            The key to set the data.
        value: object
            The value to store as data for the give key.
        """

        self._data[key] = value

    def _filterFeedbacks(self):
        """ Filter the data outputed by a process to keep only these that is not empty.

        Returns
        -------
        list
            List of feedbacks that contain at least one entry.
        Stats.__Status
            The status that corespond to the feedback, based on the highest Thread's Status priority.
        """

        # We always consider that the result should be the lowest success status.
        globalStatus = Status._DEFAULT

        feedbackContainer = []
        for processThreadName, processThread in self.process.threads.items():

            # Get the feedaback, if there is no feedback for this thread it is clean.
            feedback = processThread.feedback
            if feedback:
                feedbackContainer.append(feedback)

            # If there is anything in the feedback we check if we need to increase the fail status and we add the feedback in
            # the container to return it.
            if processThread._status._priority > globalStatus._priority:
                globalStatus = processThread._status

        return feedbackContainer, globalStatus #


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


# -- MetaID and ID are prototype to manage the values in blueprints header. 
#TODO: This must be removed or replaced for something more robust.
class MetaID(type):
        
    def __getattr__(cls, value):

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

# --


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
        """This is the base `Status` class that all type of status inherit From."""
        
        _ALL_STATUS = {}

        def __new__(cls, *args, **kwargs):
            """Allow to store all new levels in the __ALL_LEVELS class variable to return singleton."""

            instance = super(cls.__class__, cls).__new__(cls)
            cls._ALL_STATUS.setdefault(instance.__class__, set()).add(instance)

            return instance
        
        def __init__(self, name, color, priority=0.0):
            """Create the __Status object and setup it's attributes"""

            self._name = name
            self._priority = priority
            self._color = color

        @property
        def name(self):
            """Property to access the name of the __Status"""
            return self._name

        @property
        def priority(self):
            """Property to access the priority of the __Status"""
            return self._priority

        @property
        def color(self):
            """Property to access the color of the __Status"""
            return self._color       

    class FailStatus(__Status):
        """Represent a Fail Status, can be instantiated to define a new Fail level"""
        
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

    class SuccessStatus(__Status):
        """Represent a Success Status, can be instantiated to define a new Success level"""

        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

    class __BuiltInStatus(__Status):
        """Represent a Built-In Status, can be instantiated to define a new Built-In level"""

        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

    _DEFAULT =  __BuiltInStatus('Default', (60, 60, 60))

    CORRECT = SuccessStatus('Correct', (22, 194, 15), 0.1)
    SUCCESS = SuccessStatus('Success', (0, 128, 0), 0.2)

    WARNING = FailStatus('Warning', (196, 98, 16), 1.1)
    ERROR = FailStatus('Error', (102, 0, 0), 1.2)
    CRITICAL = FailStatus('Critical', (150, 0, 0), 1.3)

    _EXCEPTION = __BuiltInStatus('Exception', (110, 110, 110))

    def __new__(cls, *args, **kwargs):
        """Override the __new__ method to raise an error and ensure this class can't be instantiated."""

        raise RuntimeError('Can\'t create new instance of type `{0}`.'.format(cls.__name__))

    @classmethod
    def getAllStatus(cls):
        """Return all existing Status in a list.
        
        Return:
        -------
        list
            List containing all Status defined, Based on `Status.__Status._ALL_STATUS` keys.
        """

        return [status for statusTypeList in cls.__Status._ALL_STATUS.values() for status in statusTypeList]

    @classmethod
    def getStatusByName(cls, name):
        """Get a Status based on it's name.

        Parameters:
        -----------
        name: str
            Name of the status to find.

        Return:
        -------
        Status.__Status | None
            The status that match the name if any, else None.
        """

        for status in cls.getAllStatus():
            if status._name == name:
                return status
        else:
            return None

    @classmethod
    def getAllFailStatus(cls):
        """Get all Fail Statuses.

        Return:
        -------
        list
            List of all Fail Statuses defined.
        """

        return cls.__Status._ALL_STATUS[cls.FailStatus]

    @classmethod
    def getAllSuccessStatus(cls):
        """Get all Success Statuses.

        Return:
        -------
        list
            List of all Success Statuses defined.
        """

        return cls.__Status._ALL_STATUS[cls.SuccessStatus]

    @classmethod
    def lowestFailStatus(cls):
        """Get the lowest Fail Status based on Status._priority.

        Return:
        -------
        FailStatus:
            The Fail Status with the lowest priority.
        """

        return sorted(cls.getAllFailStatus(), key=lambda x: x._priority)[0]

    @classmethod
    def highestFailStatus(cls):
        """Get the highest Fail Status based on Status._priority.

        Return:
        -------
        FailStatus:
            The Fail Status with the highest priority.
        """

        return sorted(cls.getAllFailStatus(), key=lambda x: x._priority)[-1]

    @classmethod
    def lowestSuccessStatus(cls):
        """Get the lowest Success Status based on Status._priority.

        Return:
        -------
        FailStatus:
            The Success Status with the lowest priority.
        """

        return sorted(cls.getAllSuccessStatus(), key=lambda x: x._priority)[0]

    @classmethod
    def highestSuccessStatus(cls):
        """Get the highest Success Status based on Status._priority.

        Return:
        -------
        FailStatus:
            The Success Status with the highest priority.
        """

        return sorted(cls.getAllSuccessStatus(), key=lambda x: x._priority)[-1]


class Feedback(object):
    """Feedback object are descriptors that contains and allow to manage result found by a Process.

    The Feedback hold the result of one thread and remains linked to it, it must be initialised with values to display
    and value to select that may be an object without `__repr__` or `__str__` method.
    A `selectMethod` may also be defined and must be used in order to allow selection for object that can not be selected
    using the `Athena.AtUtils.softwareSelection` method.

    The feedback object allow to select all it's result or only one result and iteration is possible to access all items.
    """

    def __init__(self, thread, toDisplay, toSelect, selectMethod=None, help=None):
        """Create a new instance of Feedback for the given thread.

        Parameters:
        -----------
        thread: Athena.AtCore.ProcessThread
            The thread which this Feedback hold result.
        toDisplay: collections.Iterable
            An ordererd sequence of objects that will be used to display, index must match the objects provided to toSelect.
        toSelect: collections.Iterable
            And ordered sequence of objects that will be used for selection, index must match the objects provided to toDisplay.
        selecMethod: types.FunctionType
            A method that can take a list of objects like `toSelect` and select them in the software or OS. (default: None)
        help: str
            An help about how to fix the errors contains in this feedback (for example..) (default: None)
        """

        self._thread = thread

        if len(toDisplay) != len(toSelect):
            raise ValueError('You must have the same amount of object to select and to display')

        self._toDisplay = list(toDisplay)
        self._toSelect = list(toSelect) or self._toDisplay

        self._help = help

        self._selectMethod = selectMethod or AtUtils.softwareSelection

    def __iter__(self):
        """Allow to iter over the feedback object.
        
        Return:
        -------
        iterator
            Iterator that yields values from toSelect.
        """

        return iter(self._toSelect)

    @property
    def toDisplay(self):
        """Property to get the Feedbacks's results for display

        Return:
        -------
        list
            List of the result used for display.
        """

        return self._toDisplay

    @property
    def toSelect(self):
        """Property to get the Feedbacks's results for selection

        Return:
        -------
        list
            List of the result used for selection.
        """

        return self._toSelect

    @property
    def selectMethod(self):
        """Property to get the Feedbacks's method to select the results from `toSelect`

        Return:
        -------
        types.FunctionType
            Function that allow to select a list containing the same values as in `toSelect`
        """

        return self._selectMethod
    
    @property
    def help(self):
        """Property to get the help about this feedback object.

        Return:
        -------
        str
            The help about this Feedback and its result.
        """

        return self._help

    def selectAll(self):
        """Allow to select all the result in the `toSelect` list using the Feedacks `selectMethod`"""

        self._selectMethod(self._toSelect)

    def select(self, indexes):
        """Allow to select all values in the `toSelect` at the given indexes.

        Parameters:
        -----------
        indexes: list(int, ...)
            List of the indexes we want to select in the given feedback.
        """

        self._selectMethod([self._toSelect[i] for i in indexes])

    def append(self, toDisplay, toSelect):
        """Add the given pair of values to display and to select to the Feedback data.
        
        Parameters:
        -----------
        toDisplay: object
            The object to display to append to the feedback.
        toSelect: object
            The object to select to append to this Feedback.
        """

        self._toDisplay.append(toDisplay)
        self._toSelect.append(toSelect)

    def __bool__(self):
        """Return wether the Feedback contain values or not.

        Return:
        -------
        bool
            True if the feedback have any result, else False. (based on the `toSelect` values.)
        """

        return bool(self._toSelect)

    __nonzero__ = __bool__


class Thread(object):
    """To define in a Process as class attribute constant."""

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
    def title(self):
        return self._title

    @property
    def failStatus(self):
        return self._failStatus

    @property
    def successStatus(self):
        return self._successStatus


class _ProcessThread(Thread):
    """Replace a Thread to be used in an instance"""

    def __init__(self, thread):

        super(_ProcessThread, self).__init__(
            title=thread._title, 
            failStatus=thread._defaultFailStatus,
            successStatus=thread._defaultSuccessStatus,
            documentation=thread._documentation
        )

        self._thread = thread
        self._enabled = True

        self._state = Status.SuccessStatus
        self._status = self._successStatus

        self._feedback = None

    @property
    def title(self):
        return self._thread._title

    @property
    def documentation(self):
        return self._thread._documentation
    
    @property
    def state(self):
        return self._state

    @property
    def status(self):
        return self._status

    @property
    def enabled(self):
        return self._enabled

    @property
    def feedback(self):
        return self._feedback

    def reset(self):
        self._state = Status.SuccessStatus
        self._status = self._successStatus

        self._feedback = None

    def setEnabled(self, state):
        self._enabled = bool(state)

    def setFail(self, toSelect=None, toDisplay=None, selectMethod=None, help=None, overrideStatus=None):
        if overrideStatus is not None:
            if isinstance(overrideStatus, Status.FailStatus):
                self._status = overrideStatus
            else:
                raise TypeError('Fail Status can only be an instance or subtype of `{}`.'.format(type(Status.FailStatus)))
        else:
            self._status = self._failStatus

        if toDisplay:
            self._feedback = Feedback(self, toSelect, toDisplay, selectMethod=selectMethod, help=help)
        else:
            self._feedback = Feedback(self, (), (), selectMethod=None, help=None)

        self._state = Status.FailStatus

    def setSuccess(self, toSelect=None, toDisplay=None, selectMethod=None, help=None, overrideStatus=None):
        if overrideStatus is not None:
            if isinstance(overrideStatus, Status.SuccessStatus):
                self._status = overrideStatus
            else:
                raise TypeError('Success Status can only be an instance or subtype of `{}`.'.format(type(Status.SuccessStatus)))
        else:
            self._status = self._successStatus

        if toDisplay:
            self._feedback = Feedback(self, toSelect, toDisplay, selectMethod=selectMethod, help=help)
        else:
            self._feedback = Feedback(self, (), (), selectMethod=None, help=None)

        self._state = Status.SuccessStatus


# -- WIP
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
# -- WIP END


class _ProcessProfile(object):
    """Profiler that allow to profile the execution of `Athena.AtCore.Process`"""

    # Match integers, floats (comma or dot) and slash in case there is a separation for primitive calls.
    DIGIT_PATTERN = r'([0-9,.\/]+)'
    DIGIT_REGEX = re.compile(DIGIT_PATTERN)

    CATEGORIES = ('ncalls', 'tottime', 'percall', 'cumtime', 'percall', 'filename:lineno(function)')

    def __init__(self):
        """Initialiste a Process Profiler and define the default instance attributes."""

        self._profiles = {} 

    def get(self, key, default=None):
        """Get a profile log from the given key, or default if key does not exists.
        
        Parameters:
        -----------
        key: typing.hashable
            The key to get data from in the profiler's profile data.
        default: object
            The default value to return in case the key does not exists.

        Return:
        -------
        object
            The data stored at the given key if exists else the default value is returned.
        """

        return self._profiles.get(key, default)

    def _getCallDataList(self, callData):
        """Format and split `cProfile.Profiler` call data list (each value in the list must be one line.)

        This will mostly remove heading or trailing spaces and return a list of tuple where each values in the
        string is now an entry in the tuple. The order is the same than `Athena.AtCore._ProcessProfile.CATEGORIES`.
        
        Parameters:
        -----------
        callData: list(str, ...)
            List of call entry from a `cProfile.Profiler` run.
        """

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
        """Profile the given method execution and return it's result. The profiling result will be stored in the 
        object.

        Try to execute the given method with the given args and kwargs and write the result in a temporary file.
        The result will then be read and each line splited to save a dict in the object `_profiles` attribute using
        the name of the given method as key.
        This dict will hold information like the time when the profiling was done (key = `time`, it can allow to not 
        update data in a ui for instance), the total number of calls and obviously a tuple with each call data (`calls`).
        The raw stats result is also saved under the `rawStats` key if the user want to use it directly.
        
        Parameters:
        -----------
        method: types.FunctionType
            A callable for which we want to profile the execution and save new data.
        *args: *list
            The arguments to call the method with.
        **kwargs: **kwargs
            The keywords arguments to call the method with.

        Return:
        -------
        object:
            The result of the given method with the provided args and kwargs.
        """

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
            raise

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
