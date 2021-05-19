import os # importB#0

importB_bar = 'bar2' # importB#2
importB_flab = 'float' # importB#3
importB_exported = os.curdir # importB#4

importA_foo = importB_bar # importA#2

print(importA_foo) # script#3
print(importB_flab) # script#4
