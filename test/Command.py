#!/usr/bin/env python
#
# __COPYRIGHT__
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import TestSCons

python = TestSCons.python
_python_ = TestSCons._python_

test = TestSCons.TestSCons()

test.subdir('sub')

test.write('build.py', r"""
import sys
contents = open(sys.argv[2], 'rb').read()
file = open(sys.argv[1], 'wb')
file.write(contents)
file.close()
""")

test.write('SConstruct', """
import os

def buildIt(env, target, source):
    contents = open(str(source[0]), 'rb').read()
    file = open(str(target[0]), 'wb')
    xyzzy = env.get('XYZZY', '')
    if xyzzy:
        file.write(xyzzy + '\\n')
    file.write(contents)
    file.close()
    return 0

def sub(env, target, source):
    target = str(target[0])
    source = str(source[0])
    t = open(target, 'wb')
    for f in sorted(os.listdir(source)):
        t.write(open(os.path.join(source, f), 'rb').read())
    t.close()
    return 0

env = Environment(COPY_THROUGH_TEMP = '%(_python_)s build.py .tmp $SOURCE\\n%(_python_)s build.py $TARGET .tmp',
                  EXPAND = '$COPY_THROUGH_TEMP')
env.Command(target = 'f1.out', source = 'f1.in',
            action = buildIt)
env.Command(target = 'f2.out', source = 'f2.in',
            action = r'%(_python_)s build.py temp2 $SOURCES' + '\\n' + r'%(_python_)s build.py $TARGET temp2')
env.Command(target = 'f3.out', source = 'f3.in',
            action = [ [ r'%(python)s', 'build.py', 'temp3', '$SOURCES' ],
                       [ r'%(python)s', 'build.py', '$TARGET', 'temp3'] ])
Command(target = 'f4.out', source = 'sub', action = sub)
env.Command(target = 'f5.out', source = 'f5.in', action = buildIt,
            XYZZY='XYZZY is set')
Command(target = 'f6.out', source = 'f6.in',
        action = r'%(_python_)s build.py f6.out f6.in')
env.Command(target = 'f7.out', source = 'f7.in',
            action = r'%(_python_)s build.py $TARGET $SOURCE')
Command(target = 'f8.out', source = 'f8.in',
        action = r'%(_python_)s build.py $TARGET $SOURCE')
env.Command(target = 'f9.out', source = 'f9.in',
            action = r'$EXPAND')
env.Command(target = '${F10}.out', source = '${F10}.in',
            action = r'%(_python_)s build.py $TARGET $SOURCE',
            F10 = 'f10')
""" % locals())

test.write('f1.in', "f1.in\n")
test.write('f2.in', "f2.in\n")
test.write('f3.in', "f3.in\n")
test.write(['sub', 'f4a'], "sub/f4a\n")
test.write(['sub', 'f4b'], "sub/f4b\n")
test.write(['sub', 'f4c'], "sub/f4c\n")
test.write('f5.in', "f5.in\n")
test.write('f6.in', "f6.in\n")
test.write('f7.in', "f7.in\n")
test.write('f8.in', "f8.in\n")
test.write('f9.in', "f9.in\n")
test.write('f10.in', "f10.in\n")

test.run(arguments = '.')

test.must_match('f1.out', "f1.in\n")
test.must_match('f2.out', "f2.in\n")
test.must_match('f3.out', "f3.in\n")
test.must_match('f4.out', "sub/f4a\nsub/f4b\nsub/f4c\n")
test.must_match('f5.out', "XYZZY is set\nf5.in\n")
test.must_match('f6.out', "f6.in\n")
test.must_match('f7.out', "f7.in\n")
test.must_match('f8.out', "f8.in\n")
test.must_match('f9.out', "f9.in\n")
test.must_match('f10.out', "f10.in\n")

test.pass_test()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
