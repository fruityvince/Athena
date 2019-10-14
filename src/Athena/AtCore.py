import re
import numbers
import six

from pprint import pprint

from Athena import AtUtils
from Athena import AtConstants


class Process(object):
    """Abstract class from which any Athena User Process have to inherit.

    The Process object define default instance attributes for user to use and that are managed through the `automatic`
    decorator.
    It also comes with some methods to manage the internal feedback and the potentially connected QProgressbar.
    There is 3 not implemented methods to override if needed (`check`, `fix` and `tool`)
    """

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

        # Private instance attributes (Used for internal management)
        instance._name = instance.__class__.__name__
        instance._feedback = []
        instance._progressbar = None

        # Public instance attribute (To be used by user to manage process data)
        instance.toCheck = []
        instance.toFix = []
        instance.data = []
        instance.isChecked = False

        # Dunder instance attribute (To be used by user to custom the process)
        instance._docFormat_ = {}

        return instance

    def __init__(self):
        pass

    def __repr__(self):
        """Format the representation of a process"""
        return '<Process {0} at {1}>'.format(self.name, hex(id(self)))
        
    def check(self):
        raise NotImplementedError
        
    def fix(self):
        raise NotImplementedError

    def tool(self):
        raise NotImplementedError

    @property
    def name(self):
        """Return the process name, default name is class name"""
        return self._name

    @name.setter
    def name(self, value):
        """Define the process name """
        self._name = str(value)

    def setProgressValue(self, value, text=None):
        """Set the progress value of the process progressBar if exist.
        
        Parameters
        -----------
        value: numbres.Number
            The value to set the progress to.
        text: str or None
            Text to display in the progressBar, if None, the Default is used.
        """

        if self._progressbar is None:
            return

        assert isinstance(value, numbers.Number), 'Argument `value` is not numeric'
        
        self._progressbar.setValue(float(value))
        
        if text and text != self._progressbar.text():
            self._progressbar.setFormat(AtConstants.PROGRESSBAR_FORMAT.format(text))

    def addFeedback(self, title, toDisplay, toSelect=None, documentation=None):
        """Add a new feedback for the process to display

        Parameters
        -----------
        title: str
            The title linked to this feedback.
        toDisplay: <iterable> or Ellipsis
            Iterable object containing all objects found for this title, these objetcs will be displayed
            and used for selection if `toSelect` is None.
            If toDisplay is Ellipsis, this feedback can be used to only display a title.
        toSelect: <iterable> or None
            If an iterable is provided it should be ordered like the `toDisplay` iterable to match display
            and selection. If set to None, the objects used for selection will be thoses used for display.
        documentation: str or None
            This allow to affect a documentation for this feedback.
        """

        assert title, 'A title is required to add a new feedback'

        if not toDisplay:
            return

        # If toDisplay is not None check if it is necessary to conform it. Else, add None to the value to handle a no display.
        if toDisplay is not Ellipsis:

            # Check if toDisplay is conform, if it is not a list or a tuple, cast it to tuple.
            if not hasattr(toDisplay, '__iter__'):
                toDisplay = (toDisplay,)

            # Check toSelect, if it have not been given, set it to be equal to toDisplay, if it is not a list or a tuple cast it to tuple.
            if toSelect is None:
                toSelect = toDisplay
            elif not hasattr(toSelect, '__iter__'):
                toSelect = (toSelect,)

            # Check if there is the same amount of object toDisplay and toSelect.
            if len(toSelect) != len(toDisplay):
                toSelect = toDisplay

        self._feedback.append({
            'title': title,
            'toDisplay': toDisplay,
            'toSelect': toSelect,
            'documentation': documentation
        })

    def clearFeedback(self):
        """Clear all feedback for this process"""
        self._feedback = []


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
    overriddenMethods = AtUtils.getOverriddedMethods(cls, Process)

    check_ = overriddenMethods.get(AtConstants.CHECK, None)
    if check_ is not None:
        def check(self, *args, **kwargs):

            self.clearFeedback()

            self.toCheck = type(self.toCheck)()
            self.toFix = type(self.toFix)()
            self.data = type(self.data)()

            check_(self, *args, **kwargs)

            self.isChecked = True

        setattr(cls, AtConstants.CHECK, check)  # Replace the check method in the process

    fix_ = overriddenMethods.get(AtConstants.FIX, None)
    if fix_ is not None:
        def fix(self, *args, **kwargs):

            fix_(self, *args, **kwargs)

            self.isChecked = False

        setattr(cls, AtConstants.FIX, fix)  # Replace the fix method in the process

    tool_ = overriddenMethods.get(AtConstants.TOOL, None)
    if tool_ is not None:
        def tool(self, *args, **kwargs):

            tool_(self, *args, **kwargs)

        setattr(cls, AtConstants.TOOL, tool)  # Replace the tool method in the process

    return cls


