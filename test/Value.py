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

import os
import re
import string
import sys
import TestSCons
import TestCmd

test = TestSCons.TestSCons(match=TestCmd.match_re)

# Run all of the tests with both types of source signature
# to make sure there's no difference in behavior.
for source_signature in ['MD5', 'timestamp']:

    print "Testing Value node with source signatures:", source_signature

    test.write('SConstruct', """
SourceSignatures(r'%(source_signature)s')

class Custom:
    def __init__(self, value):  self.value = value
    def __str__(self):          return "C=" + str(self.value)

P = ARGUMENTS.get('prefix', '/usr/local')
L = len(P)
C = Custom(P)

def create(target, source, env):
    open(str(target[0]), 'wb').write(source[0].get_contents())

env = Environment()
env['BUILDERS']['B'] = Builder(action = create)
env['BUILDERS']['S'] = Builder(action = "%(python)s put $SOURCES into $TARGET")
env.B('f1.out', Value(P))
env.B('f2.out', env.Value(L))
env.B('f3.out', Value(C))
env.S('f4.out', Value(L))
""" % {'source_signature':source_signature,
       'python':TestSCons.python})

    test.write('put', """
import os
import string
import sys
open(sys.argv[-1],'wb').write(string.join(sys.argv[1:-2]))
""")

    test.run(arguments='-c')
    test.run()

    out1 = """create(["f1.out"], ["'/usr/local'"])"""
    out2 = """create(["f2.out"], ["10"])"""
    out3 = """create\\(\\["f3.out"\\], \\["<.*.Custom instance at """
    #" <- unconfuses emacs syntax highlighting
    test.fail_test(string.find(test.stdout(), out1) == -1)
    test.fail_test(string.find(test.stdout(), out2) == -1)
    test.fail_test(re.search(out3, test.stdout()) == None)

    test.must_match('f1.out', "/usr/local")
    test.must_match('f2.out', "10")
    test.must_match('f3.out', "C=/usr/local")
    test.must_match('f4.out', '10')

    test.up_to_date(arguments='.')

    test.run(arguments='prefix=/usr')
    out4 = """create(["f1.out"], ["'/usr'"])"""
    out5 = """create(["f2.out"], ["4"])"""
    out6 = """create\\(\\["f3.out"\\], \\["<.*.Custom instance at """
    #" <- unconfuses emacs syntax highlighting
    test.fail_test(string.find(test.stdout(), out4) == -1)
    test.fail_test(string.find(test.stdout(), out5) == -1)
    test.fail_test(re.search(out6, test.stdout()) == None)

    test.must_match('f1.out', "/usr")
    test.must_match('f2.out', "4")
    test.must_match('f3.out', "C=/usr")
    test.must_match('f4.out', '4')

    test.up_to_date('prefix=/usr', '.')

    test.unlink('f3.out')

    test.run(arguments='prefix=/var')
    out4 = """create(["f1.out"], ["'/var'"])"""

    test.fail_test(string.find(test.stdout(), out4) == -1)
    test.fail_test(string.find(test.stdout(), out5) != -1)
    test.fail_test(re.search(out6, test.stdout()) == None)

    test.up_to_date('prefix=/var', '.')

    test.must_match('f1.out', "/var")
    test.must_match('f2.out', "4")
    test.must_match('f3.out', "C=/var")
    test.must_match('f4.out', "4")

test.pass_test()
