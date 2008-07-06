"""SCons.Tool.python

Tool-specific initialization for python binary builder.

There normally shouldn't be any need to import this module directly.
It will usually be imported through the generic SCons.Tool.Tool()
selection method.

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

import os

import SCons.Action
import SCons.Builder
import SCons.Errors
import SCons.Tool


def InstallPython(env, target=None, source=None, dir=None, **kw):
    """InstallPython creates .pyc or .pyo files for .py source files
    and adds them to the list of targets along with the source files.
    They are later copied to the destination (target) directory.

    InstallPython takes target (destination) directory as its first
    argument and a list of source files/directories as a second argument.

    InstallPython returns the list of target files to copy to the
    target directory.
    """

    if target and dir:
        import SCons.Errors
        raise SCons.Errors.UserError, "Both target and dir defined for InstallPython(), only one may be defined."
    if not dir:
        dir=target
    
    try:
        dnodes = env.arg2nodes(dir, env.fs.Dir)
    except TypeError:
        raise SCons.Errors.UserError, "Target `%s' of Install() is a file, but should be a directory.  Perhaps you have the InstallPython() arguments backwards?" % str(dir)

    sources = env.arg2nodes(source, env.fs.Entry)
    tgt = []

    try:
        import py_compile
    except ImportError:
        raise SCons.Errors.InternalError, "Couldn't import py_compile module"

    # import `compileall` module only if there is a dir in sources list
    import SCons.Node
    dir_in_sources = [isinstance(i, SCons.Node.FS.Dir) for i in sources]
    if True in dir_in_sources:
        try:
            import compileall
        except ImportError:
            raise SCons.Errors.InternalError, "Couldn't import compileall module"
        import glob

    if env['PYSUFFIX'] == 'PYO':
        pysuffix = 'o'
    else:
        pysuffix = 'c'

    PIB = PythonInstallBuilder

    for dnode in dnodes:
        for src in sources:
            # add *.py and *.pyc files from a directory to tgt list
            if isinstance(src, SCons.Node.FS.Dir) and pysuffix == 'c':
                compileall.compile_dir(str(src), maxlevels = 0, quiet = 1)
                globpath = src.path + os.sep + '*.py'
                py_and_pycs = glob.glob(globpath) + glob.glob(globpath+'c')
                for filename in py_and_pycs:
                    target = env.fs.Entry('.'+os.sep+filename, dnode)
                    tgt.extend(apply(PIB, (env, target, filename), kw))
            # add *.py and *.pyo files from a directory to tgt list
            elif isinstance(src, SCons.Node.FS.Dir):
                to_compile = []
                py_files = glob.glob(src.path + os.sep + '*.py')
                for py_file in py_files:
                    to_compile.append(py_file)
                    target_path = '.' + os.sep + py_file

                    # add '.py' file to tgt list
                    py_src = env.fs.Entry(py_file)
                    py_tgt = env.fs.Entry(target_path, dnode)
                    tgt.extend(apply(PIB, (env, py_tgt, py_src), kw))

                    # add '.pyo' file to tgt list
                    pyo_src = env.fs.Entry(py_file + pysuffix)
                    pyo_tgt = env.fs.Entry(target_path + pysuffix, dnode)
                    tgt.extend(apply(PIB, (env, pyo_tgt, pyo_src), kw))
                act = SCons.Action.CommandAction('@$PYCOM %s' % (' '.join(to_compile)))
                act([], [], env)
            # add single '.py' and '.pyc' or '.pyo' file to tgt list
            else:
                # add '.py' file to tgt list
                target = env.fs.Entry('.'+os.sep+src.path, dnode)
                tgt.extend(apply(PIB, (env, target, src), kw))

                # .pyc or .pyo source and target files
                pyco_src = env.fs.Entry(src.path + pysuffix)
                pyco_tgt = env.fs.Entry(target.path + pysuffix)

                if pysuffix == 'c':
                    py_compile.compile(src.path)
                else:
                    act = SCons.Action.CommandAction('@$PYCOM %s' % (src.path))
                    act([], [], env)

                # add '.pyc' or '.pyo' file to tgt list
                tgt.extend(apply(PIB, (env, pyco_tgt, pyco_src), kw))

    return tgt


def generate(env):
    from install import copyFunc

    try:
        env['INSTALL']
    except KeyError:
        env['INSTALL']    = copyFunc

    global PythonInstallBuilder
    PythonInstallBuilder = SCons.Tool.createPythonBuilder(env)

    env['PYTHON'] = 'python'
    env['PYO_FLAGS'] = '-O'
    env['PYO_CMD'] = "-c 'import sys,py_compile; [py_compile.compile(i) for i in sys.argv[1:]]' "
    env['PYCOM'] = '$PYTHON $PYO_FLAGS $PYO_CMD '
    env['PYCOMSTR'] = 'Install file: "$SOURCE" as "$TARGET"'

    env['PYSUFFIX'] = 'PYC'
    env['BUILDERS']['InstallPython'] =  InstallPython

def exists(env):
    return 1