class Data(object):

    def __init__(self):
        pass


class Register(object):
    """Register class that contain and manage all blueprints for all available environments.

    At initialization the register will get all data it found and store them. It will also give easy accessible data
    to work with like contexts and software.
    """

    def __init__(self, verbose=False):
        """Get the software and setup data.

        Parameters
        -----------
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        self.verbose = verbose
        
        self._software = AtUtils.getSoftware()

        self._data = {}
        self._packages = {}
        self._contexts = []

        self._blueprints = []

        self._context = None
        self._env = None

        self._setup()

    def __repr__(self):
        """Return the representation of the Register"""

        return "<{0} {1} - context: {2}, env: {3}>".format(
            self.__class__.__name__,
            self._software.capitalize(),
            self._context,
            self._env,
        )

    def __nonzero__(self):
        """Allow to interpret this object as a boolean.
        
        Returns:
        bool
            True if there is any blueprint, False otherwise.
        """

        return bool(self._blueprints)

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
            - blueprints.keys()  # (index of blueprints)
            - context  # (Current targeted context)
            - env  # (Current targeted env)
        """

        if not isinstance(other, self.__class__):
            return False

        return all((
            self._software == other.software,
            self._contexts == other._contexts,
            self._blueprints == other.blueprints,
            self._context == other.context,
            self._env == other.env
        ))

    @property
    def data(self):
        """Get the Register internal data"""
        return self._data

    @property
    def software(self):
        """Get the Register software"""
        return self._software

    @property
    def blueprints(self):
        """Get all Register blueprints"""
        return self._blueprints

    @property
    def contexts(self):
        """Get all Register contexts"""
        return self._contexts

    @property
    def context(self):
        """Get the current context the register are pointing on"""
        return self._context

    @property
    def env(self):
        """Get the current env the register are pointing on"""
        return self._env

    def reload(self):
        """Reload data for the register instance.
        
        When this method is called it will clean data and recreate them.

        Parameters
        -----------
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        self._data = {}

        self._setup()

    def _setup(self):
        """Setup data for the register instance.
        
        Setup the register internal data from packages.
        The data contain all informations needed to make the tool work like each contexts, envs, blueprints and processes.
        Here only the contexts and envs are retrieved. To get blueprints, getBlueprints should be called.

        Parameters
        -----------
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        self._packages = packages = AtUtils.getPackages()

        for context, packageData in packages.items():
            envs = AtUtils.getEnvs(packageData['import'], software=self._software)
            
            self._data[context] = packageData
            self._data[context]['envs'] = envs

        self._contexts = packages.keys()
    
    def getEnvs(self, context):
        """Return envs stored in the given context.
        
        This will return list of envs from the given context. Especially useful to feed a widget.

        Parameters
        -----------
        context: str
            Context from which return stored envs.
        
        Returns
        -------
        list
            List of envs for the given context.
        """

        # First, get the context in data
        contextData = self._data.get(context, None)
        if contextData is None:
            return []

        # Then, get the env in the precedently queried context dict.
        envData = contextData.get('envs', None)
        if envData is None:
            return []

        return envData.keys()

    def getBlueprints(self, context, env, forceReload=False):
        """Get the blueprint object for the given context and env.
        
        Try to retrieve the blueprints for the specified env in the specified context. If there is already a blueprints,
        don't re-instanciate them if forceReload is `False`.

        Parameters
        ----------
        context: str
            Context from which retrieve the blueprint in the given env.
        env: str
            Env from which get the blueprint object.
        forceReload: bool
            Define if the function should reload its blueprints or not.

        Returns
        -------
        dict
            Dict containing all blueprint objects for the given context env.
        """

        assert context in self._contexts, '"{0}" Are not registered yet in this Register'.format(context)

        self._blueprints = []
        self._context = context

        # Get the dict for the specified context in self._data
        contextData = self._data.get(context, None)
        if contextData is None:
            return {}

        # Get the dict for all envs in self._data[context]
        envsData = contextData.get('envs', None)
        if envsData is None:
            return {}

        # Get the dict for the specified env in self._data[context]['envs']
        envData = envsData.get(env, None)
        if envData is None:
            return {}
        self._env = env

        # Get the blueprint in self._data[context]['envs'][env]. If one is found, return it.  #TODO: It seems there is an error
        blueprints = envData.get('blueprints', None)
        if blueprints is not None and not forceReload: # If not forceReload, return the existing blueprints. #FIXME: self._blueprints is empty outside dev
            return blueprints['objects']

        # Get the env module to retrieve the blueprint from.
        envModule = envData.get('module', None)
        if envModule is None:
            
            # Get the string path to the env package in self._data[context]['envs'][env]['import']
            envStr = envData.get('import', None)
            if envStr is None:
                return {}

            # Load the env module from the string path stored.
            envModule = AtUtils.importFromStr('{}.{}'.format(envStr, envData), verbose=self.verbose)
            if envModule is None:
                return {}
            envData['module'] = envModule

        # If force reload are enabled, this will reload the env module.
        if forceReload:
            reload(envModule)

        # Try to access the `blueprints` variable in the env module
        blueprints = getattr(envModule, 'register', {})
        ID.flush()

        # Generate a blueprint object for each process retrieved in the `blueprint` variable of the env module.
        self._blueprints = blueprintObjects = []
        for i in range(len(blueprints)):
            blueprintObjects.append(Blueprint(blueprint=blueprints[i], verbose=self.verbose))
        
        # Default resolve for blueprints if available in batch, call the `resolveLinks` method from blueprints to change the targets functions.
        batchLinkResolveBlueprints = [blueprintObject if blueprintObject._inBatch else None for blueprintObject in blueprintObjects]
        for blueprint in blueprintObjects:
            blueprint.resolveLinks(batchLinkResolveBlueprints, check=Link.CHECK, fix=Link.FIX, tool=Link.TOOL)

        # Finally store blueprints in the env dict in data.
        envData['blueprints'] = {
                'data': blueprints,
                'objects': blueprintObjects,
        }

        return self._blueprints

    def reloadBlueprintsModules(self):
        """Reload the Blueprints's source modules to reload the Processes in it
        
        Should better be called in dev mode to simplify devellopment and test of a new Process.

        Returns
        -------
        list(module, ...)
            Lis of all reloaded modules.
        """

        modules = list(set([blueprint._module for blueprint in self._blueprints]))
        for module in modules:
            reload(module)

        return modules

    def getData(self, data):
        """Get a specific data in the register current context and env.

        Parameters
        ----------
        data: str
            The key of the data to get in the register at [self._context]['envs'][self._env]

        Returns
        -------
        type or NoneType
            Data queried if exist, else NoneType.
        """

        if not self._context or not self._env:
            return None

        return self._data[self._context]['envs'][self._env].get(data, None)

    def setData(self, key, data):
        """Set the current data at the given key of the register's current env dict.

        Parameters
        ----------
        key: type (immutable)
            The key for which to add the data in the register current context and env dict.
        data: type
            The data to store in the register's current env dict of the current context.

        Returns
        -------
        Register
            Return the instance of the object to make object fluent.
        """

        self._data[self._context]['envs'][self._env][key] = data

        return self

    def setVerbose(self, value):
        """Set the Verbose state.

        Parameters
        ----------
        value: bool
            True or False to enable or disable the verbose

        Returns
        -------
        Register
            Return the instance of the object to make object fluent.
        """

        self.verbose = bool(value)

        return self

    def getContextIcon(self, context):
        """Get the icon for the given context

        Returns
        -------
        str
            Return the icon of the queried context.
        """

        return self._packages.get(context, {}).get('icon', None)

    def getEnvIcon(self, context, env):
        """Get the icon for the given env of the given context

        Returns
        -------
        str
            Return the icon of the queried env of the given context.
        """

        return self._data[context]['envs'][env].get('icon', None)

