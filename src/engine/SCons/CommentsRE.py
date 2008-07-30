"""SCons.CommentsRE

Alternative Comments module. This one is partly based on regular expressions
instead of reading whole file in while loops. Functions in this module
are faster than the old ones.

At the moment this module *is not* perfectly replaceable with SCons.Comments
module. Functions names are the same, but the behaviour of StripCComment
especially is not. The differences are easily traceable by diff'ing 
test/Comments.py and test/CommentsRE.py files.
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

def quot_regexp(c):
    """Returns a regular expression that matches a region delimited by c,
    inside which c may be escaped with a backslash."""

    return r"(%s(?:\\.|[^%s])*%s)" % (c, c, c)

def oneline_comment_regexp(chars):
    """Returns a regular expression that matches a region beginning with
    'chars' and ending with new line."""

    return r"(%s[^\n]*\n)" % (chars)

def multiline_comment_regexp(begin_string, end_string):
    """Returns a regular expression that matches a region beginning with
    begin_string and ending with end_string."""

    return r"(%s.*?%s)" % (begin_string, end_string)

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

    list_or_tuple = (type((None, )), type([None]))

    if type(patterns) not in list_or_tuple:
        patterns = (patterns, )

    try:
        contents = open(filename).read()
    except:
        return ''

    pattern = re.compile('|'.join(patterns), re.DOTALL)
    contents = re.sub(quotes_pat, '', contents)
    contents = ''.join([''.join(i) for i in pattern.findall(contents)])
    return re.sub(whitespaces, '', contents)

def GenericStripComments(filename, patterns, quotings=('"', "'"), comment_first_chars=('//','/\*'), preprocessor = False):
    """GenericStripComments() function returns contents
    of the 'filename' file except of strings that fit regular
    expressions defined in 'patterns' tuple.

    'patterns' may be a string, list or tuple containing regular expression
    strings ready to be compiled with re.compile() function.

    'quotings' is a tuple of characters, each of which marks beginning
    (and end) of a string. Patterns from the 'patterns' argument found
    between the 'quotings' characters won't be stripped.

    'comment_first_chars' is a tuple that defines signs that comments
    start with. For C-like comments comment_first_chars is equal to
    ('//', '/\*').

    When 'preprocessor' is True GenericStripComments() won't strip
    whitespaces from the lines that start with '#' sign.
    """

    # patterns must be a list, but it may be passed as a tuple or string
    if type(patterns) == type((None, )):
        patterns = list(patterns)
    elif type(patterns) == type(''):
        patterns = [patterns]

    # comment_first_chars must be tuple or list, but may be passed as string
    list_or_tuple = (type((None, )), type([None]))
    if type(comment_first_chars) not in list_or_tuple:
        comment_first_chars = (comment_first_chars, )
    
    # quotings must be a tuple or list, but may be passed as string
    if type(quotings) not in list_or_tuple:
        quotings = (quotings, )

    for quoting_char in quotings:
        # We got to insert the quoting regexp at the beginning of
        # patterns list to match quoted comments before we try to
        # match real comments.
        patterns.insert(0, quot_regexp(quoting_char))

    if preprocessor:
        # We try to match all the preprocessor lines; for every line
        # except the first line the pattern '(?:\n)(#.*?\n)' works fine,
        # but in case the first line in file is a preprocessor line
        # we got to search for '(?:^)(#.*?\n)' as well.
        patterns.insert(0, '(?:\n|^)(#.*?\n)')

    # We got all the patterns:
    #  - preprocessor pattern if 'preprocessor' argument is True
    #  - patterns for quotes (we don't want to strip comments inside quotes)
    #  - patterns for comments to strip
    # so let's compile them now.
    pattern = re.compile('|'.join(patterns), re.DOTALL)

    # drop strings that start with comment signs
    cfc_pat = re.compile('^(?:' + '|'.join(comment_first_chars) + ')')
    startswithcomment = lambda x: cfc_pat.search(x)

    # drop strings that start with quote signs
    quotings_pat = re.compile('^(?:' + '|'.join(quotings) + ')')
    startswithquoting = lambda x: quotings_pat.search(x)

    try:
        contents = open(filename).read()
    except:
        return ''

    new_buf = ['']
    buf_split = re.split(pattern, contents)
    for i in buf_split:
        if i:
            if startswithcomment(i):
                if preprocessor:
                    new_buf.append('')
                continue
            elif startswithquoting(i):
                new_buf[-1] = new_buf[-1] + i
                continue
            # don't strip the whitespaces for preprocessor lines
            elif preprocessor and i.startswith('#'):
                new_buf[-1] = new_buf[-1] + i
                continue
            # couldn't match the string, so just strip the whitespaces
            # and add it to the buffer
            new_buf[-1] = new_buf[-1] + re.sub('[ \n\r\t]', '', i)

    # add spaces wherever there was a comment
    return ' '.join(new_buf)


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

    return GenericStripComments(filename, (c_comment, cxx_comment),
                                                preprocessor = True)

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

    return GenericStripComments(filename, (d_comment, c_comment, cxx_comment),
                                     comment_first_chars = ('/\+', '/\*', '//'))


def StripFortranComments(filename):
    return GenericStripComments(filename, (oneline_comment_regexp('!')),
                                               comment_first_chars = '!')

def StripFortranCode(filename):
    return GenericStripCode(filename, oneline_comment_regexp('!'))

def StripHashComments(filename):
    return GenericStripComments(filename, oneline_comment_regexp('#'),
                                             comment_first_chars = '#')

def StripHashCode(filename):
    return GenericStripCode(filename, oneline_comment_regexp('#'))
