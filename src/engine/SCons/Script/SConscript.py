"""SCons.Script.SConscript

This module defines the Python API provided to SConscript and SConstruct 
files.

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

import SCons.Action
import SCons.Builder
import SCons.Defaults
import SCons.Environment
import SCons.Errors
import SCons.Node
import SCons.Node.FS
import SCons.Node.Python
import SCons.Platform
import SCons.SConf
import SCons.Script
import SCons.Util
import SCons.Options
import SCons
import SCons.Node.Alias

import os
import os.path
import re
import string
import sys
import traceback

def do_nothing(text): pass
HelpFunction = do_nothing

default_targets = None
clean_targets = {}
arguments = {}
launch_dir = os.path.abspath(os.curdir)

# global exports set by Export():
global_exports = {}

# chdir flag
sconscript_chdir = 1

def SConscriptChdir(flag):
    global sconscript_chdir
    sconscript_chdir = flag

def _scons_add_args(alist):
    global arguments
    for arg in alist:
        a, b = string.split(arg, '=', 2)
        arguments[a] = b

def get_calling_namespaces():
    """Return the locals and globals for the function that called
    into this module in the current callstack."""
    try: 1/0
    except: frame = sys.exc_info()[2].tb_frame
    
    while frame.f_globals.get("__name__") == __name__: frame = frame.f_back

    return frame.f_locals, frame.f_globals

    
def compute_exports(exports):
    """Compute a dictionary of exports given one of the parameters
    to the Export() function or the exports argument to SConscript()."""

    exports = SCons.Util.Split(exports)
    loc, glob = get_calling_namespaces()

    retval = {}
    try:
        for export in exports:
            if SCons.Util.is_Dict(export):
                retval.update(export)
            else:
                try:
                    retval[export] = loc[export]
                except KeyError:
                    retval[export] = glob[export]
    except KeyError, x:
        raise SCons.Errors.UserError, "Export of non-existant variable '%s'"%x

    return retval
    

class Frame:
    """A frame on the SConstruct/SConscript call stack"""
    def __init__(self, exports, sconscript):
        self.globals = BuildDefaultGlobals()
        self.retval = None 
        self.prev_dir = SCons.Node.FS.default_fs.getcwd()
        self.exports = compute_exports(exports)  # exports from the calling SConscript
        # make sure the sconscript attr is a Node.
        if isinstance(sconscript, SCons.Node.Node):
            self.sconscript = sconscript
        else:
            self.sconscript = SCons.Node.FS.default_fs.File(str(sconscript))
        
# the SConstruct/SConscript call stack:
stack = []

# For documentation on the methods in this file, see the scons man-page

def Return(*vars):
    retval = []
    try:
        for var in vars:
            for v in string.split(var):
                retval.append(stack[-1].globals[v])
    except KeyError, x:
        raise SCons.Errors.UserError, "Return of non-existant variable '%s'"%x
        
    if len(retval) == 1:
        stack[-1].retval = retval[0]
    else:
        stack[-1].retval = tuple(retval)

# This function is responsible for converting the parameters passed to
# SConscript() calls into a list of files and export variables.  If the
# parameters are invalid, throws SCons.Errors.UserError. Returns a tuple
# (l, e) where l is a list of SConscript filenames and e is a list of
# exports.

def GetSConscriptFilenames(ls, kw):
    exports = []

    if len(ls) == 0:
        try:
            dirs = kw["dirs"]
        except KeyError:
            raise SCons.Errors.UserError, \
                  "Invalid SConscript usage - no parameters"

        if not SCons.Util.is_List(dirs):
            dirs = [ dirs ]
        dirs = map(str, dirs)

        name = kw.get('name', 'SConscript')

        files = map(lambda n, name = name: os.path.join(n, name), dirs)

    elif len(ls) == 1:

        files = ls[0]

    elif len(ls) == 2:

        files   = ls[0]
        exports = SCons.Util.Split(ls[1])

    else:

        raise SCons.Errors.UserError, \
              "Invalid SConscript() usage - too many arguments"

    if not SCons.Util.is_List(files):
        files = [ files ]

    if kw.get('exports'):
        exports.extend(SCons.Util.Split(kw['exports']))

    build_dir = kw.get('build_dir')
    if build_dir:
        if len(files) != 1:
            raise SCons.Errors.UserError, \
                "Invalid SConscript() usage - can only specify one SConscript with a build_dir"
        duplicate = kw.get('duplicate', 1)
        src_dir = kw.get('src_dir')
        if not src_dir:
            src_dir, fname = os.path.split(str(files[0]))
        else:
            if not isinstance(src_dir, SCons.Node.Node):
                src_dir = SCons.Node.FS.default_fs.Dir(src_dir)
            fn = files[0]
            if not isinstance(fn, SCons.Node.Node):
                fn = SCons.Node.FS.default_fs.File(fn)
            if fn.is_under(src_dir):
                # Get path relative to the source directory.
                fname = fn.get_path(src_dir)
            else:
                # Fast way to only get the terminal path component of a Node.
                fname = fn.get_path(fn.dir)
        BuildDir(build_dir, src_dir, duplicate)
        files = [os.path.join(str(build_dir), fname)]

    return (files, exports)

def SConscript(*ls, **kw):
    files, exports = GetSConscriptFilenames(ls, kw)

    default_fs = SCons.Node.FS.default_fs
    top = default_fs.Top
    sd = default_fs.SConstruct_dir.rdir()

    # evaluate each SConscript file
    results = []
    for fn in files:
        stack.append(Frame(exports,fn))
        old_sys_path = sys.path
        try:
            if fn == "-":
                exec sys.stdin in stack[-1].globals
            else:
                if isinstance(fn, SCons.Node.Node):
                    f = fn
                else:
                    f = default_fs.File(str(fn))
                _file_ = None

                # Change directory to the top of the source
                # tree to make sure the os's cwd and the cwd of
                # SCons.Node.FS.default_fs match so we can open the
                # SConscript.
                default_fs.chdir(top, change_os_dir=1)
                if f.rexists():
                    _file_ = open(f.rstr(), "r")
                elif f.has_src_builder():
                    # The SConscript file apparently exists in a source
                    # code management system.  Build it, but then clear
                    # the builder so that it doesn't get built *again*
                    # during the actual build phase.
                    f.build()
                    f.builder_set(None)
                    s = str(f)
                    if os.path.exists(s):
                        _file_ = open(s, "r")
                if _file_:
                    # Chdir to the SConscript directory.  Use a path
                    # name relative to the SConstruct file so that if
                    # we're using the -f option, we're essentially
                    # creating a parallel SConscript directory structure
                    # in our local directory tree.
                    #
                    # XXX This is broken for multiple-repository cases
                    # where the SConstruct and SConscript files might be
                    # in different Repositories.  For now, cross that
                    # bridge when someone comes to it.
                    ldir = default_fs.Dir(f.dir.get_path(sd))
                    try:
                        default_fs.chdir(ldir, change_os_dir=sconscript_chdir)
                    except OSError:
                        # There was no local directory, so we should be
                        # able to chdir to the Repository directory.
                        # Note that we do this directly, not through
                        # default_fs.chdir(), because we still need to
                        # interpret the stuff within the SConscript file
                        # relative to where we are logically.
                        default_fs.chdir(ldir, change_os_dir=0)
                        os.chdir(f.rfile().dir.get_abspath())

                    # Append the SConscript directory to the beginning
                    # of sys.path so Python modules in the SConscript
                    # directory can be easily imported.
                    sys.path = [ f.dir.get_abspath() ] + sys.path

                    # This is the magic line that actually reads up and
                    # executes the stuff in the SConscript file.  We
                    # look for the "exec _file_ " from the beginning
                    # of this line to find the right stack frame (the
                    # next one) describing the SConscript file and line
                    # number that creates a node.
                    exec _file_ in stack[-1].globals
                else:
                    sys.stderr.write("Ignoring missing SConscript '%s'\n" %
                                     f.path)
                
        finally:
            sys.path = old_sys_path
            frame = stack.pop()
            try:
                default_fs.chdir(frame.prev_dir, change_os_dir=sconscript_chdir)
            except OSError:
                # There was no local directory, so chdir to the
                # Repository directory.  Like above, we do this
                # directly.
                default_fs.chdir(frame.prev_dir, change_os_dir=0)
                os.chdir(frame.prev_dir.rdir().get_abspath())

            results.append(frame.retval)

    # if we only have one script, don't return a tuple
    if len(results) == 1:
        return results[0]
    else:
        return tuple(results)

def is_our_exec_statement(line):
    return not line is None and line[:12] == "exec _file_ "

def SConscript_exception(file=sys.stderr):
    """Print an exception stack trace just for the SConscript file(s).
    This will show users who have Python errors where the problem is,
    without cluttering the output with all of the internal calls leading
    up to where we exec the SConscript."""
    stack = traceback.extract_tb(sys.exc_traceback)
    last_text = ""
    i = 0
    for frame in stack:
        if is_our_exec_statement(last_text):
            break
        i = i + 1
        last_text = frame[3]
    type = str(sys.exc_type)
    if type[:11] == "exceptions.":
        type = type[11:]
    file.write('%s: %s:\n' % (type, sys.exc_value))
    for fname, line, func, text in stack[i:]:
        file.write('  File "%s", line %d:\n' % (fname, line))
        file.write('    %s\n' % text)

def annotate(node):
    """Annotate a node with the stack frame describing the
    SConscript file and line number that created it."""
    stack = traceback.extract_stack()
    last_text = ""
    for frame in stack:
        # If the script text of the previous frame begins with the
        # magic "exec _file_ " string, then this frame describes the
        # SConscript file and line number that caused this node to be
        # created.  Record the tuple and carry on.
        if is_our_exec_statement(last_text):
            node.creator = frame
            return
        last_text = frame[3]

# The following line would cause each Node to be annotated using the
# above function.  Unfortunately, this is a *huge* performance hit, so
# leave this disabled until we find a more efficient mechanism.
#SCons.Node.Annotate = annotate

def Default(*targets):
    global default_targets
    if default_targets is None:
        default_targets = []
    for t in targets:
        if t is None:
            default_targets = []
        elif isinstance(t, SCons.Node.Node):
            default_targets.append(t)
        else:
            default_targets.extend(SCons.Node.arg2nodes(t,
                                         SCons.Node.FS.default_fs.Entry))

def Local(*targets):
    for targ in targets:
        if isinstance(targ, SCons.Node.Node):
            targ.set_local()
        else:
            for t in SCons.Node.arg2nodes(targ, SCons.Node.FS.default_fs.Entry):
               t.set_local()

def Help(text):
    HelpFunction(text)

def BuildDir(build_dir, src_dir, duplicate=1):
    SCons.Node.FS.default_fs.BuildDir(build_dir, src_dir, duplicate)

def GetBuildPath(files):
    nodes = SCons.Node.arg2nodes(files, SCons.Node.FS.default_fs.Entry)
    ret = map(str, nodes)
    if len(ret) == 1:
        return ret[0]
    return ret

def FindFile(file, dirs):
    nodes = SCons.Node.arg2nodes(dirs, SCons.Node.FS.default_fs.Dir)
    return SCons.Node.FS.find_file(file, nodes)

def Export(*vars):
    for var in vars:
        global_exports.update(compute_exports(var))

def Import(*vars):
    try:
        for var in vars:
            var = SCons.Util.Split(var)
            for v in var:
                if v == '*':
                    stack[-1].globals.update(global_exports)
                    stack[-1].globals.update(stack[-1].exports)
                else:
                    if stack[-1].exports.has_key(v):
                        stack[-1].globals[v] = stack[-1].exports[v]
                    else:
                        stack[-1].globals[v] = global_exports[v]
    except KeyError,x:
        raise SCons.Errors.UserError, "Import of non-existant variable '%s'"%x

def GetLaunchDir():
    return launch_dir

def SetBuildSignatureType(type):
    SCons.Warnings.warn(SCons.Warnings.DeprecatedWarning,
                        "The SetBuildSignatureType() function has been deprecated;\n" +\
                        "\tuse the TargetSignatures() function instead.")
    TargetSignatures(type)

def TargetSignatures(type):
    import SCons.Sig
    if type == 'build':
        SCons.Sig.build_signature = 1
    elif type == 'content':
        SCons.Sig.build_signature = 0
    else:
        raise SCons.Errors.UserError, "Unknown build signature type '%s'"%type

def SetContentSignatureType(type):
    SCons.Warnings.warn(SCons.Warnings.DeprecatedWarning,
                        "The SetContentSignatureType() function has been deprecated;\n" +\
                        "\tuse the SourceSignatures() function instead.")
    SourceSignatures(type)

def SourceSignatures(type):
    if type == 'MD5':
        import SCons.Sig.MD5
        SCons.Script.sig_module = SCons.Sig.MD5
    elif type == 'timestamp':
        import SCons.Sig.TimeStamp
        SCons.Script.sig_module = SCons.Sig.TimeStamp
    else:
        raise SCons.Errors.UserError, "Unknown content signature type '%s'"%type


class Options(SCons.Options.Options):
    def __init__(self, files=None, args=arguments):
        SCons.Options.Options.__init__(self, files, args)

def CheckVersion(major, minor, version_string):
    """Return 0 if 'major' and 'minor' are greater than the version
    in 'version_string', and 1 otherwise."""
    try:
        v_major, v_minor, v_micro, release, serial = sys.version_info
    except AttributeError:
        version = string.split(string.split(version_string, ' ')[0], '.')
        v_major = int(version[0])
        v_minor = int(re.match('\d+', version[1]).group())
    if major > v_major or (major == v_major and minor > v_minor):
        return 0
    else:
        return 1

def EnsureSConsVersion(major, minor):
    """Exit abnormally if the SCons version is not late enough."""
    if not CheckVersion(major,minor,SCons.__version__):
        print "SCons %d.%d or greater required, but you have SCons %s" %(major,minor,SCons.__version__)
        sys.exit(2)

def EnsurePythonVersion(major, minor):
    """Exit abnormally if the Python version is not late enough."""
    if not CheckVersion(major,minor,sys.version):
	v = string.split(sys.version, " ", 1)[0]
        print "Python %d.%d or greater required, but you have Python %s" %(major,minor,v)
        sys.exit(2)

def GetJobs():
    SCons.Warnings.warn(SCons.Warnings.DeprecatedWarning,
                        "The GetJobs() function has been deprecated;\n" +\
                        "\tuse GetOption('num_jobs') instead.")

    return GetOption('num_jobs')
 
def SetJobs(num):
    SCons.Warnings.warn(SCons.Warnings.DeprecatedWarning,
                        "The SetJobs() function has been deprecated;\n" +\
                        "\tuse SetOption('num_jobs', num) instead.")
    SetOption('num_jobs', num)

def Clean(target, files):
    if not isinstance(target, SCons.Node.Node):
        target = SCons.Node.FS.default_fs.Entry(target, create=1)

    if not SCons.Util.is_List(files):
        files = [files]

    nodes = []
    for f in files:
        if isinstance(f, SCons.Node.Node):
            nodes.append(f)
        else:
            nodes.extend(SCons.Node.arg2nodes(f, SCons.Node.FS.default_fs.Entry))

    try:
        clean_targets[target].extend(nodes)
    except KeyError:
        clean_targets[target] = nodes

def AddPreAction(files, action):
    nodes = SCons.Node.arg2nodes(files, SCons.Node.FS.default_fs.Entry)
    for n in nodes:
        n.add_pre_action(SCons.Action.Action(action))

def AddPostAction(files, action):
    nodes = SCons.Node.arg2nodes(files, SCons.Node.FS.default_fs.Entry)
    for n in nodes:
        n.add_post_action(SCons.Action.Action(action))

def Exit(value=0):
    sys.exit(value)


def Alias(name):
    alias = SCons.Node.Alias.default_ans.lookup(name)
    if alias is None:
        alias = SCons.Node.Alias.default_ans.Alias(name)
    return alias

def SetOption(name, value):
    SCons.Script.ssoptions.set(name, value)

def GetOption(name):
    return SCons.Script.ssoptions.get(name)

def SConsignFile(name=".sconsign.dbm"):
    import SCons.Sig
    if not os.path.isabs(name):
        sd = str(SCons.Node.FS.default_fs.SConstruct_dir)
        name = os.path.join(sd, name)
    SCons.Sig.SConsignFile(name)

def BuildDefaultGlobals():
    """
    Create a dictionary containing all the default globals for 
    SConstruct and SConscript files.
    """

    globals = {}
    globals['Action']            = SCons.Action.Action
    globals['AddPostAction']     = AddPostAction
    globals['AddPreAction']      = AddPreAction
    globals['Alias']             = Alias
    globals['ARGUMENTS']         = arguments
    globals['BuildDir']          = BuildDir
    globals['Builder']           = SCons.Builder.Builder
    globals['CacheDir']          = SCons.Node.FS.default_fs.CacheDir
    globals['Clean']             = Clean
    globals['Configure']         = SCons.SConf.SConf
    globals['CScan']             = SCons.Defaults.CScan
    globals['Default']           = Default
    globals['DefaultEnvironment'] = SCons.Defaults.DefaultEnvironment
    globals['Dir']               = SCons.Node.FS.default_fs.Dir
    globals['EnsurePythonVersion'] = EnsurePythonVersion
    globals['EnsureSConsVersion'] = EnsureSConsVersion
    globals['Environment']       = SCons.Environment.Environment
    globals['Exit']              = Exit
    globals['Export']            = Export
    globals['File']              = SCons.Node.FS.default_fs.File
    globals['FindFile']          = FindFile
    globals['GetBuildPath']      = GetBuildPath
    globals['GetCommandHandler'] = SCons.Action.GetCommandHandler
    globals['GetJobs']           = GetJobs
    globals['GetLaunchDir']      = GetLaunchDir
    globals['GetOption']         = GetOption    
    globals['Help']              = Help
    globals['Import']            = Import
    globals['Literal']           = SCons.Util.Literal
    globals['Local']             = Local
    globals['Options']           = Options
    globals['ParseConfig']       = SCons.Util.ParseConfig
    globals['Platform']          = SCons.Platform.Platform
    globals['Repository']        = SCons.Node.FS.default_fs.Repository
    globals['Return']            = Return
    globals['SConscript']        = SConscript
    globals['SConscriptChdir']   = SConscriptChdir
    globals['SConsignFile']      = SConsignFile
    globals['Scanner']           = SCons.Scanner.Base
    globals['SetBuildSignatureType'] = SetBuildSignatureType
    globals['SetCommandHandler'] = SCons.Action.SetCommandHandler
    globals['SetContentSignatureType'] = SetContentSignatureType
    globals['SetJobs']           = SetJobs
    globals['SetOption']         = SetOption
    globals['SourceSignatures']  = SourceSignatures
    globals['Split']             = SCons.Util.Split
    globals['TargetSignatures']  = TargetSignatures
    globals['Tool']              = SCons.Tool.Tool
    globals['Value']             = SCons.Node.Python.Value
    globals['WhereIs']           = SCons.Util.WhereIs
    return globals
