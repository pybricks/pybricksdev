subB__importA__foo = 'bar' # subB.importA#1
subB__importA__foo2 = subB__importA__foo + 'x' # subB.importA#2
importB__bar = 'bar2' # importB#1
importB__flab = 'float' # importB#2

my_local = 'ggg' # script#4
print(subB__importA__foo) # script#5
print(importB__flab) # script#6
