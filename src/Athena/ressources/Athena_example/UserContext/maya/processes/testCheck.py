from Athena import AtCore


class TestForSanityCheck(AtCore.Process):
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
    
    NAME = 'TestDeProcess NAME'

    def __init__(self):
        pass
        
    def check(self):
        print self.NAME, 'check'
        print '#'*100


class BestCheckEver(AtCore.Process):
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
        print self.NAME, 'check'
        return 'BestCheckEver'

    def fix(self):
    	print self.NAME, 'fix'