import os.path
import TestSCons


dir1, dir2, testdir = 'pyfiles', 'pyfiles2', 'pybuilderdir'
hellofile = 'hello.py'
hello2file = 'hello2.py'

test = TestSCons.TestSCons()

def pybuilder_test(pysuffix):
    hellopycfile = hellofile + pysuffix
    hello2pycfile = hello2file + pysuffix

    hellocode = r"""
#!/usr/bin/env python
print 'Hello world'
"""

    hello2code = r"""
#!/usr/bin/env python
print 'Hello world version 2'
"""

    test.subdir(dir1, dir2)


    test.write([dir1, hellofile], hellocode)
    test.write([dir1, hello2file], hello2code)

    test.write([dir2, hellofile], hellocode)
    test.write([dir2, hello2file], hello2code)

    test.run(arguments = '-Q install')

    testdir1 = os.path.join(testdir, dir1)
    testdir2 = os.path.join(testdir, dir2)

    dir1hello1 = os.path.join(testdir1, hellofile)
    dir1hello1pyco = dir1hello1 + pysuffix
    dir1hello2 = os.path.join(testdir1, hello2file)
    dir1hello2pyco = dir1hello2 + pysuffix
    dir2hello1 = os.path.join(testdir2, hellofile)
    dir2hello1pyco = dir2hello1 + pysuffix
    dir2hello2 = os.path.join(testdir2, hello2file)
    dir2hello2pyco = dir2hello2 + pysuffix

    files = dir1hello1, dir1hello1pyco, dir1hello2, dir1hello2pyco,\
            dir2hello1, dir2hello1pyco, dir2hello1, dir2hello2pyco

    for filename in files:
        test.must_exist(test.workpath(filename))

    test.must_match(dir1hello1, hellocode)
    test.must_match(dir2hello1, hellocode)
    test.must_match(dir1hello2, hello2code)
    test.must_match(dir2hello2, hello2code)

    test.fail_test(not os.path.getsize(test.workpath(dir1hello1pyco)))
    test.fail_test(not os.path.getsize(test.workpath(dir1hello2pyco)))
    test.fail_test(not os.path.getsize(test.workpath(dir2hello1pyco)))
    test.fail_test(not os.path.getsize(test.workpath(dir2hello2pyco)))

test.write('SConstruct',
"""
env = Environment()
hello = File('%s/%s')
hello2 = File('%s/%s')
pydir = Dir('%s')
env.InstallPython('%s', [hello, hello2, pydir])
env.Alias('install', '%s')
""" % (dir1, hellofile, dir1, hello2file, dir2, testdir, testdir))

# test for 'pyc' files
pybuilder_test('c')


test.write('SConstruct',
"""
env = Environment(PYSUFFIX = "PYO")
hello = File('%s/%s')
hello2 = File('%s/%s')
pydir = Dir('%s')
env.InstallPython('%s', [hello, hello2, pydir])
env.Alias('install', '%s')
""" % (dir1, hellofile, dir1, hello2file, dir2, testdir, testdir))

# test for 'pyo' files
pybuilder_test('o')
