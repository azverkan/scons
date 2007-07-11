"""SCons.Tool.Packaging.rpm

The rpm packager.
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

import SCons.Builder
import os

from SCons.Tool.packaging import stripinstall_emitter, packageroot_emitter, src_targz

def package(env, target, source, PACKAGEROOT, NAME, VERSION,
            PACKAGEVERSION, DESCRIPTION, SUMMARY, X_RPM_GROUP, LICENSE,
            **kw):
    # initialize the rpm tool
    SCons.Tool.Tool('rpm').generate(env)

    # create the neccesary builder
    bld = env['BUILDERS']['Rpm']
    env['RPMFLAGS'] = SCons.Util.CLVar('-ta')

    bld.push_emitter(targz_emitter)
    bld.push_emitter(specfile_emitter)
    bld.push_emitter(stripinstall_emitter())

    # override the default target, with the rpm specific ones.
    if str(target[0])=="%s-%s"%(NAME, VERSION):
        # This should be overridable from the construction environment,
        # which it is by using ARCHITECTURE=.
        # Guessing based on what os.uname() returns at least allows it
        # to work for both i386 and x86_64 Linux systems.
        archmap = {
            'i686'  : 'i386',
            'i586'  : 'i386',
            'i486'  : 'i386',
        }

        buildarchitecture = os.uname()[4]
        buildarchitecture = archmap.get(buildarchitecture, buildarchitecture)

        if kw.has_key('ARCHITECTURE'):
            buildarchitecture = kw['ARCHITECTURE']

        srcrpm = '%s-%s-%s.src.rpm' % (NAME, VERSION, PACKAGEVERSION)
        binrpm = srcrpm.replace( 'src', buildarchitecture )

        target = [ srcrpm, binrpm ]

    # get the correct arguments into the kw hash
    loc=locals()
    del loc['kw']
    kw.update(loc)
    del kw['source'], kw['target'], kw['env']

    # if no "SOURCE_URL" tag is given add a default one.
    if not kw.has_key('SOURCE_URL'):
        kw['SOURCE_URL']=(str(target[0])+".tar.gz").replace('.rpm', '')

    # now call the rpm builder to actually build the packet.
    return apply(bld, [env, target, source], kw)


def targz_emitter(target, source, env):
    """ Puts all source files into a tar.gz file. """
    # the rpm tool depends on a source package, until this is chagned
    # this hack needs to be here that tries to pack all sources in.
    sources = env.FindSourceFiles()

    # filter out the target we are building the source list for.
    sources = [s for s in sources if not (s in target)]

    # find the .spec file for rpm and add it since it is not necessarily found
    # by the FindSourceFiles function.
    sources.extend( [s for s in source if str(s).rfind('.spec')!=-1] )

    # as the source contains the url of the source package this rpm package
    # is built from, we extract the target name
    tarball = (str(target[0])+".tar.gz").replace('.rpm', '')
    try:
        tarball = env['SOURCE_URL'].split('/')[-1]
    except KeyError, e:
        raise SCons.Errors.UserError( "Missing PackageTag '%s' for RPM packager" % e.args[0] )

    tarball = src_targz.package(env, source=sources, target=tarball,
                                PACKAGEROOT=env['PACKAGEROOT'], )

    return (target, tarball)

def specfile_emitter(target, source, env):
    specfile = "%s-%s" % (env['NAME'], env['VERSION'])

    bld = SCons.Builder.Builder(action         = build_specfile,
                                suffix         = '.spec',
                                target_factory = SCons.Node.FS.File)

    source.extend(bld(env, specfile, source))

    return (target,source)

def build_specfile(target, source, env):
    """ Builds a RPM specfile from a dictionary with string metadata and
    by analyzing a tree of nodes.
    """
    file = open(target[0].abspath, 'w')
    str  = ""

    try:
        file.write( build_specfile_header(env) )
        file.write( build_specfile_sections(env) )
        file.write( build_specfile_filesection(env, source) )
        file.close()

        # call a user specified function
        if env.has_key('CHANGE_SPECFILE'):
            env['CHANGE_SPECFILE'](target, source)

    except KeyError, e:
        raise SCons.Errors.UserError( '"%s" package field for RPM is missing.' % e.args[0] )


#
# mandatory and optional package tag section
#
def build_specfile_sections(spec):
    """ Builds the sections of a rpm specfile.
    """
    str = ""

    mandatory_sections = {
        'DESCRIPTION'  : '\n%%description\n%s\n\n', }

    str += SimpleTagCompiler(mandatory_sections).compile( spec )

    optional_sections = {
        'DESCRIPTION_'        : '%%description -l %s\n%s\n\n',
        'CHANGELOG'           : '%%changelog\n%s\n\n',
        'X_RPM_PREINSTALL'    : '%%pre\n%s\n\n',
        'X_RPM_POSTINSTALL'   : '%%post\n%s\n\n',
        'X_RPM_PREUNINSTALL'  : '%%preun\n%s\n\n',
        'X_RPM_POSTUNINSTALL' : '%%postun\n%s\n\n',
        'X_RPM_VERIFY'        : '%%verify\n%s\n\n',

        # These are for internal use but could possibly be overriden
        'X_RPM_PREP'          : '%%prep\n%s\n\n',
        'X_RPM_BUILD'         : '%%build\n%s\n\n',
        'X_RPM_INSTALL'       : '%%install\n%s\n\n',
        'X_RPM_CLEAN'         : '%%clean\n%s\n\n',
        }

    # Default prep, build, install and clean rules
    # TODO: optimize those build steps, to not compile the project a second time
    if not spec.has_key('X_RPM_PREP'):
        spec['X_RPM_PREP'] = 'rm -rf "$RPM_BUILD_ROOT"'
        spec['X_RPM_PREP'] += '\n%setup -q'

    if not spec.has_key('X_RPM_BUILD'):
        spec['X_RPM_BUILD'] = 'mkdir "$RPM_BUILD_ROOT"'

    if not spec.has_key('X_RPM_INSTALL'):
        spec['X_RPM_INSTALL'] = 'scons --install-sandbox="$RPM_BUILD_ROOT" "$RPM_BUILD_ROOT"'

    if not spec.has_key('X_RPM_CLEAN'):
        spec['X_RPM_CLEAN'] = 'rm -rf "$RPM_BUILD_ROOT"'

    str += SimpleTagCompiler(optional_sections, mandatory=0).compile( spec )

    return str

def build_specfile_header(spec):
    """ Builds all section but the %file of a rpm specfile
    """
    str = ""

    # first the mandatory sections
    mandatory_header_fields = {
        'NAME'           : '%%define name %s\nName: %%{name}\n',
        'VERSION'        : '%%define version %s\nVersion: %%{version}\n',
        'PACKAGEVERSION' : '%%define release %s\nRelease: %%{release}\n',
        'X_RPM_GROUP'    : 'Group: %s\n',
        'SUMMARY'        : 'Summary: %s\n',
        'LICENSE'        : 'License: %s\n', }

    str += SimpleTagCompiler(mandatory_header_fields).compile( spec )

    # now the optional tags
    optional_header_fields = {
        'VENDOR'              : 'Vendor: %s\n',
        'X_RPM_URL'           : 'Url: %s\n',
        'SOURCE_URL'          : 'Source: %s\n',
        'SUMMARY_'            : 'Summary(%s): %s\n',
        'X_RPM_DISTRIBUTION'  : 'Distribution: %s\n',
        'X_RPM_ICON'          : 'Icon: %s\n',
        'X_RPM_PACKAGER'      : 'Packager: %s\n',
        'X_RPM_GROUP_'        : 'Group(%s): %s\n',

        'X_RPM_REQUIRES'      : 'Requires: %s\n',
        'X_RPM_PROVIDES'      : 'Provides: %s\n',
        'X_RPM_CONFLICTS'     : 'Conflicts: %s\n',
        'X_RPM_BUILDREQUIRES' : 'BuildRequires: %s\n',

        'X_RPM_SERIAL'        : 'Serial: %s\n',
        'X_RPM_EPOCH'         : 'Epoch: %s\n',
        'X_RPM_AUTOREQPROV'   : 'AutoReqProv: %s\n',
        'X_RPM_EXCLUDEARCH'   : 'ExcludeArch: %s\n',
        'X_RPM_EXCLUSIVEARCH' : 'ExclusiveArch: %s\n',
        'X_RPM_PREFIX'        : 'Prefix: %s\n',
        'X_RPM_CONFLICTS'     : 'Conflicts: %s\n',

        # internal use
        'X_RPM_BUILDROOT'     : 'BuildRoot: %s\n', }

    # fill in default values:
    # Adding a BuildRequires renders the .rpm unbuildable under System, which
    # are not managed by rpm, since the database to resolve this dependency is
    # missing (take Gentoo as an example)
#    if not s.has_key('x_rpm_BuildRequires'):
#        s['x_rpm_BuildRequires'] = 'scons'

    if not spec.has_key('X_RPM_BUILDROOT'):
        spec['X_RPM_BUILDROOT'] = '%{_tmppath}/%{name}-%{version}-%{release}'

    str += SimpleTagCompiler(optional_header_fields, mandatory=0).compile( spec )
    return str

#
# mandatory and optional file tags
#
def build_specfile_filesection(spec, files):
    """ builds the %file section of the specfile
    """
    str  = '%files\n'

    if not spec.has_key('X_RPM_DEFATTR'):
        spec['X_RPM_DEFATTR'] = '(-,root,root)'

    str += '%%defattr %s\n' % spec['X_RPM_DEFATTR']

    supported_tags = {
        'PACKAGING_CONFIG'           : '%%config %s',
        'PACKAGING_CONFIG_NOREPLACE' : '%%config(noreplace) %s',
        'PACKAGING_DOC'              : '%%doc %s',
        'PACKAGING_UNIX_ATTR'        : '%%attr %s',
        'PACKAGING_LANG_'            : '%%lang(%s) %s',
        'PACKAGING_X_RPM_VERIFY'     : '%%verify %s',
        'PACKAGING_X_RPM_DIR'        : '%%dir %s',
        'PACKAGING_X_RPM_DOCDIR'     : '%%docdir %s',
        'PACKAGING_X_RPM_GHOST'      : '%%ghost %s', }

    for file in files:
        # build the tagset
        tags = {}
        for k in supported_tags:
            try:
                tags[k]=getattr(file, k)
            except AttributeError:
                pass

        # compile the tagset
        str += SimpleTagCompiler(supported_tags, mandatory=0).compile( tags )

        str += ' '
        str += file.PACKAGING_INSTALL_LOCATION
        str += '\n\n'

    return str

class SimpleTagCompiler:
    """ This class is a simple string substition utility:
    the replacement specfication is stored in the tagset dictionary, something
    like:
     { "abc"  : "cdef %s ",
       "abc_" : "cdef %s %s" }

    the compile function gets a value dictionary, which may look like:
    { "abc"    : "ghij",
      "abc_gh" : "ij" }

    The resulting string will be:
     "cdef ghij cdef gh ij"
    """
    def __init__(self, tagset, mandatory=1):
        self.tagset    = tagset
        self.mandatory = mandatory

    def compile(self, values):
        """ compiles the tagset and returns a str containing the result
        """
        def is_international(tag):
            return tag.endswith('_')

        def get_country_code(tag):
            return tag[-2:]

        def strip_country_code(tag):
            return tag[:-2]

        replacements = self.tagset.items()

        str = ""
        for key, replacement in [ (k,v) for k,v in replacements if not is_international(k) ]:
            try:
                str += replacement % values[key]
            except KeyError, e:
                if self.mandatory:
                    raise e

        for key, replacement in [ (k,v) for k,v in replacements if is_international(k) ]:
            try:
                int_values_for_key = [ (get_country_code(k),v) for k,v in values.items() if strip_country_code(k) == key ]
                for v in int_values_for_key:
                    str += replacement % v
            except KeyError, e:
                if self.mandatory:
                    raise e

        return str
