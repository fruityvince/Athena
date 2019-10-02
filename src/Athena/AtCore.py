import re
import numbers

from Athena import AtUtils
from Athena import AtConstants


class Process(object):
    """
    
    """

    def __new__(cls, *args, **kwargs):
        """Generate a new class instance and setup its default attributes.
        
        The base class `Process` can't be instanciated because it is an abstract class made to inherited
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
        return self._name

    @name.setter
    def name(self, value):
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
        value = float(value)  # Ensure that value is of type float.
        
        self._progressbar.setValue(value)
        
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
    overriddenMethods = AtUtils.getOverriddenMethods(cls, Process)

    check_ = overriddenMethods.get('check', None)
    if check_ is not None:
        def check(self, *args, **kwargs):

            self.clearFeedback()

            self.toCheck = type(self.toCheck)()
            self.toFix = type(self.toFix)()
            self.data = type(self.data)()

            check_(self, *args, **kwargs)

            self.isChecked = True

        setattr(cls, 'check', check)  # Replace the check method in the process

    fix_ = overriddenMethods.get('fix', None)
    if fix_ is not None:
        def fix(self, *args, **kwargs):

            fix_(self, *args, **kwargs)

            self.isChecked = False

        setattr(cls, 'fix', fix)  # Replace the fix method in the process

    tool_ = overriddenMethods.get('tool', None)
    if tool_ is not None:
        def tool(self, *args, **kwargs):

            tool_(self, *args, **kwargs)

        setattr(cls, 'tool', tool)  # Replace the tool method in the process

    return cls


class Data(object):

    def __init__(self):
        pass


class Register(object):
    """Register class that contain and manage all blueprints for all available environments.

    At initialization the register will get all data it found and store them. It will also give easy accessible data
    to work with like prods and software.
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
        self._prods = []

        self._blueprints = {}

        self._setup()

        self._prod = None
        self._env = None
        self._module = None

    def __repr__(self):
        return "<{0} {1} - prod: {2}, env: {3}>".format(
            self.__class__.__name__,
            self._software.capitalize(),
            self._prod,
            self._env,
        )

    def __nonzero__(self):
        """ Allow to interpret this object as a boolean.
        
        Returns:
        bool
            True if there is any blueprint, False otherwise.
        """ #TODO: I forget the term

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
            - _data.keys()  # (prods)
            - prods
            - blueprints.keys()  # (index of blueprints)
            - prod  # (Current targeted prod)
            - env  # (Current targeted env)
        """

        if not isinstance(other, self.__class__):
            return False

        return all([
            self._software == other.software,
            self._data.keys() == other._data.keys(),
            self._prods == other._prods,
            self._blueprints.keys() == other.blueprints.keys(),
            self._prod == other.prod,
            self._env == other.env
        ])

    @property
    def software(self):
        return self._software

    @property
    def blueprints(self):
        return self._blueprints

    @property
    def prods(self):
        return self._prods

    @property
    def prod(self):
        return self._prod

    @property
    def env(self):
        return self._env

    @property
    def module(self):
        return self._module

    def reload(self):
        """Reload data for the register instance.
        
        When this method is called it will clean data and recreate them.

        Parameters
        -----------
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        self._data = {}
        self._prods = []

        self._setup()

    def _setup(self):
        """Setup data for the register instance.
        
        Setup the register internal data from packages.
        The data contain all informations needed to make the tool work like each prods, envs, blueprints and processes.
        Here only the prods and envs are retrieved. To get blueprints, getBlueprints should be called.

        Parameters
        -----------
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        packages = AtUtils.getPackages()

        for prod, packageData in packages.items():
            
            self._data[prod] = {'prod': packageData}
            self._prods.append(prod)
            
            envs = AtUtils.getEnvs(packageData['str'], software=self._software)
            self._data[prod]['envs'] = envs
    
    def getEnvs(self, prod):
        """Return envs stored in the given prod.
        
        This will return list of envs from the given prod. Especially useful to feed a widget.

        Parameters
        -----------
        prod: str
            Prod from which return stored envs.
        verbose: bool
            Define if the function should log informations about its process. (default: False)
        """

        # First, get the prod in data
        _prod = self._data.get(prod, None)
        if prod is None:
            #TODO: Maybe verbsose ? or error ? The prod does not exist.
            return

        # Then, get the env in the precedently queried prod dict.
        _envs = _prod.get('envs', None)
        if prod is None:
            #TODO: Maybe verbsose ?
            return

        return _envs.keys()

    def getBlueprints(self, prod, env, forceReload=False):
        """Get the blueprint object for the given prod and env.
        
        Try to retrieve the blueprints for the specified env in the specified prod. If there is already a blueprints,
        don't re-instanciate them.

        Parameters
        -----------
        prod: str
            Prod from which retrieve the blueprint in the given env.
        env: str
            Env from which get the blueprint object.
        forceReload: bool
            Define if the function should reload its blueprints or not.
        """

        assert prod in self._prods, '"{0}" Are not registered yet in this Register'.format(prod)

        self._prod = prod
        self._env = env
        
        self._blueprints = {}

        # Get the dict for the specified prod in self._data
        _prod = self._data.get(prod, None)
        if _prod is None:
            return {}

        # Get the dict for all envs in self._data[prod]
        _envs = _prod.get('envs', None)
        if _envs is None:
            return {}

        # Get the dict for the specified env in self._data[prod]['envs']
        _env = _envs.get(env, None)
        if _env is None:
            return {}

        # Get the blueprint in self._data[prod]['envs'][env]. If one is found, return it.  #TODO: It seems there is an error
        _blueprints = _env.get('blueprints', None)
        if _blueprints is not None and not forceReload:
            return _blueprints['objects']

        # Get the env module to retrieve the blueprint from.
        _envModule = _env.get('module', None)
        if _envModule is None:
            
            # Get the string path to the env package in self._data[prod]['envs'][env]['str']
            _envStr = _env.get('str', None)
            if _envStr is None:
                return {}

            # Load the env module from the string path stored.
            _envModule = AtUtils.importFromStr('{}.{}'.format(_envStr, _env), verbose=self.verbose)
            if _envModule is None:
                return {}
            _env['module'] = _envModule
        self._module = _envModule

        # If force reload are enabled, this will reload the env module.
        if forceReload:
            reload(_envModule)  #TODO: Maybe do this only in dev mode !

        # Try to access the `blueprints` variable in the env module
        _blueprints = getattr(_envModule, 'blueprints', {})

        # Generate a blueprint object for each process retrieved in the `blueprint` variable of the env module.
        for i in range(len(_blueprints)):
            self._blueprints[i] = Blueprint(blueprint=_blueprints[i], verbose=self.verbose)
        
        batchLinkResolveBlueprints = {blueprintIndex: blueprintObject for blueprintIndex, blueprintObject in self._blueprints.items() if blueprintObject.inBatch}
        for blueprint in self._blueprints.values():
            blueprint.resolveLinks(batchLinkResolveBlueprints, check=Link.CHECK, fix=Link.FIX, tool=Link.TOOL)

        # Finally store blueprints in the env dict in data.
        _env['blueprints'] = {'data': _blueprints,
                              'objects': self._blueprints} #TODO: These data seems to not be used.

        return self._blueprints

    def reloadBlueprintsModules(self):

        modules = list(set([blueprint.module for blueprint in  self._blueprints.values()]))

        for module in modules:
            reload(module)

        return modules

    def getData(self, data):

        if not self._prod or not self._env:
            return None
        return self._data[self._prod]['envs'][self._env].get(data, None)

    def setData(self, key, data):

        assert key not in ('data', 'objects'), 'Key "" is already used by the register for built-in data.'.format(key)

        self._data[self._prod]['envs'][self._env][key] = data

    def setVerbose(value):

        self.verbose = value


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
        self.processStr = self.blueprint.get('process', None)
        self.category = self.blueprint.get('category', 'Other')

        _initArgs, _initKwargs = self.getArguments('__init__')
        self.module = None
        self.process = self.getProcess(_initArgs, _initKwargs)

        self.links = {'check': [], 'fix': []}

        self.name = AtUtils.camelCaseSplit(self.process._name)
        self.docstring = self.createDocstring()

        self._check = None
        self._fix = None
        self._tool = None

        self.isOptional = False
        self.isNonBlocking = False
        self.isDependant = False
        self.inUi = True
        self.inBatch = True

        self.isCheckable = False
        self.isFixable = False
        self.hasTool = False

        # setupCore will automatically retrieve the method needed to execute the process. 
        # And also the base variable necessary to define if theses methods are available.
        self.setupCore()
        self.setupTags()

    def __repr__(self):

        return "<{0} '{1}' object at {2}'>".format(self.__class__.__name__, self.process.__class__.__name__, hex(id(self)))

    ## --- Methods to execute Process Methods -- ##
    def check(self, links=True):
        """This is a wrapper for the process check that will automatically execute it with the right parameters.

        Returns
        -------
        type
            The value returned by the check.
        bool
            True if the check return an error, False otherwise.
        """

        if self._check is None:
            return None, None
        
        args, kwargs = self.getArguments(self._check.__name__)
        returnValue = self._check(*args, **kwargs)

        result = self.filterResult(self.process._feedback)

        if links:
            self.runLinks('check')  #FIXME: Links seems to be launched in batch even if they are UI_ONLY.
        
        return result, bool(result)

    def fix(self, links=True):
        """This is a wrapper for the process fix that will automatically execute it with the right parameters.

        Returns
        -------
        type
            The value returned by the fix.
        """

        if self._fix is None:
            return None

        args, kwargs = self.getArguments(self._fix.__name__)
        result = self._fix(*args, **kwargs)

        if links:
            self.runLinks('fix')

        return result

    def tool(self, links=True):
        """This is a wrapper for the process tool that will automatically execute it with the right parameters.

        Returns
        -------
        type
            The value returned by the tool method.
        """

        if self._tool is None:
            return

        args, kwargs = self.getArguments(self._tool.__name__)
        result = self._tool(*args, **kwargs)

        if links:
            self.runLinks('tool')

        return result

    def runLinks(self, which):

        links = self.links[which]

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
        kwargs: list
            dict of all kwargs expected by the process __init__ method.

        Returns
        -------
        object
            An instance of the process class.
        """

        if self.processStr is None:
            raise RuntimeError() #TODO Add an error message here

        moduleStr, _, processStr = self.processStr.rpartition('.')
        self.module = AtUtils.importFromStr(moduleStr)
        if self.module is None:
            raise RuntimeError('Can not import module {0}'.format(moduleStr))

        processClass = getattr(self.module, processStr)

        return processClass(*args, **kwargs)

    def setupCore(self):
        """Setup the all data for the wrapping method (check, fix...) and bool to know if isCheckable, isFixable...

        Retrieve all overridden methods and set the instance attributes with the retrieved data.

        Parameters
        ----------
        args: list
            List of all args expected by the process __init__ method.
        kwargs: list
            dict of all kwargs expected by the process __init__ method.
        """
        
        overriddenMethods = AtUtils.getOverriddenMethods(self.process.__class__, Process)

        if overriddenMethods.get('check', False):
            self.isCheckable = True
            self._check = self.process.check

        if overriddenMethods.get('fix', False):
            self.isFixable = True
            self._fix = self.process.fix

        if overriddenMethods.get('tool', False):
            self.hasTool = True
            self._tool = self.process.tool

    def setupTags(self):
        """Setup the tags used by this process

        This method will setup the tags from the list given in the env module to affect the process comportment.
        """

        tags = self.blueprint.get('tags', None)
        if tags is None:
            return

        if tags & Tag.NO_CHECK:
            self.isCheckable = False

        if tags & Tag.NO_FIX:
            self.isFixable = False

        if tags & Tag.NO_TOOL:
            self.hasTool = False

        if tags & Tag.OPTIONAL:
            self.isOptional = True
            self.isNonBlocking = True

        if tags & Tag.NON_BLOCKING:
            self.isNonBlocking = True

        if tags & Tag.BATCH_ONLY:
            self.inBatch = True
            self.inUi = False

        if tags & Tag.UI_ONLY:
            self.inUi = True
            self.inBatch = False

    def resolveLinks(self, linkedObjects, check='check', fix='fix', tool='tool'):
        """  """

        self.links = {'check': [], 'fix': [], 'tool': []}

        links = self.blueprint.get('links', None)
        if links is None:
            return

        assert all([hasattr(link, '__iter__') for link in links]), 'Links should be of type tuple(int, str, str)'
        for link in links:
            index, _driver, _driven = link

            # Allow to prevent error when the key does not exist, this could happen when the target is available in ui or batch only.
            if linkedObjects.get(index, None) is None:
                continue

            driven = _driven
            driven = check if _driven == Link.CHECK else driven
            driven = fix if _driven == Link.FIX else driven
            driven = tool if _driven == Link.TOOL else driven

            self.links[_driver].append(getattr(linkedObjects[index], driven))

    def setProgressbar(self, progressbar):
        """ Called in the ui this method allow to give access to the progress bar for the user

        Parameters
        ----------
        progressbar: QProgressBar
            QProgressBar object to connect to the process to display check and fix progression.
        """

        self.process._progressbar = progressbar

    def createDocstring(self):

        docstring = self.process.__doc__ or AtConstants.NO_DOCUMENTATION_AVAILABLE
        docstring += '\n {0} '.format(self.processStr)

        docFormat = {}
        for match in re.finditer(r'\{(\w+)\}', docstring):
            matchStr = match.group(1)
            docFormat[matchStr] = self.process._docFormat_.get(matchStr, '')

        return docstring.format(**docFormat)

    def filterResult(self, result):
        """ Filter the data ouputed by a process to keep only these that is not empty.

        Parameters
        ----------
        result: tuple
            Tuple containing tuple with a str for title and list of errors.
            => tuple(tuple(str, list), ...)

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
    OPTIONAL: str
       This tag will set a check optional, an optional process is not checked by default and will.
    NO_CHECK: str
        This tag will remove the check of a process, it will force the isCheckable to False in blueprint.
    NO_FIX: str
        This tag will remove the fix of a process, it will force the isFixable to False in blueprint.
    NO_TOOL: str
        This tag will remove the tool of a process, it will force the hasTool to False in blueprint.
    DEPENDANT: str
        A dependent process need links to be run through another process.
    NON_BLOCKING: str
        A non blocking process will raise a non blocking error (orange), its error is ignored.
    BACTH_ONLY: str
        This process will not be run in ui but only in batch mode.
    UI_ONLY: str
        This process will not be executed outside ui.

    """

    NO_CHECK        = 1
    NO_FIX          = 2
    NO_TOOL         = 4
    NON_BLOCKING    = 8
    OPTIONAL        = 16
    BATCH_ONLY      = 32
    UI_ONLY         = 64
    
    DEPENDANT       = NO_CHECK | NO_FIX | NO_TOOL


#TODO: Implement this functionality.
class Link(object):

    CHECK = 'check'
    FIX = 'fix'
    TOOL = 'tool'

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
        overrided_method = AtUtils.getOverriddenMethods(processClass, Process)

        print overrided_method

        # if '__init__' in overrided_method:
        #     print '__init__ for ' + str(processClass)
        #     __process.__init__()

        # if 'check' in overrided_method:
        #     print 'check for ' + str(processClass)
        #     __process.check()

        # if 'fix' in overrided_method:
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