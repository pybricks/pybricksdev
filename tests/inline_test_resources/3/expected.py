def importB_func1(param): # importB#0
    print('hi') # importB#1
    print('ho') # importB#2


class importB_Class1: # importB#5
    def __init__(self): # importB#6
        self.myvar = 'foo' # importB#7
        pass # importB#8

importB_func1('foo') # importA#2


def importA_func2(param): # importA#5
    print(importB_func1(param)) # importA#6
    print('ho') # importA#7
    importA_Class1().myfunc('y') # importA#8


class importA_Class1: # importA#11
    def __init__(self): # importA#12
        self.myvar = importB_Class1().myvar # importA#13

    def myfunc(self, p2): # importA#15
        print(self.myvar) # importA#16
        importA_func2('x') # importA#17

print(importA_func2('x')) # script#2
print(importA_Class1().myvar) # script#3
# expect the following line to be unchanged, because importB isn't imported here # script#4
print(importB.func1('x')) # script#5
