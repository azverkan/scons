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

import SCons.Node.FS

# Set of file names that are automatically distributed.
auto_dist = ("INSTALL", "NEWS", "README", "AUTHORS", "ChangeLog", "THANKS", "HACKING", "COPYING")

# Pasted from Philip Scholl's packaging extension, until it is merged
def FindSourceFiles(env, target=None, source=None ):
    """ returns a list of all children of the target nodes, which have no
    children. This selects all leaves of the DAG that gets build by SCons for
    handling dependencies.
    """
    if target==None: target = '.'

    nodes = env.arg2nodes(target, env.fs.Entry)

    sources = []
    def build_source(ss):
        for s in ss:
            if s.__class__==SCons.Node.FS.Dir:
                build_source(s.all_children())
            elif not s.has_builder() and s.__class__==SCons.Node.FS.File:
                sources.append(s)
            else:
                build_source(s.sources)

    for node in nodes:
        build_source(node.all_children())

    # now strip the build_node from the sources by calling the srcnode
    # function
    def get_final_srcnode(file):
        srcnode = file.srcnode()
        while srcnode != file.srcnode():
            srcnode = file.srcnode()
        return srcnode

    # get the final srcnode for all nodes, this means stripping any
    # attached build node.
    map( get_final_srcnode, sources )

    # remove duplicates
    return list(set(sources))

class DirectoryHierarchy:
    """Installation directory hierarchy.
    """
    def __init__(self, **kw):

        # Standard hierarchy
        self.prefix = "/usr/local"
        self.dataroot = "${DIR.prefix}/share"
        self.data = "${DIR.dataroot}"
        self.pkgdata = "${DIR.data}/${NAME}" # not required by standard, Automake-specific
        self.doc = "${DIR.dataroot}/doc/${NAME}"
        self.html = dvi = ps = pdf = "${DIR.doc}"
        self.info = "${DIR.dataroot}/info"
        self.lisp = "${DIR.dataroot}/emacs/site-lisp"
        self.locale = "${DIR.dataroot}/locale"
        self.man = "${DIR.dataroot}/man"
        self.man1 = "${DIR.man}/man1"
        self.man2 = "${DIR.man}/man2"
        self.man3 = "${DIR.man}/man3"
        self.man4 = "${DIR.man}/man4"
        self.man5 = "${DIR.man}/man5"
        self.man6 = "${DIR.man}/man6"
        self.man7 = "${DIR.man}/man7"
        self.man8 = "${DIR.man}/man8"
        self.man9 = "${DIR.man}/man9"
        self.manl = "${DIR.man}/manl"
        self.mann = "${DIR.man}/mann"
        self.sysconf = "${DIR.prefix}/etc"
        self.sharedstate = "${DIR.prefix}/com" # most distros set it to /var/lib
        self.pkgsharedstate = "${DIR.sharedstate}/${NAME}" # not required by standard
        self.localstate = "${DIR.prefix}/var"
        self.pkglocalstate = "${DIR.localstate}/${NAME}" # not required by standard
        self.include = "${DIR.prefix}/include"
        self.pkginclude = "${DIR.include}/${NAME}" # not required by standard, Automake-specific
        self.exec_prefix = "${DIR.prefix}"
        self.bin = "${DIR.exec_prefix}/bin"
        self.sbin = "${DIR.exec_prefix}/sbin"
        self.libexec = "${DIR.exec_prefix}/libexec"
        self.pkglibexec = "${DIR.libexec}/${NAME}" # not required by standard
        self.lib = "${DIR.exec_prefix}/lib"
        self.pkglib = "${DIR.exec_prefix}/lib/${NAME}" # not required by standard, Automake-specific
        self.oldinclude = "/usr/include"
        self.pkgoldinclude = "${DIR.oldinclude}/${NAME}" # not required by standard

        # Override from keyword arguments.
        self.__dict__.update(kw)

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
        self.distribution_roots = []

        self['DIR'] = DirectoryHierarchy()

        # Automatically include recognized files.
        for filename in auto_dist:
            if os.path.exists(filename):
                self.distribution.extend(self.arg2nodes([filename]))

    def finish(self):
        for node in self.distribution_roots:
            self.distribution.extend(FindSourceFiles(self.env, node))
        print self['NAME'], 'would distribute:', ', '.join(str(a) for a in self.distribution)

    def Distribute(self, *args):
        nodes = []
        for arg in args:
            nodes.extend(self.arg2nodes(arg))
        self.distribution.extend(nodes)
        return nodes

    def Build(self, *nodes):
        print "Would build:", nodes
        self.distribution_roots.extend(nodes)
        return nodes

    def Test(self, *nodes):
        print "Would test:", nodes
        self.distribution_roots.extend(nodes)
        return nodes

    def AutoInstall(self, *nodes, **kwargs):
        print "Would autoinstall:", [str(node) for node in nodes], kwargs
        self.distribution_roots.extend(nodes)
        return nodes
