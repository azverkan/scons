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

import sys
import unittest
import UserDict

import SCons.Environment

from SCons.Tool.project import *

class DummyNode:
    """Simple node work-alike."""
    def __init__(self, name):
        class attrholder: pass
        self.attributes = attrholder()
        self.name = os.path.normpath(name)
    def __str__(self):
        return self.name
    def is_literal(self):
        return 1
    def rfile(self):
        return self
    def get_subst_proxy(self):
        return self

class DummyEnv(UserDict.UserDict):
    pass

class ProjectTestCase(unittest.TestCase):
    "Test Project functionality"

    def test_project(self):
        "Test Project class"
        env = SCons.Environment.Environment()
        prj = Project(env, NAME='test', VERSION='0.1')

        # Does project becomes default project?
        assert find_project() == prj

        prj.Distribute('LICENSE')
        prj.Distribute('README-local', 'LICENSE-local')

        prj.finish([])

        # Check assembling distribution
        distribution = map(str, prj.distribution)
        distribution.sort()
        assert distribution == ['LICENSE', 'LICENSE-local',
                                'README', 'README-local'], \
                                distribution

        # Does project stop being default?
        assert find_project() is None

        alias = env.arg2nodes('install-test')
        children = alias[0].children()
        assert len(children)==2, map(str, children)
        children_names = map(str, children)
        children_names.sort()
        assert children_names == ['install-data-test','install-exec-test'], children_names

if __name__ == "__main__":
    suite = unittest.makeSuite(ProjectTestCase, 'test_')
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        sys.exit(1)

