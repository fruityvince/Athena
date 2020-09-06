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
from Athena import AtCore, AtUtils, AtConstants, AtTests

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


def _reload(main='__main__', verbose=False):
    """This hidden method is meant to reload all Athena related packages, especially to work on the tool core.

    It should not be used by artist and dev that work on processes. It should only be used to work on the API and 
    everything related to this package.

    .. notes:: 
        Athena loads some modules that contains processes that are subprocess of AtCore.Process. But when this base class is reloaded 
        and not the subclass weird things can happen because we now get two different version of the same class and AtCore.Process can 
        become different to AtCore.Process.
        So the solution is to reload the baseClass and then the process classes to use the same version. This code will clean 
        all Athena related modules in the sys.modules() except submodules that will be reloaded.

    >>>import Athena
    >>>Athena._reload(__name__)
    """

    import time
    reloadStartTime = time.time()

    # ---------- Keep functions from AtUtils and constant from AtConstants available in local variables ---------- #
    # This function will clean all athena packages in sys.modules but we must keep these functions and constants 
    # available while the function is processing.
    _import = AtUtils.importFromStr
    _reload = AtUtils.reloadModule
    _programName = AtConstants.PROGRAM_NAME

    # ---------- Get which modules must be deleted and which must be reloaded ---------- #
    toDelete = {}
    toReimport = {}
    atPackages = {package['import'] for package in AtUtils.getPackages().values()}
    for moduleName, module in sys.modules.items():
        # Skip all modules in sys.modules if they are not related to Athena and skip Athena main module that will be reloaded after.
        if _programName not in moduleName or moduleName == __name__:
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
                toReimport[moduleName] = module
                break
        else:
            toDelete[moduleName] = module

    # ---------- Delete all Athena modules ---------- #
    # Then we delete all modules that must be deleted. After this, this function is unable to call any of its imported Athena modules.
    for moduleName, module in toDelete.items():
        del sys.modules[moduleName]
        if verbose:
            print('Remove {}'.format(moduleName))

    # ---------- Reload current module if it is not main ---------- #
    # Reload the current module to be sure it will be up to date after. Except if the current module is '__main__'.
    if __name__ != '__main__':
        _reload(sys.modules[__name__])

    # ---------- Reimport all user Athena packages ---------- #
    # Last, we reimport all Athena packages to make sure the API will detect it.
    for moduleName in sorted(toReimport.keys(), key=lambda x: x.count('.')):
        _import(moduleName)
        if verbose:
            print('Reload {}'.format(moduleName))

    # ---------- Restore the reloaded Athena main module in the __main__ module ---------- #
    if __name__ != '__main__':
        # for moduleName in toReimport:
        #     setattr(sys.modules[main], moduleName, sys.modules[moduleName])  #FIXME: We can't update all name in local.
        setattr(sys.modules[main], __name__, sys.modules[__name__])

    # ---------- Display reload time, even if there is no verbose ---------- #
    print('[Reloaded in {:.2f}s]'.format(time.time() - reloadStartTime))


if __name__ == '__main__':
    _reload(__name__)
    sys.modules[__name__].launch(dev=True)