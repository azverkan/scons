"""SCons.Tool.substitute

Builder to substitute keys in text files.
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

import re
from SCons.Script import *  # the usual scons stuff you get in a SConscript

import SCons.Node.Python
import SCons.Subst
import SCons.Util

def subst_in_file(target, source, env):
    for (t,s) in zip(target, source):
        # Computed substitution dictionary and restrict list is already in dependencies.
        for child in t.children():
            if isinstance(child, SCons.Node.Python.Value):
                restrict, subst_dict = child.value
                break
            
        try:
            f = open(s.rfile().get_abspath(), 'rb')
            contents = f.read()
            f.close()
        except:
            raise SCons.Errors.UserError, "Can't read source file %s"%sourcefile

        try:
            f = open(t.get_abspath(), 'wb')
        except:
            raise SCons.Errors.UserError, "Can't write target file %s"%targetfile

        subst_re = re.compile(env.subst('$SUBST_REGEXP', SCons.Subst.SUBST_RAW))
        last, match = 0, subst_re.search(contents)
        while match:
            f.write(contents[last:match.start()])

            key = match.group(1)
            if key == '':
                value = env.subst('$SUBST_MARKER', SCons.Subst.SUBST_RAW)
            else:
                if restrict and key not in restrict:
                    raise SCons.Errors.UserError, 'Substitution key not allowed: %s' % key

                try:
                    if callable(subst_dict):
                        value = subst_dict(env, key)
                    else:
                        value = env.subst(subst_dict[key], SCons.Subst.SUBST_RAW)
                except KeyError:
                    raise SCons.Errors.UserError, 'Unknown substitution key: %s' % key
            f.write(value)

            last = match.end()

            match = subst_re.search(contents, pos=match.end())
        f.write(contents[last:])

        f.close()

    return 0 # success

def subst_in_file_string(target, source, env):
    """This is what gets printed on the console."""
    return '\n'.join(['Substituting vars from %s into %s'%(str(s), str(t))
                      for (t,s) in zip(target, source)])

def subst_emitter(target, source, env):
    """Add dependency from substituted SUBST_DICT to target.
    Returns original target, source tuple unchanged.
    """
    restrict = None
    subst_dict = env.get('SUBST_DICT') or env.Dictionary()
    if SCons.Util.is_Sequence(subst_dict):
        restrict = subst_dict
        subst_dict = env.Dictionary()
    Depends(target, SCons.Node.Python.Value((restrict,subst_dict)))
    return target, source

SubstituteBuilder = None
 
def generate(env):
    """Adds SubstInFile builder, which substitutes the keys->values of SUBST_DICT
    from the source to the target.
    The values of SUBST_DICT first have any construction variables expanded
    (its keys are not expanded).
    If a value of SUBST_DICT is a python callable function, it is called and
    the result is expanded as the value.
    If there's more than one source and more than one target, each target gets
    substituted from the corresponding source.
    """
    try:
        env['BUILDERS']['Substitute']
    except KeyError:
        global SubstituteBuilder
        if SubstituteBuilder is None:
            subst_action=SCons.Action.Action(subst_in_file, subst_in_file_string)
            SubstituteBuilder = Builder(action=subst_action, emitter=subst_emitter, src_suffix='.in')
        env['BUILDERS']['Substitute'] = SubstituteBuilder

    env.SetDefault(
        SUBST_MARKER = '@',
        SUBST_PREFIX = '${SUBST_MARKER}',
        SUBST_SUFFIX = '${SUBST_MARKER}',
        SUBST_KEY_REGEXP = '[a-zA-Z0-9_]+',
        SUBST_REGEXP = '${SUBST_PREFIX}(|$SUBST_KEY_REGEXP)${SUBST_SUFFIX}'
        )

def exists(env):
    return 1
