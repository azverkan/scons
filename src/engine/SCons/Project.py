"""SCons.Project

Base class for constructing and managing Projects.  These group and
manage information needed to automate deployment, which is central
concept to Automake compatibility.
"""

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

import os.path

# Set of file names that are automatically distributed.
auto_dist = ("INSTALL", "NEWS", "README", "AUTHORS", "ChangeLog", "THANKS", "HACKING", "COPYING")

class Base:
    """Base class for Project objects

    Final class inherits this class and
    SCons.Environment.SubstitutionEnvironment in Environment.py to
    avoid mutual import.
    """

    def __init__(self):
        """Project-specific initialisation.

        To be run after initializing SubstitutionEnvironment.
        """
        self.distribution = []

        # Automatically include recognized files.
        for filename in auto_dist:
            if os.path.exists(filename):
                self.distribution.extend(self.arg2nodes([filename]))

    def finish(self):
        print self['NAME'], 'would distribute:', ', '.join(str(a) for a in self.distribution)

    def Distribute(self, *args):
        nodes = []
        for arg in args:
            nodes.extend(self.arg2nodes(arg))
        self.distribution.extend(nodes)
        return nodes

    def Build(self, *nodes):
        print "Would build:", nodes
        return nodes

    def Test(self, *nodes):
        print "Would test:", nodes
        return nodes

    def AutoInstall(self, *nodes, **kwargs):
        print "Would autoinstall:", nodes, kwargs
        return nodes
