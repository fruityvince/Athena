"""
          _   _                      
     /\  | | | |                     
    /  \ | |_| |__   ___ _ __   __ _ 
   / /\ \| __| '_ \ / _ \ '_ \ / _` |
  / ____ \ |_| | | |  __/ | | | (_| |
 /_/    \_\__|_| |_|\___|_| |_|\__,_|
"""

from Athena.gui import AtUi
from Athena import AtCore, AtUtils, AtConstants

__version__ = AtConstants.VERSION

def launch(context=None, env=None, displayMode='Blueprint', dev=False, verbose=False):
    """ Main function to launch the tool. """

    if dev:
        safeReload()

    window = AtUi.Athena(context=context, env=env, displayMode=displayMode, dev=dev, verbose=verbose)
    window.show()

    return window

def batch(context, env, dev=False, verbose=False):
    """ Used to run blueprintes without any AtUi """

    if dev:
        safeReload()

    register = AtCore.Register(verbose=verbose)
    blueprints = register.getBlueprints(context, env)

    traceback = []
    toFix = []
    for blueprint in blueprints:

        if not blueprint._isCheckable or blueprint._isNonBlocking or not blueprint._inBatch:
            continue

        print blueprint
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
