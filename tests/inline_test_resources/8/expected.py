import os # imb#1

imb__bar = 'bar2' # imb#3
imb__flab = 'float' # imb#4
imb__exported = os.curdir # imb#5

ima__foo = imb__bar # ima#3

print(ima__foo) # script#4
print(imb__flab) # script#5
