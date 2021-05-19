import importB

importB.func1('foo')


def func2(param):
    print(importB.func1(param))
    print('ho')
    Class1().myfunc('y')


class Class1:
    def __init__(self):
        self.myvar = importB.Class1().myvar

    def myfunc(self, p2):
        print(self.myvar)
        func2('x')
