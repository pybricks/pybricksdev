import importA

print(importA.func2('x'))
print(importA.Class1().myvar)
# expect the following line to be unchanged, because importB isn't imported here
print(importB.func1('x'))
