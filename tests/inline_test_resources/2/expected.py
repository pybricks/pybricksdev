import os # importB#1

importB__bar = 'bar2' # importB#3
importB__flab = 'float' # importB#4
importB__exported = os.curdir # importB#5

importA__foo = importB__bar # importA#3

print(importA__foo) # script#3
# expect the following line to be unchanged, because importB isn't imported here # script#4
print(importB.flab) # script#5
