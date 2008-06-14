import TestSCons
import Comments


# test C-stripper

cfile = 'ccomments.c'
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


test = TestSCons.TestSCons()

test.subdir('C-one', 'C-two', 'D-one', 'D-two', 'py-one', 'py-two', 'fortran-one', 'fortran-two')

test.write(['C-one', cfile], ccode)

test.write(['C-one', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.CComments('ccomments.c'))
""")

test.run(chdir = 'C-one', arguments = '-q -Q', stdout = r"""#include<stdio.h>intmain(void){intw=10+1;charx='\'';chary='\n';printf("not comment\n\\\"\\");printf("\"/\\/* not comment\"/\\/*\n");printf("'///*not comment*/'");printf("/");printf("/**\"not comment*/");return0;}
""")



test.write(['C-two', cfile], ccode)

test.write(['C-two', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.CCode('ccomments.c'))
""")


test.run(chdir = 'C-two', arguments = '-q -Q', stdout = r"""/*multiline*comment*//*comment*///two-slashes-comment//two-slashes-comment/*comment*/
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


test.write(['D-one', dfile], dcode)

test.write(['D-one', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.DComments('dcomments.d'))
""")

test.run(chdir = 'D-one', arguments = '-q -Q', stdout = r"""importstd.stdio;voidmain(){writefln("/+\" not \\\\\"comment\" +/");writefln("//\\\\\" not comment");writefln("/* not comment */");}
""")


test.write(['D-two', dfile], dcode)

test.write(['D-two', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.DCode('dcomments.d'))
""")


test.run(chdir = 'D-two', arguments = '-q -Q', stdout = r"""/+thisisanembeddedcomment/*thisisacommentwithinanembeddedcomment*/+////+comment+//*comment*//+comment+///comment
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

test.write(['py-one', pyfile], pycode)

test.write(['py-one', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.Comments('pycomments.py'))
""")

test.run(chdir = 'py-one', arguments = '-q -Q', stdout = r"""print"#!notcomment\\\\\""print'#!notcomment'print'"#!notcomment"'print"'#!notcomment'"
""")



test.write(['py-two', pyfile], pycode)

test.write(['py-two', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.Code('pycomments.py'))
""")


test.run(chdir = 'py-two', arguments = '-q -Q', stdout = r"""#!/usr/bin/envpython#comment#comment#comment#comment#comment#comment
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

test.write(['fortran-one', ffile], fcode)

test.write(['fortran-one', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.Comments('fcomments.f90', '!'))
""")

test.run(chdir = 'fortran-one', arguments = '-q -Q', stdout = r"""programhelloprint*,"!notcomment"print*,'!notcomment'print*,'"!notcomment"'print*,"'!notcomment'"endprogramhello
""")


test.write(['fortran-two', ffile], fcode)

test.write(['fortran-two', 'SConstruct'],
      """
import Comments
print r"%s" % (Comments.Code('fcomments.f90', '!'))
""")


test.run(chdir = 'fortran-two', arguments = '-q -Q', stdout = r"""!comment!comment!comment!comment
""")
