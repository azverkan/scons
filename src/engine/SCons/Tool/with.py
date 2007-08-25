"""SCons.Tool.with

Autotools-style --with-something, --without-something,
--enable-something, --disable-something command-line arguments.

Adds Environment.WithArgument and Environment.EnableArgument methods.
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

import optparse

import SCons.Script

def WithArgument(env, name, help='', default=None, opts=('with','without'), metavar='DIR'):
    """Add optional support switches, by default --with-name and --without-name, with specified help string.

    Adds options for end-user to specify compilation options.  Option
    value is stored as with_name, and its value is: False if user
    specified --without-name, True if user specified --with-name
    without arguments, string if user specified --with-name=string, or
    default if user didn't specify any of the options.

    "with" and "without" in switch and option names can be changed
    with opts argument; metavar is optparse's meta-variable for help
    string.
    """
    
    var = '%s_%s' % ( opts[0], name )
    with_switch = '--%s-%s' % (opts[0], name)
    without_switch = '--%s-%s' % (opts[1], name)
    help_string = '%s' % (help)
    SCons.Script.AddOption(with_switch, dest=var, metavar=metavar,
                           nargs='?', const=True, default=default, help=help_string)
    SCons.Script.AddOption(without_switch, dest=var,
                           action='store_false', help='')

def EnableArgument(*args, **kwargs):
    """Add optional support switches, by default --enable-name and --disable-name.

    See WithArgument for details.
    """
    kwargs.setdefault('opts', ('enable', 'disable'))
    kwargs.setdefault('metavar', None)
    apply(WithArgument, args, kwargs)

def generate(env):
    env.AddMethod(WithArgument)
    env.AddMethod(EnableArgument)

def exists(env):
    return True
