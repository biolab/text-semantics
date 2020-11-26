# prefix components:
space = '    '
branch = '│   '
# pointers:
tee = '├── '
last = '└── '


def print_onto_tree(class_, world, prefix: str = ''):
    """A recursive generator, given a directory Path object
    will yield a visual tree structure line by line
    with each line prefixed by the same characters
    """
    classes_ = list(class_.subclasses(world=world))
    # contents each get pointers that are ├── with a final └── :
    pointers = [tee] * (len(classes_) - 1) + [last]
    for pointer, cl in zip(pointers, classes_):
        print(prefix + pointer + cl.name)
        extension = branch if pointer == tee else space
        # i.e. space because last, └── , above so no more |
        print_onto_tree(cl, world, prefix=prefix+extension)