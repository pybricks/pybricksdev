print("Hello!")

try:
    hub = MoveHub()
except:
    hub = CPlusHub()

hub.light.on(Color.RED)
wait(2000)
print("World!")
