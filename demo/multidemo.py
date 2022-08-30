from pybricks.hubs import ThisHub
from pybricks.parameters import Color
from pybricks.tools import wait
from .module2 import nice_color

hub = ThisHub()
hub.light.on(Color.RED)
wait(2000)
print("I am", __name__)
hub.light.on(nice_color)
wait(2000)
