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
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import os
import os.path
import string
import sys
import TestSCons

python = TestSCons.python

test = TestSCons.TestSCons()



test.write('mytex.py', r"""
import sys
import os
base_name = os.path.splitext(sys.argv[1])[0]
infile = open(sys.argv[1], 'rb')
out_file = open(base_name+'.dvi', 'wb')
for l in infile.readlines():
    if l[0] != '\\':
	out_file.write(l)
sys.exit(0)
""")

test.write('SConstruct', """
env = Environment(TEX = r'%s mytex.py', tools=['tex'])
env.DVI(target = 'test.dvi', source = 'test.tex')
""" % python)

test.write('test.tex', r"""This is a test.
\end
""")

test.run(arguments = 'test.dvi', stderr = None)

test.fail_test(test.read('test.dvi') != "This is a test.\n")



tex = test.where_is('tex')

if tex:

    test.write("wrapper.py", """import os
import string
import sys
open('%s', 'wb').write("wrapper.py\\n")
os.system(string.join(sys.argv[1:], " "))
""" % string.replace(test.workpath('wrapper.out'), '\\', '\\\\'))

    test.write('SConstruct', """
import os
ENV = { 'PATH' : os.environ['PATH'] }
foo = Environment(ENV = ENV)
tex = foo.Dictionary('TEX')
bar = Environment(ENV = ENV, TEX = r'%s wrapper.py ' + tex)
foo.DVI(target = 'foo.dvi', source = 'foo.tex')
foo.DVI(target = 'foo-latex.dvi', source = 'foo-latex.tex')
bar.DVI(target = 'bar', source = 'bar.tex')
bar.DVI(target = 'bar-latex', source = 'bar-latex.tex')
foo.DVI('rerun.tex')
foo.DVI('bibtex-test.tex')
""" % python)

    tex = r"""
This is the %s TeX file.
\end
"""

    latex = r"""
\document%s{letter}
\begin{document}
This is the %s LaTeX file.
\end{document}
"""

    rerun = r"""
\documentclass{article}

\begin{document}

\LaTeX\ will need to run twice on this document to get a reference to section
\ref{sec}.

\section{Next section}
\label{sec}

\end{document}
"""

    bibtex = r"""
\documentclass{article}

\begin{document}

Run \texttt{latex}, then \texttt{bibtex}, then \texttt{latex} twice again \cite{lamport}.

\bibliographystyle{plain}
\bibliography{test}

\end{document}
"""

    bib = r"""
@Book{lamport,
  author =	 {L. Lamport},
  title = 	 {{\LaTeX: A} Document Preparation System},
  publisher = 	 {Addison-Wesley},
  year = 	 1994
}
"""

    test.write('foo.tex', tex % 'foo.tex')
    test.write('bar.tex', tex % 'bar.tex')
    test.write('foo-latex.tex', latex % ('style', 'foo-latex.tex'))
    test.write('bar-latex.tex', latex % ('class', 'bar-latex.tex'))
    test.write('rerun.tex', rerun)
    test.write('bibtex-test.tex', bibtex)
    test.write('test.bib', bib)

    test.run(arguments = 'foo.dvi foo-latex.dvi', stderr = None)
    test.fail_test(os.path.exists(test.workpath('wrapper.out')))
    test.fail_test(not os.path.exists(test.workpath('foo.dvi')))
    test.fail_test(not os.path.exists(test.workpath('foo-latex.dvi')))

    test.run(arguments = 'bar.dvi bar-latex.dvi', stderr = None)
    test.fail_test(not os.path.exists(test.workpath('wrapper.out')))
    test.fail_test(not os.path.exists(test.workpath('bar.dvi')))
    test.fail_test(not os.path.exists(test.workpath('bar-latex.dvi')))

    test.run(stderr = None)
    output_lines = string.split(test.stdout(), '\n')
    reruns = filter(lambda x: x == 'latex rerun.tex', output_lines)
    test.fail_test(len(reruns) != 2)
    bibtex = filter(lambda x: x == 'bibtex bibtex-test', output_lines)
    test.fail_test(len(bibtex) != 1)

test.pass_test()
