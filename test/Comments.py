import TestSCons

# test C-stripper

cfile = 'ccomments.c'
cofile = 'ccomments.o'
ccode = r"""
#include <stdio.h>
/* multiline
 * comment
 */
int main(void)
{
   int w = 10 + /* comment */ 1;
   char x = '\'';
   char y = '\n';
   printf("not comment\n\\\"\\");
   printf("\"/\\/* not comment\"/\\/*\n"); // two-slashes-comment
   printf("'///*not comment*/'"); // two-slashes-comment
   printf("/"); /* comment */
   printf("/**\"not comment*/");
   return 0;
}
"""

# quote in first printf() changed
ccode_quote_changed = r"""
#include <stdio.h>
/* multiline
 * comment
 */
int main(void)
{
   int w = 10 + /* comment */ 1;
   char x = '\'';
   char y = '\n';
   printf("CHANGE HERE\n\\\"\\");
   printf("\"/\\/* not comment\"/\\/*\n"); // two-slashes-comment
   printf("'///*not comment*/'"); // two-slashes-comment
   printf("/"); /* comment */
   printf("/**\"not comment*/");
   return 0;
}
"""



# changed 'int w = 10' into 'int w = 11'
ccode_code_changed = r"""
#include <stdio.h>
/* multiline
 * comment
 */
int main(void)
{
   int w = 11 + /* comment */ 1;
   char x = '\'';
   char y = '\n';
   printf("not comment\n\\\"\\");
   printf("\"/\\/* not comment\"/\\/*\n"); // two-slashes-comment
   printf("'///*not comment*/'"); // two-slashes-comment
   printf("/"); /* comment */
   printf("/**\"not comment*/");
   return 0;
}
"""


test = TestSCons.TestSCons()

subdirs = 'C-one', 'C-two', 'D-one', 'D-two', 'py-one', 'py-two', 'fortran-one', 'fortran-two', 'sig-check1'

#test.subdir('C-one', 'C-two', 'D-one', 'D-two', 'py-one', 'py-two', 'fortran-one', 'fortran-two', 'sigs-check1')

test.subdir(*subdirs)

test.write([subdirs[0], cfile], ccode)

test.write([subdirs[0], 'SConstruct'],
      """
from SCons.Comments import StripCComments
print r"%s" % (StripCComments('ccomments.c'))
""")

test.run(chdir = subdirs[0], arguments = '-q -Q', stdout = r"""#include<stdio.h>intmain(void){intw=10+1;charx='\'';chary='\n';printf("not comment\n\\\"\\");printf("\"/\\/* not comment\"/\\/*\n");printf("'///*not comment*/'");printf("/");printf("/**\"not comment*/");return0;}
""")



test.write([subdirs[1], cfile], ccode)

test.write([subdirs[1], 'SConstruct'],
      """
from SCons.Comments import StripCCode
print r"%s" % (StripCCode('ccomments.c'))
""")


test.run(chdir = subdirs[1], arguments = '-q -Q', stdout = r"""/*multiline*comment*//*comment*///two-slashes-comment//two-slashes-comment/*comment*/
""")



# test D-stripper



dfile = 'dcomments.d'
dcode = r"""
/+ this is an embedded comment
  /* this is a comment within an embedded comment */ +/

import std.stdio;

void main()
{
   writefln("/+\" not \\\\\"comment\" +/"); // /+ comment +/
   writefln("//\\\\\" not comment"); /* comment */
   writefln("/* not comment */"); /+ comment +/
} // comment
"""


test.write([subdirs[2], dfile], dcode)

test.write([subdirs[2], 'SConstruct'],
      """
from SCons.Comments import StripDComments
print r"%s" % (StripDComments('dcomments.d'))
""")

test.run(chdir = subdirs[2], arguments = '-q -Q', stdout = r"""importstd.stdio;voidmain(){writefln("/+\" not \\\\\"comment\" +/");writefln("//\\\\\" not comment");writefln("/* not comment */");}
""")


test.write([subdirs[3], dfile], dcode)

