__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import TestCmd
import SCons.Scanner.C
import unittest
import sys

test = TestCmd.TestCmd(workdir = '')

# create some source files and headers:

test.write('f1.cpp',"""
#include \"f1.h\"
#include <f2.h>

int main()
{
   return 0;
}
""")

test.write('f2.cpp',"""
#include \"d1/f1.h\"
#include <d2/f1.h>
#include \"f1.h\"
#include <f4.h>

int main()
{
   return 0;
}
""")

test.write('f3.cpp',"""
#include \t "f1.h"
   \t #include "f2.h"
#   \t include "f3.h"

#include \t <d1/f1.h>
   \t #include <d1/f2.h>
#   \t include <d1/f3.h>

// #include "never.h"

const char* x = "#include <never.h>"

int main()
{
   return 0;
}
""")


# for Emacs -> "

test.subdir('d1', ['d1', 'd2'])

headers = ['f1.h','f2.h', 'f3.h', 'never.h',
           'd1/f1.h', 'd1/f2.h', 'd1/f3.h',
           'd1/d2/f1.h', 'd1/d2/f2.h', 'd1/d2/f3.h', 'd1/d2/f4.h']

for h in headers:
    test.write(h, " ")

# define some helpers:

class DummyEnvironment:
    pass

def deps_match(deps, headers):
    return deps.sort() == map(test.workpath, headers).sort()

# define some tests:

class CScannerTestCase1(unittest.TestCase):
    def runTest(self):
        env = DummyEnvironment
        s = SCons.Scanner.C.CScan()
        deps = s.scan(test.workpath('f1.cpp'), env)
        self.failUnless(deps_match(deps, ['f1.h', 'f2.h']))

class CScannerTestCase2(unittest.TestCase):
    def runTest(self):
        env = DummyEnvironment
        env.CPPPATH = [test.workpath("d1")]
        s = SCons.Scanner.C.CScan()
        deps = s.scan(test.workpath('f1.cpp'), env)
        headers = ['f1.h', 'd1/f2.h']
        self.failUnless(deps_match(deps, headers)) 

class CScannerTestCase3(unittest.TestCase):
    def runTest(self):
        env = DummyEnvironment
        env.CPPPATH = [test.workpath("d1")]
        s = SCons.Scanner.C.CScan()
        deps = s.scan(test.workpath('f2.cpp'), env)
        headers = ['f1.h', 'd1/f2.h', 'd1/d2/f1.h']
        self.failUnless(deps_match(deps, headers))
                  

class CScannerTestCase4(unittest.TestCase):
    def runTest(self):
        env = DummyEnvironment
        env.CPPPATH = [test.workpath("d1"), test.workpath("d1/d2")]
        s = SCons.Scanner.C.CScan()
        deps = s.scan(test.workpath('f2.cpp'), env)
        headers =  ['f1.h', 'd1/f2.h', 'd1/d2/f1.h', 'd1/d2/f4.h']
        self.failUnless(deps_match(deps, headers))
        
class CScannerTestCase5(unittest.TestCase):
    def runTest(self):
        env = DummyEnvironment
        s = SCons.Scanner.C.CScan()
        deps = s.scan(test.workpath('f3.cpp'), env)
        headers =  ['f1.h', 'f2.h', 'f3.h', 'd1/f1.h', 'd1/f2.h', 'd1/f3.h']
        self.failUnless(deps_match(deps, headers))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(CScannerTestCase1())
    suite.addTest(CScannerTestCase2())
    suite.addTest(CScannerTestCase3())
    suite.addTest(CScannerTestCase4())
    suite.addTest(CScannerTestCase5())
    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    result = runner.run(suite())
    if not result.wasSuccessful():
        sys.exit(1)
