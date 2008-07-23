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

"""
Test that the --debug=garbage option works.
"""

import TestSCons
import sys
import string
import re
import time

test = TestSCons.TestSCons()

test.write('SConstruct', """
env = Environment()
l = [env]
l.append(l)
""")

test.run(arguments = '-Q --debug=garbage')

lines = string.split(test.stdout(), '\n')[1:]

resz = r' *\d+[.]?\d* +(B|KB|MB|GB|TB) *'

pheader = re.compile(r'id +size +type +representation')
pinst = re.compile(r'0x[\d,a-f]{8} +\d+ +[\w,.]+')
psum = re.compile(r'Garbage: +\d+ collected objects \( *\d+ in cycles\): *%s' % resz)

test.fail_test(pheader.match(lines[0]) is None)
test.fail_test(psum.match(lines[-2]) is None)
for line in lines[1:-2]:
    test.fail_test(pinst.match(line) is None)
    test.fail_test(len(line) >= 80)

garbage = test.workpath('garbage.txt')

test.run(arguments = '-Q --debug=garbage --garbage %s' % garbage)
lines = string.split(test.stdout(), '\n')

pfile = 'Garbage reference graph saved to: %s' % garbage
test.fail_test(lines[1] != pfile)
test.fail_test(psum.match(lines[2]) is None)

test.run(arguments = '-Q --garbage %s' % garbage)
test.fail_test(string.split(test.stdout(), '\n')[1] != '')

test.pass_test()


