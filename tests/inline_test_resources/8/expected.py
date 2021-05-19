import os # imb#0

imb_bar = 'bar2' # imb#2
imb_flab = 'float' # imb#3
imb_exported = os.curdir # imb#4

ima_foo = imb_bar # ima#2

print(ima_foo) # script#3
print(imb_flab) # script#4
