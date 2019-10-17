from Athena import AtCore

class OnlyPipedShaders(AtCore.Process):
    """This check is a demo to get name and docstring.
    
    Check:
        Voici le detail du check.
        
    fix:
        Voici le detail du fix.
        
    ui:
        L'ui lance tel script
        
    features:
        - numero 1
        - Have a realtime check
        - tamer
    
    """
    
    def __init__(self):
        pass
        
    def check(self):
        return 'Toto'

    def fix(self):
    	self.camion()

    def camion(self):
        print('camion')


class DemoCheckSG(AtCore.Process):
    """This check is a demo to get name and docstring.
    
    Check:
        Voici le detail du check.
        
    fix:
        Voici le detail du fix.
        
    ui:
        L'ui lance tel script
        
    features:
        - numero 1
        - Have a realtime check
        - tamer
    
    """
    
    def __init__(self):
        pass
        
    def check(self):
        return {'Test': ['1', '2', '3']}

    def tool(self):
        return