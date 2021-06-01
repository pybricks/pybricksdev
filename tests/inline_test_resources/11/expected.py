class importA__UsesConstants: # importA#1

    def foo(self): # importA#3
        return importA__HasConstants(importA__HasConstants.DRIVE) # importA#4


class importA__HasConstants: # importA#7
    DRIVE = 0 # importA#8
    TURN = 1 # importA#9

    def __init__(self, x): # importA#11
        self.x = x # importA#12

my_drive = importA__HasConstants(importA__HasConstants.DRIVE) # script#3
