"""SCons.Tool.jar

Tool-specific initialization for jar.

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

import glob
import os.path

import SCons.Builder

def jarSources(target, source, env, for_signature):
    """Only include sources that are not a manifest file."""
    ret = []
    for src in source:
        contents = src.get_contents()
        if contents[:16] != "Manifest-Version":
            if env.has_key('JARCHDIR'):
                # If we are changing the dir with -C, then sources should
                # be relative to that directory.
                ret.append(src.get_path(src.fs.Dir(env['JARCHDIR'])))
            else:
                ret.append(src)
    return ret

def jarManifest(target, source, env, for_signature):
    """Look in sources for a manifest file, if any."""
    for src in source:
        contents = src.get_contents()
        if contents[:16] == "Manifest-Version":
            return src
    return ''

def jarFlags(target, source, env, for_signature):
    """If we have a manifest, make sure that the 'm'
    flag is specified."""
    for src in source:
        contents = src.get_contents()
        if contents[:16] == "Manifest-Version":
            if not 'm' in env['JARFLAGS']:
                return env['JARFLAGS'] + 'm'
            break
    return env['JARFLAGS']

def jarChdir(target, source, env, for_signature):
    """If we have an Environment variable by the name
    of JARCHDIR, then supply the command line option
    '-C <dir>' to Jar."""
    if env.has_key('JARCHDIR'):
        return [ '-C', '$JARCHDIR' ]
    return ''
        
JarBuilder = SCons.Builder.Builder(action = '$JARCOM',
                                   source_factory = SCons.Node.FS.default_fs.Entry,
                                   suffix = '$JARSUFFIX')

def generate(env):
    """Add Builders and construction variables for jar to an Environment."""
    try:
        bld = env['BUILDERS']['Jar']
    except KeyError:
        env['BUILDERS']['Jar'] = JarBuilder

    env['JAR']        = 'jar'
    env['JARFLAGS']   = 'cf'
    env['_JARFLAGS']  = jarFlags
    env['_JARMANIFEST'] = jarManifest
    env['_JARSOURCES'] = jarSources
    env['_JARCHDIR']  = jarChdir
    env['JARCOM']     = '$JAR $_JARFLAGS $TARGET $_JARMANIFEST $_JARCHDIR $_JARSOURCES'
    env['JARSUFFIX']  = '.jar'

def exists(env):
    return env.Detect('jar')
