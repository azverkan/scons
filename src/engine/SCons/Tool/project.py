"""SCons.Tool.project

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
import sys
from distutils import sysconfig

import SCons.Node.FS
import SCons.Script.Main
import SCons.Tool.header
import SCons.Tool.packaging

# Set of file names that are automatically distributed.
auto_dist = ("INSTALL", "NEWS", "README", "AUTHORS", "ChangeLog", "THANKS", "HACKING", "COPYING")

_standard_directory_hierarchy = {
    'prefix' : "/usr/local",
    'dataroot' : "${DIR.prefix}/share",
    'data' : "${DIR.dataroot}",
    'pkgdata' : "${DIR.data}/${NAME}", # not required by standard, Automake-specific
    'doc' : "${DIR.dataroot}/doc/${NAME}",
    'html' : "${DIR.doc}",
    'dvi' : "${DIR.doc}",
    'ps' : "${DIR.doc}",
    'pdf' : "${DIR.doc}",
    'info' : "${DIR.dataroot}/info",
    'lisp' : "${DIR.dataroot}/emacs/site-lisp",
    'locale' : "${DIR.dataroot}/locale",
    'man' : "${DIR.dataroot}/man",
    'man1' : "${DIR.man}/man1",
    'man2' : "${DIR.man}/man2",
    'man3' : "${DIR.man}/man3",
    'man4' : "${DIR.man}/man4",
    'man5' : "${DIR.man}/man5",
    'man6' : "${DIR.man}/man6",
    'man7' : "${DIR.man}/man7",
    'man8' : "${DIR.man}/man8",
    'man9' : "${DIR.man}/man9",
    'manl' : "${DIR.man}/manl",
    'mann' : "${DIR.man}/mann",
    'sysconf' : "${DIR.prefix}/etc",
    'sharedstate' : "${DIR.prefix}/com", # most distros set it to /var/lib
    'pkgsharedstate' : "${DIR.sharedstate}/${NAME}", # not required by standard
    'localstate' : "${DIR.prefix}/var",
    'pkglocalstate' : "${DIR.localstate}/${NAME}", # not required by standard
    'include' : "${DIR.prefix}/include",
    'pkginclude' : "${DIR.include}/${NAME}", # not required by standard, Automake-specific
    'exec_prefix' : "${DIR.prefix}",
    'bin' : "${DIR.exec_prefix}/bin",
    'sbin' : "${DIR.exec_prefix}/sbin",
    'libexec' : "${DIR.exec_prefix}/libexec",
    'pkglibexec' : "${DIR.libexec}/${NAME}", # not required by standard
    'lib' : "${DIR.exec_prefix}/lib",
    'pkglib' : "${DIR.exec_prefix}/lib/${NAME}", # not required by standard, Automake-specific
    'oldinclude' : "/usr/include",
    'pkgoldinclude' : "${DIR.oldinclude}/${NAME}", # not required by standard
    'python' : sysconfig.get_python_lib(0,0,prefix=sys.prefix) # not required by standard,
}

_default_arch_dependent = (
    'exec_prefix', 'bin', 'sbin', 'libexec', 'pkglibexec', 'lib', 'pkglib'
    )

class DirectoryHierarchy:
    """Installation directory hierarchy.
    """
    def __init__(self, **kw):
        self.__arch_dependent = []

        directories = _standard_directory_hierarchy.copy()
        directories.update(kw)

        for directory in directories:
            self.DefineDirectory(directory, directories[directory],
                                 directory in _default_arch_dependent)

    def is_arch_dependent(self, name):
        return name in self.__arch_dependent

    def DefineDirectory(self, name, directory, arch_dependent=False, help=None):
        # self.setattr(name, directory)
        SCons.Script.Main.AddOption(
            '--dir_'+name, action='store', type='string', dest='dir_'+name, default=directory,
            metavar='DIRECTORY', help=help or '%s directory [%s]'%(name,directory))
        setattr(self, name, SCons.Script.Main.GetOption('dir_'+name))
        if arch_dependent:
            self.__arch_dependent.append(name)

# List that keeps all created projects that are not finished yet.
_all_projects = []

def finish_all(sconscripts=()):
    "Finish all unfinished projects."
    for proj in tuple(_all_projects): # copy _all_projects, since
                                      # proj.finish() modifies it
        proj.finish(sconscripts=sconscripts)

    # Sanity check
    assert _all_projects == [], _all_projects

def find_project(name=None):
    "Return first unfinished project, or first unfinished project that has given name."
    if not _all_projects: return None
    if name is None:
        return _all_projects[0]
    for project in _all_projects:
        if project['NAME'] == name:
            return project

class Project(SCons.Environment.SubstitutionEnvironment):
    def _setdefault(self, **kw):
        for k in kw.keys():
            if self._dict.has_key(k):
                del kw[k]
        self._dict.update(kw)

    def _my_alias(self, alias):
        return '%s-%s' % (alias, self['NAME'])

    def __init__(self, env, **kw):
        """Project-specific initialisation.

        To be run after initializing SubstitutionEnvironment.
        """
        apply(SCons.Environment.SubstitutionEnvironment.__init__, (self,), kw)
        
        self.env = env
        
        if not 'packaging' in self.env['TOOLS']:
            self.env.Tool('packaging')

        _all_projects.append(self)
        self.finished = False

        self.distribution = []
        self.distribution_roots = []
        self.tests = []

        self._setdefault(
            DIR =  apply(DirectoryHierarchy, (), self.get('DIRECTORIES', {})),
            shortname = self['NAME'],
            TEST_ENVIRONMENT = {},
            TEST_COMMAND = '',
            TEST_ARGS = '',
            DIST_TYPE = 'src_targz',

            # Autotools compatibility
            PACKAGE = self['NAME'],
            configure_input = '',
            )

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

        # Prepare aliases
        my_aliases = {}
        for alias in ('all', 'dist', 'check', 'distcheck',
                      'install', 'install-data', 'install-exec'):
            my_alias = self.env.Alias(self._my_alias(alias))
            self.env.Alias(alias, my_alias)
            my_aliases[alias] = my_alias

        self.env.Depends(my_aliases['install'], my_aliases['install-data'])
        self.env.Depends(my_aliases['install'], my_aliases['install-exec'])
        self.env.Depends(my_aliases['check'], my_aliases['all'])

        self.env.Depends(self.env.Alias(self._my_alias('check')),
                         self.env.Alias(self._my_alias('all')))

        self.env.Append(PROJECTS=[self])

    # Wrappers
    def Configure(self, *args, **kwargs):
        try:
            kwargs.setdefault(header=self['header'])
        except KeyError:
            # everything is right, project does not have Header assocated yet.
            pass
        return apply(self.env.Configure, args, kwargs)

    def Header(self, header=None, lang=None):
        if header is None:
            return self['header']
        if not isinstance(header, SCons.Tool.header.HeaderFile):
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
            self.env.Append(CPPPATH=header.node.dir)

    def Substitute(self, *args, **kwargs):
        """Substitute, but default dictionary is parent Environment's
        dictionary, updated by self."""
        
        if 'substitute' not in self.env['TOOLS']:
            self.env.Tool('substitute')

        mydict = {}
        mydict.update(self.env.Dictionary())
        mydict.update(self._dict)

        userdict = kwargs.get('SUBST_DICT', None)
        if userdict is None:
            final_dict = mydict
        elif SCons.Util.is_Sequence(userdict):
            final_dict = {}
            for key in userdict:
                if mydict.has_key(key):
                    final_dict[key] = mydict[key]
        else:
            final_dict = userdict

        kwargs['SUBST_DICT'] = final_dict
        return apply(self.env.Substitute, args, kwargs)

    # Internal API
    def finish(self, sconscripts=()):
        global _all_projects

        if self.finished:
            raise SCons.Errors.UserError('Project %s already finished.' % self['NAME'])

        apply(self.Distribute, sconscripts)
        apply(self.Attach, self.env.get('ALL_LIBOBJS', []))

        self.distribution = self.arg2nodes(self.distribution, self.env.fs.Entry)

        for node in self.distribution:
            if node.has_builder():
                self.distribution_roots.append(node)

        for node in self.distribution_roots:
            self.distribution.extend(self.env.FindSourceFiles(node))

        pkg_kw = dict(self.items())
        pkg_kw['PACKAGETYPE'] = self['DIST_TYPE']
        
        package = apply(self.env.Package, (list(set(self.arg2nodes(self.distribution))),), pkg_kw)
        self.env.Ignore(package[0].dir, package)
        self.env.Alias('dist-'+self['NAME'], package)

        self.finished = True
        _all_projects.remove(self)

    def add_dist_root(self, nodes):
        self.distribution_roots.extend(nodes)

    # Entry points
    def Distribute(self, *nodes):
        nodes = list(SCons.Util.flatten(nodes))
        self.distribution.extend(nodes)
        return nodes

    def Attach(self, *nodes):
        nodes = self.arg2nodes(SCons.Util.flatten(nodes))
        self.add_dist_root(nodes)
        return nodes

    def Test(self, nodes, sources=[],
             distribute_sources=True, environment=None, command=None, args=None):
        nodes = self.arg2nodes(SCons.Util.flatten([nodes]))

        if SCons.Util.is_Sequence(sources):
            sources = SCons.Util.flatten(sources)
        else:
            sources = [sources]

        if SCons.Util.is_Sequence(nodes):
            nodes = SCons.Util.flatten(nodes)
        else:
            nodes = [nodes]

        if environment is None:
            environment = self['TEST_ENVIRONMENT']

        if command is None:
            command = self['TEST_COMMAND']

        if args is None:
            args = self['TEST_ARGS']

        for node in nodes:
            cmd = self.env.Command(str(node)+' test', # fake file name to make Command actually work
                                   [node,self._my_alias('all')] + sources,
                                   '$COMMAND ${SOURCE.abspath} $ARGS',
                                   COMMAND=command,
                                   ARGS=args,
                                   ENV=environment)
            if distribute_sources:
                self.add_dist_root(cmd)
            self.env.Alias(self._my_alias('check'), cmd)
            self.env.Ignore(cmd[0].dir, cmd)

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
        if node.env:
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
            if SCons.Util.is_String(node):
                node = self.env.File(node)
            returned_nodes.append(
                apply(self.__autoinstall_node, (node,), kwargs))

        self.env.Alias('all-'+self['NAME'], returned_nodes)
        self.Attach(returned_nodes)
        return returned_nodes

def ProjectMethod(env, name=None, version=None, bugreport=None, *args, **kwargs):
    """Return or look up Project object."""
    if version is None:
        proj = find_project(name)
        if not proj:
            raise SCons.Errors.UserError, 'No project named %s' % name
        return proj
    return Project(env, NAME=name, VERSION=version, BUGREPORT=bugreport, *args, **kwargs)

def generate(env):
    if 'header' not in env['TOOLS']:
        env.Tool('header')

    env.AddMethod(ProjectMethod, 'Project')

def exists(env):
    return True
