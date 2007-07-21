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
import SCons.Tool.packaging

# Set of file names that are automatically distributed.
auto_dist = ("INSTALL", "NEWS", "README", "AUTHORS", "ChangeLog", "THANKS", "HACKING", "COPYING")

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

        self.__arch_dependent = ['exec_prefix', 'bin', 'sbin', 'libexec', 'pkglibexec', 'lib', 'pkglib']

        # Override from keyword arguments.
        self.__dict__.update(kw)

    def is_arch_dependent(self, name):
        return name in self.__arch_dependent

    def defineDirectory(self, name, directory, arch_dependent=False):
        self.setattr(name, directory)
        if arch_dependent:
            self.__arch_dependent.append(name)

_all_projects = []
def finish_all(sconscripts=()):
    for proj in _all_projects:
        proj.finish(sconscripts=sconscripts)

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
        if not 'packaging' in self.env['TOOLS']:
            self.env.Tool('packaging')

        _all_projects.append(self)
        self.finished = False

        self.distribution = []
        self.distribution_roots = []

        self['DIR'] = DirectoryHierarchy()
        if not self.has_key('shortname'):
            self['shortname'] = self['NAME']

        if self.has_key('header'):
            if SCons.Util.is_Sequence(self['header']):
                apply(self.Header, self['header'])
            else:
                self.Header(self['header'])

        # Automatically include recognized files.
        for filename in auto_dist:
            f = self.env.File(filename)
            if f.rexists():
                self.distribution.append(f)

        def my_alias(alias): return '%s-%s' % (alias, self['NAME'])
        for alias in ('all', 'dist', 'check', 'distcheck',
                      'install-data', 'install-exec', 'install-init'):
            self.env.Alias(my_alias(alias))
            self.env.Alias(alias, my_alias(alias))

        self.env.Alias('install','install-data')
        self.env.Alias('install','install-exec')
        self.env.Alias('install','install-init') # FIXME

        self.env.Alias(my_alias('install'), my_alias('install-data'))
        self.env.Alias(my_alias('install'), my_alias('install-exec'))
        self.env.Alias(my_alias('install'), my_alias('install-init')) # FIXME

    # Wrappers
    def Header(self, header=None, lang=None):
        if header is None:
            return self['header']
        if not isinstance(header, SCons.Header.HeaderFile):
            header = self.env.Header(header, lang)
        self['header'] = header

        # Default header contents
        header.Template('PACKAGE', 'Name of package', self['NAME'])
        header.Template('VERSION', 'Version number of package', self['VERSION'])
        header.Template('PACKAGE_NAME', 'Define to the full name of this package.', self['NAME'])
        header.Template('PACKAGE_TARNAME', 'Define to one symbol short name of this package.  (Automake compatibility definition)', self.get('shortname'))
        header.Template('PACKAGE_SHORT_NAME', 'Define to one symbol short name of this package.', self.get('shortname'))
        header.Template('PACKAGE_VERSION', 'Define to the version of this package.', self['VERSION'])
        header.Template('PACKAGE_STRING', 'Define to the full name and version of this package.', '%s %s' % (self['NAME'], self['VERSION']))
        header.Template('PACKAGE_BUGREPORT', 'Define to the address where bug reports for this package should be sent.', self.get('BUGREPORT'))

        if header.language == 'C':
            self.env.Append(CPPPATH=header.node.get_dir())

    # Internal API
    def finish(self, sconscripts=()):
        if self.finished: return

        apply(self.Distribute, sconscripts)
        for node in self.distribution_roots:
            self.distribution.extend(self.env.FindSourceFiles(node))

        pkg_kw = dict(self.items())
        pkg_kw['PACKATE_TYPE'] = 'targz'
        
        package = apply(self.env.Package, (self.distribution,), pkg_kw)
        self.env.Alias('dist-'+self['NAME'], package)

        self.finished = True

    # Entry points
    def Distribute(self, *args):
        nodes = []
        for arg in args:
            nodes.extend(self.arg2nodes(arg))
        self.distribution.extend(nodes)
        return nodes

    def Attach(self, *nodes):
        print "Attached:", nodes
        self.distribution_roots.extend(nodes)
        return nodes

    def Test(self, *nodes):
        print "Would test:", nodes
        self.distribution_roots.extend(nodes)
        return nodes

    __default_autoinstall_keywords = dict(executable = False,
                                          arch_dependent = False,
                                          machine_specific = False,
                                          writable = False)
    def __autoinstall_node(self, node, **kwargs):
        kw = self.__default_autoinstall_keywords.copy()
        kw.update(self.env.get('autoinstall_keywords', {}))
        kw.update(self.get('autoinstall_keywords', {}))
        kw.update(getattr(node.attributes, 'autoinstall_keywords', {}))
        kw.update(node.env.get('autoinstall_keywords', {}))
        kw.update(kwargs)

        try: install = kw['install']
        except KeyError:
            if kw.get('writable'):
                if kw.get('machine_specific') or kw.get('arch_dependent'):
                    install = 'pkglocalstate'
                else:
                    install = 'pkgsharedstate'
            elif kw.get('machine_specific'):
                install = 'sysconf'
            elif kw.get('arch_dependent'):
                install = 'pkglib'
            else:
                install = 'pkgdata'

        tdir = self.subst(install)
        arch_dependent = kw.get('arch_dependent', self['DIR'].is_arch_dependent(tdir))
        if not os.path.isabs(tdir):
            tdir = self.subst(getattr(self['DIR'], tdir))

        t = self.env.Install(tdir, node)
        if arch_dependent:
            self.env.Alias('install-exec-'+self['NAME'], t)
        else:
            self.env.Alias('install-data-'+self['NAME'], t)

        return node

    def AutoInstall(self, *nodes, **kwargs):
        returned_nodes = []
        for node in SCons.Util.flatten(nodes):
            returned_nodes.append(
                apply(self.__autoinstall_node, (node,), kwargs))

        self.env.Alias('all-'+self['NAME'], returned_nodes)
        self.distribution_roots.extend(returned_nodes)
        return returned_nodes
