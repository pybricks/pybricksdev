class UsesConstants:

    def foo(self):
        return HasConstants(HasConstants.DRIVE)


class HasConstants:
    DRIVE = 0
    TURN = 1

    def __init__(self, x):
        self.x = x
