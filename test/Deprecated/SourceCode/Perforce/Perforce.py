#!/usr/bin/env python
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

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

"""
Test fetching source files from Perforce.

This test requires that a Perforce server be running on the test system
on port 1666, as well as that of course a client must be present.
"""

import os

import TestSCons

test = TestSCons.TestSCons()

test.write('SConscript', """
Environment(tools = ['Perforce']).Perforce()
""")

msg_p4 = """The Perforce() factory is deprecated and there is no replacement."""
warn_p4 = test.deprecated_fatal('deprecated-build-dir', msg_p4)
msg_sc = """SourceCode() has been deprecated and there is no replacement.
\tIf you need this function, please contact dev@scons.tigris.org."""
warn_sc = test.deprecated_wrap(msg_sc)

class TestPerforce(TestSCons.TestSCons):
    def __init__(self, *args, **kw):
        TestSCons.TestSCons.__init__(self, *args, **kw)

        self.p4d = None

        self.p4path = self.where_is('p4')
        if not self.p4path:
            self.skip_test("Could not find 'p4'; skipping test(s).\n")

        #import socket
        #self.host = socket.gethostname()
        self.host = '127.0.0.1'

        self.user = os.environ.get('USER')
        if not self.user:
            self.user = os.environ.get('USERNAME')
        if not self.user:
            self.user = os.environ.get('P4USER')

        self.depot = 'testme'

        self.p4d = self.where_is('p4d')
        if self.p4d:
            self.p4portflags = ['-p', self.host + ':1777']
            self.subdir('depot', ['depot', 'testme'])
            def quote_space(a):
                if ' ' in a:
                    a = '"%s"' % a
                return a
            args = list(map(quote_space, [self.p4d, '-q', '-d'] + \
                                    self.p4portflags + \
                                    ['-J', 'Journal',
                                     '-L', 'Log',
                                     '-r', self.workpath('depot')]))

            # We don't use self.run() because the TestCmd logic will hang
            # waiting for the daemon to exit, even when we pass it
            # the -d option.
            try:
                spawnv = os.spawnv
            except AttributeError:
                os.system(' '.join(args))
            else:
                spawnv(os.P_NOWAIT, self.p4d, args)
                self.sleep(2)
        else:
            import socket
            s = socket.socket()
            host_port = (self.host, 1666)
            try:
                s.connect(host_port)
            except socket.error:
                self.skip_test("No Perforce server found; skipping test(s).\n")
            else:
                s.close()

            self.p4portflags = ['-p', '%s:%s' % host_port]
            try:
                self.p4('obliterate -y //%s/...' % self.depot)
                self.p4('depot -d %s' % self.depot)
            except TestSCons.TestFailed:
                # It's okay if this fails.  It will fail if the depot
                # is already clear.
                pass

        self.portflag = ' '.join(self.p4portflags)

    def p4(self, *args, **kw):
        try:
            arguments = kw['arguments']
        except KeyError:
            arguments = args[0]
            args = args[1:]
        kw['arguments'] = ' '.join(self.p4portflags + [arguments])
        kw['program'] = self.p4path
        return self.run(*args, **kw)

    def substitute(self, s, **kw):
        kw = kw.copy()
        kw.update(self.__dict__)
        return s % kw

    def cleanup(self, condition = None):
        if self.p4d:
            self.p4('admin stop')
            self.p4d = None

        if TestSCons:
            TestSCons.TestSCons.cleanup(self, condition)

test = TestPerforce()

# Set up a perforce depot for testing.
depotspec = test.substitute("""\
# A Perforce Depot Specification.
Depot:  %(depot)s

Owner:  %(user)s

Date:   2003/02/19 17:21:41

Description:
        A test depot.

Type:   local

Address:        subdir

Map:    %(depot)s/...
""")

test.p4(arguments='depot -i', stdin = depotspec)

# Now set up 2 clients, one to check in some files, and one to
# do the building.
clientspec = """\
# A Perforce Client Specification.
Client: %(client)s

Owner:  %(user)s

Description:
        Created by %(user)s.

Root:   %(root)s

Options:        noallwrite noclobber nocompress unlocked nomodtime normdir

LineEnd:        local

View:
        //%(depot)s/%(subdir)s... //%(client)s/...
"""

