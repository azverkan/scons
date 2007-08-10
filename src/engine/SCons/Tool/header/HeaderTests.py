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

import StringIO
import sys
import unittest

from SCons.Tool.header import *

class DummyHeaderFile(HeaderFile):
    """Dummy header file for tests.
    """
    language = 'Dummy'

    def check_comment_line(self, line):
        return line.find('WRONG') < 0

    def check_name(self, name):
        return name.find(' ') < 0

    def format_comment(self, lines):
        return string.join(map(lambda s:"C"+s, lines), "\n") + '\n'

    def format_definition(self, name, value):
        return "D"+name+"="+value

    def format_undefinition(self, name):
        return 'U'+name

    def format_string(self, s):
        return '"'+s

    def format_integer(self, number):
        return str(number)

    def format_floating_point(self, number):
        return repr(number)


class HeaderTestCase(unittest.TestCase):
    def test_abstract_base(self):
        "Test if abstract base class doesn't work as it's supposed to."
        h = HeaderFile()
        
        try: h.format_comment([])
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.format_comment didn't raise expected NotImplementedError."

        try: h.format_definition('foo',1)
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.format_definition didn't raise expected NotImplementedError."

        try: h.format_undefinition('foo')
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.format_undefinition didn't raise expected NotImplementedError."

        try: h.format_string('foo')
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.format_string didn't raise expected NotImplementedError."

        try: h.format_integer(23)
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.format_integer didn't raise expected NotImplementedError."

        try: h.format_floating_point(23.5)
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.format_floating_point didn't raise expected NotImplementedError."

        try: h.check_comment_line('foo')
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.check_comment_line didn't raise expected NotImplementedError."

        try: h.check_name([])
        except NotImplementedError: pass
        else: raise AssertionError, "HeaderFile.check_name didn't raise expected NotImplementedError."

    def test_base(self):
        "Test high-level features of base class."
        h = DummyHeaderFile()

        # Check various insertion commands and their return values.
        assert h.Verbatim('** top1', position='top') == '** top1'
        assert h.Comment('foo bar') == 'Cfoo bar\n'
        assert h.Comment('shmoo\nbar\n') == 'Cshmoo bar\n'
        assert h.Verbatim('** top2', position='top') == '** top2'
        assert h.Verbatim('** bottom1', position='bottom') == '** bottom1'
        assert h.Comment('baz\nbar\n', nowrap=True) == 'Cbaz\nCbar\n'
        assert h.Definition('foo', None) == '\nUfoo\n'
        assert h.Definition('foo', 'bar') == '\nDfoo="bar\n'
        assert h.Definition('foo', 'bar', verbatim=True) == '\nDfoo=bar\n'
        assert h.Definition('foo', 23) == '\nDfoo=23\n'
        assert h.Verbatim('** bottom2', position='bottom') == '** bottom2'
        assert h.Definition('foo', 23.5) == '\nDfoo=23.5\n'
        assert h.Definition('foo', None, comment='foo bar') == '\nCfoo bar\nUfoo\n'
        assert h.Definition('foo', None, comment='foo\nbar\n\n') == '\nCfoo bar\nUfoo\n'
        assert h.Definition('foo', None, comment='foo\nbar\n\n', nowrap=True) == '\nCfoo\nCbar\nUfoo\n'
        assert h.Verbatim('** bottom3', position='bottom') == '** bottom3'
        assert h.Verbatim('** top3', position='top') == '** top3'

        # Check name and comment syntax checks.
        try: h.Comment("Well ain't that cute... but it's WRONG!!!")
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.Header.Comment() didn't raise expected UserError on invalid comment."

        try: h.Definition('foo bar', 23)
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.Header.Definition() didn't raise expected UserError on invalid identifier."

        try: h.Template('foo bar', 'A foo and a bar.')
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.Header.Definition() didn't raise expected UserError on invalid identifier."

        try: h.Template('three', 'Something is WRONG.')
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.Header.Definition() didn't raise expected UserError on invalid identifier."

        # High-level template and dictionary access
        h['one'] = 1
        h['two'] = 'II'
        h['three'] = 3.
        h.Template('two', 'The number Two in Roman', 23)
        h.Template('fifteen', 'Fifteeen', 15)
        h.Template('twentythree', 'Twenty and three')
        h.Template('twentyfive', 'Five times five')
        h.Template('fourtytwo', 'The Answer', 'fourty two')
        h['twentyfive'] = 25
        h['fourtytwo'] = 42

        # Check final text of header file
        expected_text = \
              '** top3\n' \
              '** top2\n' \
              '** top1\n' \
              'Cfoo bar\n\n' \
              'Cshmoo bar\n\n' \
              'Cbaz\n' \
              'Cbar\n\n\n' \
              'Ufoo\n\n\n' \
              'Dfoo="bar\n\n\n' \
              'Dfoo=bar\n\n\n' \
              'Dfoo=23\n\n\n' \
              'Dfoo=23.5\n\n\n' \
              'Cfoo bar\n' \
              'Ufoo\n\n\n' \
              'Cfoo bar\n' \
              'Ufoo\n\n\n' \
              'Cfoo\n' \
              'Cbar\n' \
              'Ufoo\n\n\n' \
              'CFifteeen\nDfifteen=15\n\n\n' \
              'CThe Answer\nDfourtytwo=42\n\n\n' \
              'Done=1\n\n\n' \
              'Dthree=3.0\n\n\n' \
              'CFive times five\nDtwentyfive=25\n\n\n' \
              'CTwenty and three\nUtwentythree\n\n\n' \
              'CThe number Two in Roman\nDtwo="II\n\n' \
              '** bottom1\n' \
              '** bottom2\n' \
              '** bottom3\n'

        assert h.Text() == expected_text, h.Text()

        sio = StringIO.StringIO()
        h.Write(sio)
        assert sio.getvalue() == expected_text, sio.getvalue()
        
    def test_cheader(self):
        "Test CHeaderFile concrete class."
        h = CHeaderFile()

        # Valid comment and definitions should not raise UserError
        h.Comment("/* foo bar")
        h.Definition('foobar', 23)
        h.Definition('foo_bar', 23)
        h.Definition('_foo_bar', 23)
        h.Definition('foo_bar5', 23)
        h.Definition('foo5bar', 23)

        # Invalid comment and definitions should do raise UserError
        try: h.Comment("*/")
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.CHeader.Comment() didn't raise expected UserError on invalid comment."

        try: h.Definition('foo-bar', 23)
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.CHeader.Definition() didn't raise expected UserError on invalid identifier."

        try: h.Definition('foo bar', 23)
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.CHeader.Definition() didn't raise expected UserError on invalid identifier."

        try: h.Definition('!foobar', 23)
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.CHeader.Definition() didn't raise expected UserError on invalid identifier."

        try: h.Definition('5foobar', 23)
        except SCons.Errors.UserError: pass
        else: raise AssertionError, "SCons.Header.CHeader.Definition() didn't raise expected UserError on invalid identifier."

        # Check low-level formatting
        assert h.format_definition('a', 'b') == '#define a b'
        assert h.format_undefinition('a') == '/* #undef a */'
        assert h.format_string('abc') == '"abc"'
        assert h.format_string('ab"c') == '"ab\\"c"'
        assert h.format_string('a\tb\r\nc\a') == '"a\\tb\\r\\nc\\a"'
        assert h.format_string('a\\bc') == '"a\\\\bc"'
        assert h.format_integer(23) == '23'
        assert h.format_integer(23000000000000000) == '23000000000000000' # Header class doesn't do data range checks by design.
        assert h.format_floating_point(23.125) == '23.125'

if __name__ == "__main__":
    suite = unittest.makeSuite(HeaderTestCase, 'test_')
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        sys.exit(1)
