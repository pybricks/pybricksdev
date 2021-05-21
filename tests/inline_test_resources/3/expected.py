def importB__func1(param): # importB#1
    print('hi') # importB#2
    print('ho') # importB#3


class importB__Class1: # importB#6
    def __init__(self): # importB#7
        self.myvar = 'foo' # importB#8

importB__func1('foo') # importA#3


def importA__func2(param): # importA#6
    print(importB__func1(param)) # importA#7
    print('ho') # importA#8
    importA__Class1().myfunc('y') # importA#9


class importA__Class1: # importA#12
    def __init__(self): # importA#13
        self.myvar = importB__Class1().myvar # importA#14

    def myfunc(self, p2): # importA#16
        print(self.myvar) # importA#17
        importA__func2('x') # importA#18

print(importA__func2('x')) # script#3
print(importA__Class1().myvar) # script#4
# expect the following line to be unchanged, because importB isn't imported here # script#5
print(importB.func1('x')) # script#6
