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
This is basic test for SCons project API.
"""

import os
import TestSCons

test = TestSCons.TestSCons()

tar = test.Environment().WhereIs('tar')
if not tar:
    test.skip_test('tar not found, skipping test.')

test.write('README', """Read me first.""")
test.write('DISTME', """Distribute me too.""")
test.write('t_correct',  'Hello, World!, from hello 1.0.\n')
test.write('test.sh', """#!/bin/sh
set -e
./src/hello > t_actual
diff -s t_actual t_correct""")

test.subdir('src')
test.write(['src', 'main.c'], """
#include <config.h>
#include <stdio.h>

int
main (void)
{
  puts ("Hello, World!, from " PACKAGE_STRING ".");
  return 0;
}
""")

test.write('SConstruct', """
env = Environment(tools=['default','project'])
proj = env.Project('hello', '1.0', 'maciekp@japhy.fnord.org',
               header='config.h')
proj.Distribute('DISTME')
hello = env.Program('src/hello', 'src/main.c')
proj.AutoInstall(hello)
proj.AutoInstall(hello, install='sbin')
proj.AutoInstall(hello, base=False)
proj.Test('test.sh', sources=['t_correct'], command='/bin/sh')
""")

test.run(arguments='dist', stderr=None)
test.must_exist('hello-1.0.tar.gz')

test.run(arguments='all', stderr=None)
test.must_exist('src/hello')
test.run(program=test.workpath('src/hello'), stdout='Hello, World!, from hello 1.0.\n')
test.run(arguments='check')

test.run(arguments='--dir_prefix=_inst/ install', stderr=None)
test.must_exist('_inst/bin/hello')
test.must_exist('_inst/sbin/hello')
test.must_exist('_inst/bin/src/hello')

# test.run(arguments='distcheck', stderr=None)

test.pass_test()
