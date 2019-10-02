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

def launch(prod=None, env=None, displayMode='Blueprint', dev=False, verbose=False):
    """ Main function to launch the tool. """

    if dev:
        safeReload()

    window = AtUi.Athena(prod=prod, env=env, displayMode=displayMode, dev=dev, verbose=verbose)
    window.show()

    return window

def batch(prod, env, dev=False, verbose=False):
    """ Used to run processes without any AtUi """

    if dev:
        safeReload()

    register = AtCore.Register(verbose=verbose)
    blueprint = register.getBlueprints(prod, env)

    traceback = []
    toFix = []
    for process in blueprint.itervalues():

        if not process.isCheckable or process.isNonBlocking or not process.inBatch:
            continue

        try:
            result, state = process.check()
            if state:
                toFix.append(process)

        except Exception as exception:
            pass  #TODO: Raise an error

    for process in toFix:
        try:
            process.fix()
            result, state = process.check()
            
            if state:
                traceback.append((process.name, result))

        except Exception as exception:
            pass  #TODO: Raise an error

    if traceback:
        log = "\nErrors found during execution of {0}'s {1} processes:\n".format(prod, env)
        log += '-'*len(log) + '\n'

        for processName, result in traceback:
            log += '\n\t{0}:'.format(processName)

            for each in result:
                log += '\n\t\t- {0}:'.format(each['title'])
                log += '\n\t\t\t{0}'.format(each['toDisplay'])
        
        if verbose: print(log)
        return False
    return True

def safeReload():

    # reloading the core cause issue since the base class is reloaded
    # but not the classes that inherits it (All user defined processes)
    # http://stackoverflow.com/questions/9722343
    _legacyProcess = AtCore.Process
    reload(AtCore)
    AtCore.Process = _legacyProcess
    
    reload(AtUtils)
    reload(AtUi)
    reload(AtConstants)
