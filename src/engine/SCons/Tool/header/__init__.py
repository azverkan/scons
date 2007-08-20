"""SCons.Tool.header

Header file generation.
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
import string
import textwrap
import time
from types import *
import UserDict

import SCons.Action
import SCons.Errors
import SCons.Util

def _final_text(text):
    if SCons.Util.is_String(text):
        return text
    elif callable(text):
        return _final_text(text())

    raise SCons.Errors.UserError("TODO/jph: Non-string text not supported yet.")

class HeaderFile(UserDict.UserDict):
    language = None

    def __init__(self, dict=None, **kwargs):
        self._top = []
        self._bottom = []
        self._maincontent = []
        self._descriptions = {}
        apply(UserDict.UserDict.__init__, (self, dict), kwargs)
        self.node = None

    def set_node(self, node):
        self.node = node

    # Stub methods to be overloaded.
    def format_comment(self, lines):
        """Format list of lines as a comment.

        Lines are assumed to be valid."""
        raise NotImplementedError

    def format_definition(self, name, value):
        """Format definition of `name' to `value'.

        `name' should be a string that is valid identifier for
        language, `value' should be a string that is valid literal for
        language.
        """
        raise NotImplementedError

    def format_undefinition(self, name):
        """Format definition of `name' to undefined value.

        `name' should be a string that is valid identifier for
        language.
        """
        raise NotImplementedError

    def format_string(self, string):
        """Format string using target language syntax.
        """
        raise NotImplementedError

    def format_integer(self, string):
        """Format integer number using target language syntax.
        """
        raise NotImplementedError

    def format_floating_point(self, string):
        """Format floating point number using target language syntax.
        """
        raise NotImplementedError

    def check_comment_line(self, line):
        """Check comment line to see if it doesn't close comment.
        """
        raise NotImplementedError

    def check_name(self, line):
        """Check identifier for correctness.
        """
        raise NotImplementedError

    # Internal methods
    def __setitem__(self, name, value):
        if not self.check_name(name):
            raise SCons.Errors.UserError("Invalid identifier.")        
        UserDict.UserDict.__setitem__(self, name, value)

    def _kwdefs(self):
        rv = []
        keys = self.keys()
        keys.sort()
        for key in keys:
            rv.append(self.Definition(key, self[key], self._descriptions.get(key), noinsert=True))
        return rv

    def _format_literal(self, value):
        """Format `value' as valid literal.
        """
        if value is None:
            raise SCons.Errors.InternalError("Cannot format literal for None value.")
        
        if SCons.Util.is_String(value):
            return self.format_string(value)

        t = type(value)
        if t is IntType or t is LongType:
            return self.format_integer(value)

        if t is FloatType:
            return self.format_floating_point(value)

        if callable(getattr(value, 'read', None)):
            return self._format_literal(value.read())

        if callable(value):
            return self._format_literal(value())

        # Last resort
        return self.format_string(str(value))

    # Exported methods
    def Verbatim(self, text, position=None):
        """Insert text literally into header file.

        `text' may be:
         - a string to be inserted

        `position' may be "top" or "bottom".

        Return inserted text as a string.
        """

        text = _final_text(text)

        if position == "top":
            self._top.insert(0, text)
        elif position == "bottom":
            self._bottom.append(text)
        else:
            self._maincontent.append(text)
        return text

    def Comment(self, text, position=None, noinsert = False, nowrap=False):
        text = string.strip(_final_text(text))
        if nowrap:
            text = string.split(text, "\n")
        else:
            text = textwrap.wrap(text)

        for line in text:
            if not self.check_comment_line(line):
                raise SCons.Errors.UserError("Invalid comment.")

        text = self.format_comment(text)

        if noinsert:
            return text
        else:
            return self.Verbatim(text, position)

    def Definition(self, name, value, comment=None, position=None,
                   noinsert=False, nowrap=False, verbatim=False):
        name = _final_text(name)
        if not self.check_name(name):
            raise SCons.Errors.UserError("Invalid identifier.")

        text = "\n"

        if comment:
            if not self.check_comment_line(comment):
                raise SCons.Errors.UserError("Invalid comment.")
            text += self.Comment(comment, noinsert=True, nowrap=nowrap)

        if value is None:
            text += self.format_undefinition(name)
        else:
            if verbatim:
                text += self.format_definition(name, value)
            else:
                text += self.format_definition(name, self._format_literal(value))
                
        text += "\n"

        if noinsert:
            return text
        else:
            return self.Verbatim(text)

    def Template(self, name, comment, value=None, nodef=False):
        name = _final_text(name)
        comment = _final_text(comment)

        if not self.check_name(name):
            raise SCons.Errors.UserError("Invalid identifier.")

        self._descriptions[name] = comment

        if not nodef and not self.has_key(name):
            self[name] = value

    # Output                                 
    def Text(self):
        """Return header final contents as string.
        """            
        return string.join(self._top + self._maincontent + self._kwdefs() + self._bottom, '\n')+'\n'

    def Write(self, file):
        """Write header contents to file.

        File can be a file name or open file-like object.
        """

        needs_closing = False
        if SCons.Util.is_String(file):
            file = open(file, "w")
            needs_closing = True

        file.write(self.Text())

        if needs_closing:
            file.close()

    def _bld_action_func(self, target, source, env):
        self.Write(target[0].get_abspath())

    def _bld_emitter(self, target, source, env):
        return target, source+[SCons.Node.Python.Value(time.time())] # FIXME

    def _bld(self, env):
        """Return a Builder to build this header.
        """
        act = env.Action(self._bld_action_func, "Generating header file '${TARGET}'.")
        bld = env.Builder(action=act, emitter=self._bld_emitter)
        return bld

class CHeaderFile(HeaderFile):
    """Header file generator for C language
    """
    language = 'C'
    close_comment_re = re.compile("\\*/")
    name_re = re.compile("^[_A-Za-z][_A-Za-z0-9]*$")

    def check_comment_line(self, line):
        return not self.close_comment_re.match(line)

    def check_name(self, name):
        return self.name_re.match(name)

    def format_comment(self, lines):
        return "/*\n" + string.join(map(lambda s: " * "+s, lines), "\n") + "\n */\n"

    def format_definition(self, name, value):
        return "#define %s %s" % (name, value)

    def format_undefinition(self, name):
        return "/* #undef %s */" % name

    _quote_chars = {
        '\\' : '\\\\',
        '"'  : '\\"',
        '\a' : '\\a',
        '\b' : '\\b',
        '\f' : '\\f',
        '\n' : '\\n',
        '\r' : '\\r',
        '\t' : '\\t',
        }

    def format_string(self, str):
        """Format string using target language syntax.
        """
        return '"' + string.join(map(
            lambda c: self._quote_chars.get(c,c), str),'') + '"'

    def format_integer(self, number):
        """Format integer number using target language syntax.
        """
        return str(number)

    def format_floating_point(self, number):
        """Format floating point number using target language syntax.
        """
        return repr(number)


def HeaderMethod(env, name, lang=None, dict=None, **kwargs):
    node = env.arg2nodes(name)[0]
    try:
        header = node.attributes.__header
    except AttributeError: pass
    else:
        if lang:
            raise SCons.Errors.UserError(
                "%s is already defined header, can't change its language" % node)
        if dict: header.update(dict)
        header.update(kwargs)
        return header

    header_class = CHeaderFile # TODO: use a map.
    header = apply(header_class, (dict,), kwargs)
    bld = header._bld(env)
    node = bld(env, name)
    node[0].attributes.__header = header
    header.set_node(node[0])
    return header


def generate(env):
    env.AddMethod(HeaderMethod, 'Header')

def exists(env):
    return True
