"""SCons.CommentsRE

Alternative Comments module. This one is partly based on regular expressions
instead of reading whole file in while loops. Functions in this module
are faster than the old ones.

At the moment this module is perfectly replaceable with SCons.Comments
module (the tests for old SCons.Comments shall be passed by functions in
CommentsRE module).

At the moment:
 - all Strip*Code() functions work (but REs are not optimized yet),
 - all Strip*Comments() functions work (but REs are supported by
   whitespaces_filter() function which uses while loops)
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

# based on Jeff Epler's idea:
# http://mail.python.org/pipermail/python-list/2005-July/333370.html

# TODO: 
#   - add RE which is able to strip whitespaces from the whole buffer
#     but not from the quotings (change '   printf("    ");    ' into
#     'printf("     ");'). At the moment whitespaces_filter() function
#     does this.


def string_to_buf(txt, i, len_max, end_char='"'):
    """Extract string from the buffer. The string starts at
    the position 'i' in the buffer 'txt' and ends with the
    sign 'end_char'.

    Function string_to_buf() takes four arguments:
    'txt' - file contents (as a string or list of characters)
    'i' - current position in the file (when calling
          string_to_buf() 'i' *must* be a string opening char)
    'len_max' - length of the string/list 'txt'
    'end_char' - sign closing the string (default: '"')

    Returns a tuple: extracted string as a list of characters
    and the current position in the buffer (first sign after
    the extracted string).

    This function is escaped-quotes sensitive."""

    metachars = 0
    buf = []
    buf.append(txt[i])
    i += 1
    try:
        while i < len_max:
            if txt[i] == '\\':
                metachars += 1
                buf.append(txt[i])
                i += 1
                continue
            elif txt[i] == end_char:
                if metachars % 2:
                    buf.append(txt[i])
                    i += 1
                    metachars = 0
                    continue
                buf.append(txt[i])
                i += 1
                break
            buf.append(txt[i])
            i += 1
            metachars = 0
    except IndexError:
        return buf, i
    return buf, i


def whitespaces_filter(txt, preprocessor=False):
    """Strips the whitespaces (' ', '\t', '\n' and '\r') from the
    buffer 'txt', but leaves the whitespaces within the quotes
    (and within the lines that start with '#' sign when the 'preprocessor'
    flag is True).

    In other words whitespaces_filter() changes the string:
    '\n \r \t" \n\"\r" \t' into: '" \n\"\r"'.

    This function is escaped-quotes sensitive."""

    i = 0
    len_max = len(txt)
    buf = []
    whitespaces = ' \t\n\r'
    while i < len_max:
        # add double-quoted string to the buffer
        if txt[i] == '"':
            new_buf, i = string_to_buf(txt, i, len_max)
            buf.extend(new_buf)
        elif txt[i] == "'":
            new_buf, i = string_to_buf(txt, i, len_max, "'")
            buf.extend(new_buf)
        # add single-quoted string to the buffer
        elif preprocessor and txt[i] == '#':
            new_buf, i = string_to_buf(txt, i, len_max, '\n')
            buf.extend(new_buf)
        else:
            if not (txt[i] in whitespaces):
                buf.append(txt[i])
            i += 1

    return ''.join(buf)

def quot_regexp(c):
    """Returns a regular expression that matches a region delimited by c,
    inside which c may be escaped with a backslash."""

    return r"%s(\\.|[^%s])*%s" % (c, c, c)

def oneline_comment_regexp(chars):
    """Returns a regular expression that matches a region beginning with
    'chars' and ending with new line."""

    return r"%s[^\n]*\n" % (chars)

def multiline_comment_regexp(begin_string, end_string):
    """Returns a regular expression that matches a region beginning with
    begin_string and ending with end_string."""

    return r"%s.*?%s" % (begin_string, end_string)

def comments_replace(x, char='#'):
    """Returns empty string for a string that starts with 'char' character
    or the string itself otherwise."""

    x = x.group(0)
    if x.startswith(char):
        return ''
    return x

single_quoted_string = quot_regexp("'")
double_quoted_string = quot_regexp('"')

whitespaces = "[ \n\r\t]"

c_comment = multiline_comment_regexp(r"/\*", r"\*/")
d_comment = multiline_comment_regexp(r"/\+", r"\+/")

cxx_comment = oneline_comment_regexp('//')

quotes_pat = re.compile('|'.join([single_quoted_string,
                                  double_quoted_string]),
                                  re.DOTALL)

def GenericStripCode(filename, patterns):
    """GenericStripCode() function returns strings that fit
    regular expressions defined in 'patterns' tuple from
    the 'filename' file."""

    if type(patterns) != type((None, None)):
        patterns = (patterns, )

    try:
        contents = open(filename).read()
    except:
        return ''

    pattern = re.compile('|'.join(patterns), re.DOTALL)
    contents = re.sub(quotes_pat, '', contents)
    contents = ''.join(pattern.findall(contents))
    return re.sub(whitespaces, '', contents)

def GenericStripComments(filename, patterns, comment_first_chars=('/',), preprocessor = False):
    """GenericStripComments() function returns contents
    of the 'filename' file except of strings that fit regular
    expressions defined in 'patterns' tuple.

    'comment_first_chars' is a tuple that defines signs that comments
    start with. For C-like comments comment_first_chars is equal to
    ('/',), because '/' sign fits for '/* ... */' comments as well
    as '// ...' comments.

    When 'preprocessor' is True GenericStripComments won't strip
    whitespaces from the lines that start with '#' sign.
    """

    if type(patterns) != type((None, None)):
        patterns = (patterns, )

    if type(comment_first_chars) != type((None, None)):
        comment_first_chars = (comment_first_chars, )

    try:
        contents = open(filename).read()
    except:
        return ''

    pattern = re.compile('|'.join(patterns), re.DOTALL)

    for first_char in comment_first_chars:
        def generic_replace(x):
            return comments_replace(x, first_char)

        contents = pattern.sub(generic_replace, contents)

    return whitespaces_filter(contents, preprocessor)


def StripCCode(filename):
    """Strip the code from the file and return comments.

    Open the file 'filename', get the contents, strip the source code
    and return comments.

    Works for '//' and '/* */' comments."""

    return GenericStripCode(filename, (c_comment, cxx_comment))

def StripCComments(filename):
    """Strip C-like comments from the file and return source code.

    Open the file 'filename', get the contents, strip the comments
    and return source code.

    Works for '//' and '/* */' comments."""

    return GenericStripComments(filename, (single_quoted_string,
                                           double_quoted_string,
                                           c_comment,
                                           cxx_comment), preprocessor = True)

def StripDCode(filename):
    """Strip the code from the file and return comments.

    Open the file 'filename', get the contents, strip the code
    and return the comments.

    Works for '//', '/* */' and '/+ +/' comments."""

    return GenericStripCode(filename, (d_comment, c_comment, cxx_comment))


def StripDComments(filename):
    """Strip D-like comments from the file and return source code.
    
    Open the file 'filename', get the contents, strip the comments
    and return source code.
    
    Works for '//', '/* */' and '/+ +/' comments."""

    return GenericStripComments(filename, (single_quoted_string,
                                           double_quoted_string,
                                           d_comment,
                                           c_comment,
                                           cxx_comment))


def StripFortranComments(filename):
    return GenericStripComments(filename, (single_quoted_string,
                                           double_quoted_string,
                                           oneline_comment_regexp('!')),
                                             comment_first_chars = '!')

def StripFortranCode(filename):
    return GenericStripCode(filename, oneline_comment_regexp('!'))

def StripHashComments(filename):
    return GenericStripComments(filename, (single_quoted_string,
                                           double_quoted_string,
                                           oneline_comment_regexp('#')),
                                             comment_first_chars = '#')

def StripHashCode(filename):
    return GenericStripCode(filename, oneline_comment_regexp('#'))

