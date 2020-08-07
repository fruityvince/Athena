"""
          _   _                      
     /\  | | | |                     
    /  \ | |_| |__   ___ _ __   __ _ 
   / /\ \| __| '_ \ / _ \ '_ \ / _` |
  / ____ \ |_| | | |  __/ | | | (_| |
 /_/    \_\__|_| |_|\___|_| |_|\__,_|
"""

import sys

from Athena.AtGui import AtUi
from Athena import AtCore, AtUtils, AtConstants

__version__ = AtConstants.VERSION

def launch(context=None, env=None, displayMode='Blueprint', dev=False, verbose=False):
    """ Main function to launch the tool. """

    # if dev:
    #     forceReload()

    window = AtUi.Athena(context=context, env=env, displayMode=displayMode, dev=dev, verbose=verbose)
    window.show()

    return window

def batch(context, env, dev=False, verbose=False):
    """ Used to run blueprintes without any AtUi """

    # if dev:
    #     forceReload()

    register = AtCore.Register(verbose=verbose)
    blueprints = register.getBlueprints(context, env)

    traceback = []
    toFix = []
    for blueprint in blueprints:

        if not blueprint._isCheckable or blueprint._isNonBlocking or not blueprint._inBatch:
            continue

        try:
            result, state = blueprint.check()
            if state:
                toFix.append(blueprint)

        except Exception as exception:
            pass  #TODO: Raise an error

    for blueprint in toFix:
        try:
            blueprint.fix()
            result, state = blueprint.check()
            
            if state:
                traceback.append((blueprint.name, result))

        except Exception as exception:
            pass  #TODO: Raise an error

    if traceback:
        log = "\nErrors found during execution of {0}'s {1} blueprints:\n".format(context, env)
        log += '-'*len(log) + '\n'

        for blueprintName, result in traceback:
            log += '\n\t{0}:'.format(blueprintName)

            for each in result:
                log += '\n\t\t- {0}:'.format(each['title'])
                log += '\n\t\t\t{0}'.format(each['toDisplay'])
        
        if verbose: print(log)
        return False
    return True

def safeReload():

    # reloading the core cause issue since the base class is reloaded but not the classes that inherits it 
    # (All user defined blueprints) see more: http://stackoverflow.com/questions/9722343
    _legacyProcess = AtCore.Process
    reload(AtCore)
    AtCore.Process = _legacyProcess
    
    reload(AtUtils)
    reload(AtUi)
    reload(AtConstants)

def __reload(verbose=False):
    """This hidden method is meant to reload all Athena related packages, especially to work on the tool core.

    It should not be used by artist and dev that work on processes. It should only be used to work on the API and 
    everything related to this package.

    .. notes:: 
        Athena loads some modules that contains processes that are subprocess of AtCore.Process. But when this base class is reloaded 
        and not the subclass weird things can happen because we now get two different version of the same class and AtCore.Process can 
        become different to AtCore.Process.
        So the solution is to reload the baseClass and then the process classes to use the same version. This code will clean 
        all Athena related modules in the sys.modules() except submodules that will be reloaded.

    >>># This must be used before reloading Athena
    >>>Athena.__reload()
    >>>import Athena
    >>>reload(Athena)
    """

    atPackages = [package['import'] for package in AtUtils.getPackages().values()]

    toReload = {}
    toDelete = {}
    for moduleName, module in sys.modules.items():
        if AtConstants.PROGRAM_NAME not in moduleName:
            continue

        # Some name contains modules that are None. We prefer to get rid of them.
        if module is None:
            toDelete[moduleName] = module
            continue
        
        # We iterate over the Athena packages (packages containing processes) to know thoses that will ne to be reimported after.
        # If it does not match any of them, we only remove the package from sys.modules().
        for package in atPackages:
            if moduleName.startswith(package):
                toDelete[moduleName] = module
                toReload[moduleName] = module
                break                
        else:
            toDelete[moduleName] = module

    for moduleName, module in toDelete.items():
        sys.modules.pop(moduleName)
        del module
        print('Remove {}'.format(moduleName))

    # Last, we reimport all Athena packages to make sure the API will detect it.
    for moduleName in sorted(toReload.keys(), key=lambda x: x.count('.')):
        AtUtils.importFromStr(moduleName)
        print('Reload {}'.format(moduleName))


if __name__ == '__main__':
    launch(dev=True)