class Blueprint(object):
    """This object will manage a single process instance to be used through an ui.

    The blueprint will init all informations it need to wrap a process like the methods that have been overrided, 
    if it can run a check, a fix, if it has a ui, its name, docstring and a lot more.
    """

    def __init__(self, blueprint, verbose=False):
        """Get the software and setup data.

        Parameters
        -----------
        blueprint: dict
            Dict containing the process string and the object (optional).
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        self.verbose = verbose

        self.blueprint = blueprint
        self.processStr = blueprint.get('process', None)
        self.category = blueprint.get('category', 'Other')

        initArgs, initKwargs = self.getArguments('__init__')
        self._module = None
        self._process = self.getProcess(initArgs, initKwargs)
        self._links = {AtConstants.CHECK: [], AtConstants.FIX: [], AtConstants.TOOL: []}
        self._options = blueprint.get('options', {})

        self._name = AtUtils.camelCaseSplit(self._process._name)
        self._docstring = self.createDocstring()

        self._check = None
        self._fix = None
        self._tool = None

        self._isEnabled = True

        self._isCheckable = False
        self._isFixable = False
        self._hasTool = False

        self._inUi = True
        self._inBatch = True

        self._isNonBlocking = False

        # setupCore will automatically retrieve the method needed to execute the process. 
        # And also the base variable necessary to define if theses methods are available.
        self.setupCore()
        self.setupTags()

    def __repr__(self):
        """Return the representation of the object."""

        return "<{0} '{1}' object at {2}'>".format(self.__class__.__name__, self._process.__class__.__name__, hex(id(self)))

    @property
    def options(self):
        """Get the Blueprint's options"""
        return self._options

    @property
    def name(self):
        """Get the Blueprint's name"""
        return self._name

    @property
    def docstring(self):
        """Get the Blueprint's docstring"""
        return self._docstring

    @property
    def isEnabled(self):
        """Get the Blueprint's enabled state"""
        return self._isEnabled
    
    @property
    def isCheckable(self):
        """Get the Blueprint's checkable state"""
        return self._isCheckable

    @property
    def isFixiable(self):
        """Get the Blueprint's fixable state"""
        return self._isFixiable

    @property
    def hasTool(self):
        """Get if the Blueprint's have a tool"""
        return self._hasTool

    @property
    def inUi(self):
        """Get if the Blueprint should be run in ui"""
        return self._inUi
    
    @property
    def inBatch(self):
        """Get if the Blueprint should be run in batch"""
        return self._inBatch

    @property
    def isNonBlocking(self):
        """Get the Blueprint's non blocking state"""
        return self._isNonBlocking
        
    def check(self, links=True):
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

        if self._check is None:
            return None, None
        
        args, kwargs = self.getArguments(AtConstants.CHECK)
        returnValue = self._check(*args, **kwargs)  #TODO: Not used !!

        result = self.filterResult(self._process._feedback)

        if links:
            self.runLinks(AtConstants.CHECK)
        
        return result, bool(result)

    def fix(self, links=True):
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

        if self._fix is None:
            return None

        args, kwargs = self.getArguments(AtConstants.FIX)
        returnValue = self._fix(*args, **kwargs)

        if links:
            self.runLinks(AtConstants.FIX)

        return returnValue

    def tool(self, links=True):
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

        if self._tool is None:
            return

        args, kwargs = self.getArguments(AtConstants.TOOL)
        result = self._tool(*args, **kwargs)

        if links:
            self.runLinks(AtConstants.TOOL)

        return result

    def runLinks(self, which):

        links = self._links[which]

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

        arguments = self.blueprint.get('arguments', None)
        if arguments is None:
            return ([], {})

        arguments = arguments.get(method, None)
        if arguments is None:
            return ([], {})

        return arguments

    def getProcess(self, args, kwargs):
        """Retrieve the process path and create an instance.
        
        Parameters
        ----------
        args: list
            List of all args expected by the process __init__ method.
        kwargs: dict
            dict of all kwargs expected by the process __init__ method.

        Returns
        -------
        object
            An instance of the process class.
        """

        if self.processStr is None:
            raise RuntimeError() #TODO Add an error message here

        moduleStr, _, processStr = self.processStr.rpartition('.')
        self._module = module = AtUtils.importFromStr(moduleStr)
        if module is None:
            raise RuntimeError('Can not import module {0}'.format(moduleStr))

        processClass = getattr(module, processStr)

        return processClass(*args, **kwargs)

    def setupCore(self):
        """Setup all data for the wrapping method (check, fix, tool...) and bool to know if isCheckable, isFixable, 
        hasTool...

        Retrieve all overridden methods and set the instance attributes with the retrieved data.
        """
        
        overriddenMethods = AtUtils.getOverriddedMethods(self._process.__class__, Process)

        if overriddenMethods.get(AtConstants.CHECK, False):
            self._isCheckable = True
            self._check = self._process.check

        if overriddenMethods.get(AtConstants.FIX, False):
            self._isFixable = True
            self._fix = self._process.fix

        if overriddenMethods.get(AtConstants.TOOL, False):
            self._hasTool = True
            self._tool = self._process.tool

    def setupTags(self):
        """Setup the tags used by this process

        This method will setup the tags from the Tags given in the env module to affect the process behaviour.
        """

        tags = self.blueprint.get('tags', None)
        if tags is None:
            return

        if tags & Tag.DISABLED:
            self._isEnabled = False

        if tags & Tag.NO_CHECK:
            self._isCheckable = False

        if tags & Tag.NO_FIX:
            self._isFixable = False

        if tags & Tag.NO_TOOL:
            self._hasTool = False

        if tags & Tag.NON_BLOCKING:
            self._isNonBlocking = True

        if tags & Tag.NO_BATCH:
            self._inBatch = False

        if tags & Tag.NO_UI:
            self._inUi = False

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

        self._links = {AtConstants.CHECK: [], AtConstants.FIX: [], AtConstants.TOOL: []}

        if not linkedObjects:
            return

        links = self.blueprint.get('links', None)
        if links is None:
            return

        assert all([hasattr(link, '__iter__') for link in links]), 'Links should be of type tuple(int, str, str)'
        for link in links:
            index, _driver, _driven = link
            if linkedObjects[index] is None:
                continue

            driven = _driven
            driven = check if _driven == Link.CHECK else driven
            driven = fix if _driven == Link.FIX else driven
            driven = tool if _driven == Link.TOOL else driven

            self._links[_driver].append(getattr(linkedObjects[index], driven))

    def setProgressbar(self, progressbar):
        """ Called in the ui this method allow to give access to the progress bar for the user

        Parameters
        ----------
        progressbar: QtWidgets.QProgressBar
            QProgressBar object to connect to the process to display check and fix progression.
        """

        self._process._progressbar = progressbar

    def createDocstring(self):
        """Generate the Blueprint doc from Process docstring and data in the `_docFormat_` variable.

        Returns
        -------
        str
            Return the formatted docstring to be more readable and also display the path of the process.
        """

        docstring = self._process.__doc__ or AtConstants.NO_DOCUMENTATION_AVAILABLE
        docstring += '\n {0} '.format(self.processStr)

        docFormat = {}
        for match in re.finditer(r'\{(\w+)\}', docstring):
            matchStr = match.group(1)
            docFormat[matchStr] = self._process._docFormat_.get(matchStr, '')

        return docstring.format(**docFormat)

    def filterResult(self, result):
        """ Filter the data ouputed by a process to keep only these that is not empty.

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

        filtered_result = []
        for feedback in result:
            toDisplay = feedback['toDisplay']
            if not toDisplay:
                continue
            elif feedback['toDisplay'] is Ellipsis:
                feedback['toDisplay'] = []
                feedback['toSelect'] = []

            filtered_result.append(feedback)

        return filtered_result


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

    DISABLED        = 1

    NO_CHECK        = 2
    NO_FIX          = 4
    NO_TOOL         = 8

    NON_BLOCKING    = 16
    
    NO_BATCH        = 32
    NO_UI           = 64
    
    OPTIONAL        = NON_BLOCKING | DISABLED
    DEPENDANT       = NO_CHECK | NO_FIX | NO_TOOL


class Link(object):
    """Give access to the AtConstants to simplify the use of the links."""

    CHECK = AtConstants.CHECK
    FIX = AtConstants.FIX
    TOOL = AtConstants.TOOL


class MetaID(type):
        
    def __getattr__(cls, value):

        if value not in cls._data_:
            idCount = len(cls._data_)
            setattr(cls, value, idCount)
            cls._data_[value] = idCount

        return value

    def __getattribute__(cls, value):
        
        if value in type.__dict__:
            raise ValueError('Can not create ID: `{0}`, it will override python <type> inherited attribute of same name.'.format(value))

        return type.__getattribute__(cls, value)

#TODO: six is used to ensure compatibility between python 2.x and 3.x, replace by `object, metaclass=MetaID`
class ID(six.with_metaclass(MetaID, object)):
    
    _data_ = {}

    def __new__(cls):
        raise NotImplementedError('{0} is not meant to be instanciated.'.format(cls))

    @classmethod
    def flush(cls):
        for key in cls._data_:
            delattr(cls, key)
        
        cls._data_.clear()


# def merge_env(env_pck):

#     to_merge = []

#     for first_env in env_pck:
#         for second_env in env_pck:
#             if first_env == second_env:
#                 continue
#             if first_env[-1][0] == second_env[-1][0]:
#                 index = None
#                 for i in range(len(to_merge)):
#                     if to_merge[i] != first_env[-1][0]:
#                         continue
#                     index = i
#                 if index is None:
#                     to_merge.append((first_env[-1][0], []))
#                     index = -1
#                 to_merge[index][-1].append(second_env[-1][-1])

#     return to_merge




""" #TODO: This snippet of code is now out of date
def start(env, register, verbose=False):

    processes = load_moduleStr('{}.{}'.format(env, register))
    print Register.extract()

    for process in []:

        # separate module hierarchy from class to instance (check)
        moduleStr, class_str = process[0].rsplit('.', 1)

        module = load_moduleStr(moduleStr, verbose=verbose)  #module etant une instance comme cmds le serait. il devrait avoir une plus grande portee.

        if module is None:
            raise RuntimeError('Module {0} can not be found'.format(moduleStr))

        # get the process class <class 'gpdev.tools.Athena.testCheck.TestForSanityCheck'>
        processClass = getattr(module, class_str, None) #TODO Enhance this process
        if processClass is None:
            raise RuntimeError('Process class {0} can not be found in module {1}'.format(class_str, moduleStr))

        if processClass: #create an instance.
            __process = processClass()  # instance de la class <gpdev.tools.Athena.testCheck.TestForSanityCheck object at 0x000001A4C70B4A90>

        if not __process:
            raise RuntimeError('Unable to instance ' + processClass) #custom erreurs
        
        # get list of methods that have been overrided (implemented.)
        overrided_method = AtUtils.getOverriddedMethods(processClass, Process)

        print overrided_method

        # if '__init__' in overrided_method:
        #     print '__init__ for ' + str(processClass)
        #     __process.__init__()

        # if AtConstants.CHECK in overrided_method:
        #     print 'check for ' + str(processClass)
        #     __process.check()

        # if AtConstants.FIX in overrided_method:
        #     print 'fix for ' + str(processClass)
        #     __process.fix()


# This function is the entry point to load all environmnet
def main(envs=None, verbose=False):

    if not envs:
        envs = AtUtils.get_envs()  # Get all already imported envs
        if verbose: print('{} envs have been succesfully retrieved ({})'.format(len(envs), ', '.join(envs)))

    # Keys will be the envs resolved path and the values will be associated env_pck
    env_pck = {}
    for env in envs:
        env_pck[env] = AtUtils.rez_env(env)

    if not env_pck:
        AtConstants.LOGGER.info('No envs available') 
        return

    process_registers = env_pck.get(env[0], None)
    if process_registers is None:
        raise ImportError('No register {0} have been resolved, you should import them'.format(register))

    process_importer = process_registers.get(register, None)
    if process_importer is None:
        raise ImportError('No register {0} found in env {1}'.format(register, env))  # An env is a package containing register that is like modules.

    start(env, register)

"""