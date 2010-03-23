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

test = TestSCons.TestSCons()

test.subdir('dir1', 'dir2', 'dir3', 'dir4', 'dir5')

test.write('SConstruct', """
env = Environment()
SConscript('dir1/SConscript')
SConscriptChdir(1)
SConscript('dir2/SConscript')
SConscriptChdir(0)
SConscript('dir3/SConscript')
env.SConscriptChdir(1)
SConscript('dir4/SConscript')
env.SConscriptChdir(0)
SConscript('dir5/SConscript')
""")

test.write(['dir1', 'SConscript'], """
exec(open("create_test.py", 'rU').read())
""")

test.write(['dir2', 'SConscript'], """
exec(open("create_test.py", 'rU').read())
""")

test.write(['dir3', 'SConscript'], """
import os.path
name = os.path.join('dir3', 'create_test.py')
exec(open(name, 'rU').read())
""")

test.write(['dir4', 'SConscript'], """
exec(open("create_test.py", 'rU').read())
""")

test.write(['dir5', 'SConscript'], """
import os.path
name = os.path.join('dir5', 'create_test.py')
exec(open(name, 'rU').read())
""")

for dir in ['dir1', 'dir2', 'dir3','dir4', 'dir5']:
    test.write([dir, 'create_test.py'], r"""
f = open("test.txt", "ab")
f.write("This is the %s test.\n")
f.close()
""" % dir)

test.run(arguments=".", stderr=None)

test.fail_test(test.read(['dir1', 'test.txt']) != "This is the dir1 test.\n")
test.fail_test(test.read(['dir2', 'test.txt']) != "This is the dir2 test.\n")
test.fail_test(test.read('test.txt') != "This is the dir3 test.\nThis is the dir5 test.\n")
test.fail_test(test.read(['dir4', 'test.txt']) != "This is the dir4 test.\n")

test.pass_test()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
