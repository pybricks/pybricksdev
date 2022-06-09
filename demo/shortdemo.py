from pybricks.tools import wait

from dep1 import *
from dep2 import data2

print("Hello", data1)
wait(1000)
print("World!", data2)

# Force error with correct line number
1 / 0
