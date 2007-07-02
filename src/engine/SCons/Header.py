"""SCons.Header

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

import SCons.Errors
import SCons.Util

def _final_text(text):
    if SCons.Util.is_String(text):
        return text

    raise Exception("TODO/jph: Non-string text not supported yet.")

class HeaderFile:
    def __init__(self):
        self._top = []
        self._bottom = []
        self._maincontent = []

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

    def check_comment_line(self, line):
        """Check comment line to see if it doesn't close comment.
        """
        raise NotImplementedError

    def check_name(self, line):
        """Check identifier for correctness.
        """
        raise NotImplementedError


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
        if not self.check_name(name):
            raise SCons.Errors.UserError("Invalid identifier.")

        text = "\n"
        if comment:
            text += self.Comment(comment, noinsert=True, nowrap=nowrap)

        if value is None:
            text += self.format_undefinition(name)
        else:
            text += self.format_definition(name, value)

        text += "\n"

        if noinsert:
            return text
        else:
            return self.Verbatim(text)
    
    # Output
    def Text(self):
        """Return header final contents as string.
        """
        return string.join(self._top + self._maincontent + self._bottom, '\n')+'\n'

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

    def build_function(self, target, source, env):
        self.Write(str(target[0]))

class CHeaderFile(HeaderFile):
    """Header file generator for C language
    """
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

HeaderClassSelector = SCons.Util.Selector( {
    '.c' : CHeaderFile,
    } )