test.write([subdirs[3], 'SConstruct'],
      """
from SCons.Comments import StripDCode
print r"%s" % (StripDCode('dcomments.d'))
""")


test.run(chdir = subdirs[3], arguments = '-q -Q', stdout = r"""/+thisisanembeddedcomment/*thisisacommentwithinanembeddedcomment*/+////+comment+//*comment*//+comment+///comment
""")



# python-stripper test (char test)
pyfile = 'pycomments.py'
pycode = r"""
#!/usr/bin/env python

# comment
print "#! not comment\\\\\"" # comment
print '#! not comment' # comment
print '"#! not comment"' # comment
print "'#! not comment'" # comment
# comment
"""

test.write([subdirs[4], pyfile], pycode)

test.write([subdirs[4], 'SConstruct'],
      """
from SCons.Comments import StripComments
print r"%s" % (StripComments('pycomments.py'))
""")

test.run(chdir = subdirs[4], arguments = '-q -Q', stdout = r"""print"#! not comment\\\\\""print'#! not comment'print'"#! not comment"'print"'#! not comment'"
""")



test.write([subdirs[5], pyfile], pycode)

test.write([subdirs[5], 'SConstruct'],
      """
from SCons.Comments import StripCode
print r"%s" % (StripCode('pycomments.py'))
""")


test.run(chdir = subdirs[5], arguments = '-q -Q', stdout = r"""#!/usr/bin/envpython#comment#comment#comment#comment#comment#comment
""")



# fortran-stripper test (char test)

ffile = 'fcomments.f90'
fcode = r"""
! comment
program hello ! comment
   print *,"! not comment" ! comment
   print *,'! not comment'
   print *,'"! not comment"'
   print *,"'! not comment'"
end program hello
! comment
"""

test.write([subdirs[6], ffile], fcode)

test.write([subdirs[6], 'SConstruct'],
      """
from SCons.Comments import StripFortranComments
print r"%s" % (StripFortranComments('fcomments.f90'))
""")

test.run(chdir = subdirs[6], arguments = '-q -Q', stdout = r"""programhelloprint*,"! not comment"print*,'! not comment'print*,'"! not comment"'print*,"'! not comment'"endprogramhello
""")


test.write([subdirs[7], ffile], fcode)

test.write([subdirs[7], 'SConstruct'],
      """
from SCons.Comments import StripFortranCode
print r"%s" % (StripFortranCode('fcomments.f90'))
""")


test.run(chdir = subdirs[7], arguments = '-q -Q', stdout = r"""!comment!comment!comment!comment
""")


### comments stripper framework tests

test.write([subdirs[8], cfile], ccode)

test.write([subdirs[8], 'SConstruct'],
"""
env = Environment()
env.Program('%s')
""" % cfile)

# first compilation - should compile
test.run(chdir = subdirs[8], arguments = '-Q', stdout = r"""gcc -o %s -c %s
gcc -o ccomments %s
""" % (cofile, cfile, cofile))

# second try - up to date, so do not compile
test.run(chdir = subdirs[8], arguments = '-Q', stdout = r"""scons: `.' is up to date.
""")

# comment added - should not rebuild
test.write([subdirs[8], cfile], ccode + '// comment')

test.run(chdir = subdirs[8], arguments = '-Q', stdout = r"""scons: `.' is up to date.
""")

# code changed - should rebuild
test.write([subdirs[8], cfile], ccode_code_changed)

test.run(chdir = subdirs[8], arguments = '-Q', stdout = r"""gcc -o %s -c %s
gcc -o ccomments %s
""" % (cofile, cfile, cofile))


# quote in printf() changed - should rebuild
test.write([subdirs[8], cfile], ccode_quote_changed)

test.run(chdir = subdirs[8], arguments = '-Q', stdout = r"""gcc -o %s -c %s
gcc -o ccomments %s
""" % (cofile, cfile, cofile))

# no changes - do not rebuild
test.run(chdir = subdirs[8], arguments = '-Q', stdout = r"""scons: `.' is up to date.
""")

