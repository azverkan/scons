"""SCons.CommentsRE

Alternative Comments module. This one is partly based on regular expressions
instead of reading whole file in while loops. When finished, functions
in this module should be faster than the old ones.

At the moment this module is perfectly replaceable with SCons.Comments
module (the tests for old SCons.Comments shall be passed by functions in
CommentsRE module as well).

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
import sys

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
    chars and ending with new line."""

    return r"%s[^\n]*[\n]" % (chars)

def comments_replace(x, char='#'):
    """Returns empty string for a string that starts with 'char' character
    or the string itself otherwise."""
    x = x.group(0)
    if x.startswith(char):
        return ''
    return x

def slash_comments_replace(x):
    return comments_replace(x, '/')

def exclamation_comments_replace(x):
    return comments_replace(x, '!')

def hash_comments_replace(x):
    return comments_replace(x, '#')

single_quoted_string = quot_regexp("'")
double_quoted_string = quot_regexp('"')

whitespaces = "[ \n\r\t]"

c_comment = r"/\*.*?\*/" # matches '/* ... */' comments
d_comment = r"/\+.*?\+/" # matches '/+ ... +/' comments

hash_comment = oneline_comment_regexp('#')
exclamation_comment = oneline_comment_regexp('!')
cxx_comment = oneline_comment_regexp('//')

quotes_pat = re.compile('|'.join([single_quoted_string,
                                  double_quoted_string]),
                                  re.DOTALL)

# strip CPP-like comments (applicable for C, C++, JAVA)
c_comments_pat = re.compile("|".join([single_quoted_string,
                                      double_quoted_string,
                                      c_comment,
                                      cxx_comment]),
                                      re.DOTALL)

c_code_pat = re.compile("|".join([c_comment,
                                  cxx_comment]), re.DOTALL)


# strip D-like comments
d_comments_pat = re.compile("|".join([single_quoted_string,
                                      double_quoted_string,
                                      d_comment,
                                      c_comment,
                                      cxx_comment]), re.DOTALL)

d_code_pat = re.compile('|'.join([d_comment,
                                  c_comment,
                                  cxx_comment]), re.DOTALL)

hash_comments_pat = re.compile('|'.join([single_quoted_string,
                                         double_quoted_string,
                                         hash_comment]), re.DOTALL)

hash_code_pat = re.compile('|'.join([hash_comment]), re.DOTALL)


# fortran
exclamation_comments_pat = re.compile('|'.join([single_quoted_string,
                                                double_quoted_string,
                                                exclamation_comment]),
                                                re.DOTALL)

exclamation_code_pat = re.compile('|'.join([exclamation_comment]), re.DOTALL)


def StripCCode(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = re.sub(quotes_pat, '', contents)
    contents = ''.join(c_code_pat.findall(contents))
    return re.sub(whitespaces, '', contents)


def StripCComments(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = c_comments_pat.sub(slash_comments_replace, contents)
    return whitespaces_filter(contents, preprocessor = True)

def StripDCode(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = re.sub(quotes_pat, '', contents)
    return re.sub(whitespaces, '', ''.join(d_code_pat.findall(contents)))

def StripDComments(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = d_comments_pat.sub(slash_comments_replace, contents)
    return whitespaces_filter(contents)


def StripComments(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = hash_comments_pat.sub(hash_comments_replace, contents)
    return whitespaces_filter(contents)

def StripCode(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = re.sub(quotes_pat, '', contents)
    contents = ''.join(hash_code_pat.findall(contents))
    return re.sub(whitespaces, '', contents)

def StripFortranComments(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = exclamation_comments_pat.sub(exclamation_comments_replace, contents)
    return whitespaces_filter(contents)

def StripFortranCode(filename):
    try:
        contents = open(filename).read()
    except:
        return ''
    contents = re.sub(quotes_pat, '', contents)
    contents = ''.join(exclamation_code_pat.findall(contents))
    return re.sub(whitespaces, '', contents)


#print StripCCode('c.c')
#print StripCComments('c.c')
#print StripDCode('d.d')
#print StripDComments('d.d')
#print StripCode('hello.py')
#print StripComments('hello.py')
#print StripFortranCode('hello.f90')
#print StripFortranComments('hello.f90')