clientspec1 = test.substitute(clientspec,
                              client = 'testclient1',
                              root = test.workpath('import'),
                              subdir = 'foo/',
                              )

clientspec2 = test.substitute(clientspec,
                              client = 'testclient2',
                              root = test.workpath('work'),
                              subdir = '',
                              )

test.subdir('import', ['import', 'sub'], 'work')

test.p4('client -i', stdin=clientspec1)
test.p4('client -i', stdin=clientspec2)

test.write(['import', 'aaa.in'], "import/aaa.in\n")
test.write(['import', 'bbb.in'], "import/bbb.in\n")
test.write(['import', 'ccc.in'], "import/ccc.in\n")

test.write(['import', 'sub', 'SConscript'], """
Import("env")
env.Cat('ddd.out', 'ddd.in')
env.Cat('eee.out', 'eee.in')
env.Cat('fff.out', 'fff.in')
env.Cat('all', ['ddd.out', 'eee.out', 'fff.out'])
""")

test.write(['import', 'sub', 'ddd.in'], "import/sub/ddd.in\n")
test.write(['import', 'sub', 'eee.in'], "import/sub/eee.in\n")
test.write(['import', 'sub', 'fff.in'], "import/sub/fff.in\n")

# Perforce uses the PWD environment variable in preference to the actual cwd
os.environ["PWD"] = test.workpath('import')
paths = [ 'aaa.in', 'bbb.in', 'ccc.in',
          'sub/ddd.in', 'sub/eee.in', 'sub/fff.in', 'sub/SConscript' ]
paths = list(map(os.path.normpath, paths))
args = '-c testclient1 add -t binary %s' % ' '.join(paths)
test.p4(args, chdir='import')

changespec = test.substitute("""
Change: new

Client: testclient1

User:   %(user)s

Status: new

Description:
        A test check in

Files:
        //%(depot)s/foo/aaa.in  # add
        //%(depot)s/foo/bbb.in  # add
        //%(depot)s/foo/ccc.in  # add
        //%(depot)s/foo/sub/SConscript  # add
        //%(depot)s/foo/sub/ddd.in      # add
        //%(depot)s/foo/sub/eee.in      # add
        //%(depot)s/foo/sub/fff.in      # add
""")

test.p4('-c testclient1 opened')
test.p4('-c testclient1 submit -i', stdin=changespec)

SConstruct_contents = test.substitute("""
SetOption('warn', 'deprecated-source-code')
def cat(env, source, target):
    target = str(target[0])
    f = open(target, "wb")
    for src in source:
        f.write(open(str(src), "rb").read())
    f.close()
env = Environment(tools = ['default', 'Perforce'],
                  BUILDERS={'Cat':Builder(action=cat)},
                  P4=r'%(p4path)s',
                  P4FLAGS='%(portflag)s -c testclient2')
env.Cat('aaa.out', 'foo/aaa.in')
env.Cat('bbb.out', 'foo/bbb.in')
env.Cat('ccc.out', 'foo/ccc.in')
env.Cat('all', ['aaa.out', 'bbb.out', 'ccc.out'])
env.SourceCode('.', env.Perforce())
SConscript('foo/sub/SConscript', 'env')
""")

test.write(['work', 'SConstruct'], SConstruct_contents)

test.subdir(['work', 'foo'])
test.write(['work', 'foo', 'bbb.in'], "work/foo/bbb.in\n")

test.subdir(['work', 'foo', 'sub'])
test.write(['work', 'foo', 'sub', 'eee.in'], "work/foo/sub/eee.in\n")

test.run(chdir = 'work',
         arguments = '.',
         stderr = warn_p4 + warn_sc,
         match = TestSCons.match_re_dotall)

test.fail_test(test.read(['work', 'all']) != "import/aaa.in\nwork/foo/bbb.in\nimport/ccc.in\n")
test.fail_test(test.read(['work', 'foo', 'sub', 'all']) != "import/sub/ddd.in\nwork/foo/sub/eee.in\nimport/sub/fff.in\n")

test.pass_test()

# Local Variables:
# tab-width:4
# indent-tabs-mode:nil
# End:
# vim: set expandtab tabstop=4 shiftwidth=4:
