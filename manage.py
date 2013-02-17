#!/usr/bin/env python

from everblag import run, db


def example(name='world'):
    """
    An example CLI function.

    Any function defined in this module is available to be called via
    'manage.py <name> <args ...>'. Ex 'manage.py example John'. The first line
    of the doc comment is used to form the usage text.

    The remainder of the doc comment is only shown if a command is misused
    specifically.
    """

    print 'Hello, %s!' % name


def runserver():
    run()


def createdb():
    db.create_all()

def resetdb():
    db.drop_all()
    db.create_all()


###############################################################################
# Caution: Magic
#
# The following code creates the command line interface to all of the functions
# defined in this module automatically. Do not edit it.

if __name__ == '__main__':
    import inspect
    import sys

    functions = []

    # Get all of the function defined in this module.
    for k in globals().keys():
        f = globals()[k]
        if callable(f):
            try:
                if inspect.getfile(f) == sys.modules[__name__].__file__:
                    functions.append(f)
            except TypeError:
                pass

    # Create the usage dialog. Only prints the first line of the doc comment
    # for usage help. Defined after the call to dir() so it won't show up to
    # users.
    def usage(funcs):
        print "Usage"
        for f in funcs:
            doc = inspect.getdoc(f)
            if doc:
                print "    %s    %-s" % (f.__name__, doc.split('\n')[0])
            else:
                print "    %s" % f.__name__

    # No arguments means show usage.
    if len(sys.argv) == 1:
        usage(functions)
        quit()

    function = [f for f in functions if f.__name__ == sys.argv[1]]

    # If you didn't use an actual function name.
    if not len(function) == 1:
        usage(functions)
        quit()

    f = function[0]

    # Call the specified functions, passing addtional args.
    # try:
    apply(f, sys.argv[2:])
    # except TypeError:
    #     print 'Usage of %s\n%s' % (f.__name__, f.__doc__)
