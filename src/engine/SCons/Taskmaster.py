"""SCons.Taskmaster

Generic Taskmaster.

"""

#
# Copyright (c) 2001, 2002 Steven Knight
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




import SCons.Node
import string
import SCons.Errors
import copy

class Task:
    """Default SCons build engine task.
    
    This controls the interaction of the actual building of node
    and the rest of the engine.

    This is expected to handle all of the normally-customizable
    aspects of controlling a build, so any given application
    *should* be able to do what it wants by sub-classing this
    class and overriding methods as appropriate.  If an application
    needs to customze something by sub-classing Taskmaster (or
    some other build engine class), we should first try to migrate
    that functionality into this class.
    
    Note that it's generally a good idea for sub-classes to call
    these methods explicitly to update state, etc., rather than
    roll their own interaction with Taskmaster from scratch."""
    def __init__(self, tm, targets, top, node):
        self.tm = tm
        self.targets = targets
        self.top = top
        self.node = node

    def execute(self):
        # This methods is called from multiple threads in
        # a parallel build, so only do thread safe stuff here.
        # Do thread unsafe stuff in executed() or failed().
        if self.targets[0].get_state() != SCons.Node.up_to_date:
            self.targets[0].prepare()
            self.targets[0].build()

    def get_target(self):
        """Fetch the target being built or updated by this task.
        """
        return self.node

    def set_tstates(self, state):
        """Set all of the target nodes's states."""
        for t in self.targets:
            t.set_state(state)

    def executed(self):
        """Called when the task has been successfully executed.

        This may have been a do-nothing operation (to preserve
        build order), so check the node's state before updating
        things.  Most importantly, this calls back to the
        Taskmaster to put any node tasks waiting on this one
        back on the pending list."""

        if self.targets[0].get_state() == SCons.Node.executing:
            self.set_tstates(SCons.Node.executed)
            for t in self.targets:
                t.store_sigs()
                t.built()

        self.tm.executed(self.node)

    def failed(self):
        """Default action when a task fails:  stop the build."""
        self.fail_stop()

    def fail_stop(self):
        """Explicit stop-the-build failure."""
        self.set_tstates(SCons.Node.failed)
        self.tm.stop()

    def fail_continue(self):
        """Explicit continue-the-build failure.

        This sets failure status on the target nodes and all of
        their dependent parent nodes.
        """
        for t in self.targets:
            def get_parents(node, parent): return node.get_parents()
            def set_state(node, parent): node.set_state(SCons.Node.failed)
            walker = SCons.Node.Walker(t, get_parents, eval_func=set_state)
            n = walker.next()
            while n:
                n = walker.next()
        
        self.tm.executed(self.node)

    def make_ready(self):
        """Make a task ready for execution."""
        state = SCons.Node.up_to_date
        for t in self.targets:
            bsig = self.tm.calc.bsig(t)
            t.set_bsig(bsig)
            if not self.tm.calc.current(t, bsig):
                state = SCons.Node.executing
        self.set_tstates(state)

class Calc:
    def bsig(self, node):
        """
        """
        return None

    def current(self, node, sig):
        """Default SCons build engine is-it-current function.
    
        This returns "always out of date," so every node is always
        built/visited.
        """
        return 0

class Taskmaster:
    """A generic Taskmaster for handling a bunch of targets.

    Classes that override methods of this class should call
    the base class method, so this class can do its thing.    
    """

    def __init__(self, targets=[], tasker=Task, calc=Calc()):
        self.targets = targets # top level targets
        self.candidates = targets[:] # nodes that might be ready to be executed
        self.candidates.reverse()
        self.executing = [] # nodes that are currently executing
        self.pending = [] # nodes that depend on a currently executing node
        self.tasker = tasker
        self.ready = None # the next task that is ready to be executed
        self.calc = calc

    def _find_next_ready_node(self):
        """Find the next node that is ready to be built"""

        if self.ready:
            return
        
        while self.candidates:
            node = self.candidates[-1]
            state = node.get_state()
            
            # Skip nodes that have already been executed:
            if state != None and state != SCons.Node.stack:
                self.candidates.pop()
                continue

            # keep track of which nodes are in the execution stack:
            node.set_state(SCons.Node.stack)

            children = node.children()

            # detect dependency cycles:
            def in_stack(node): return node.get_state() == SCons.Node.stack
            cycle = filter(in_stack, children)
            if cycle:
                nodes = filter(in_stack, self.candidates) + cycle
                nodes.reverse()
                desc = "Dependency cycle: " + string.join(map(str, nodes), " -> ")
                raise SCons.Errors.UserError, desc

            for child in children:
                if not child.builder:
                    # set the signature for non-derived files
                    # here so they don't get recalculated over
                    # and over again:
                    child.set_csig(self.calc.csig(child))

            # Add non-derived files that have not been built
            # to the candidates list:
            def derived(node):
                return node.builder and node.get_state() == None
            derived = filter(derived, children)
            if derived:
                derived.reverse()
                self.candidates.extend(derived)
                continue

            # Skip nodes that are pending on a currently executing node:
            if node.depends_on(self.executing) or node.depends_on(self.pending):
                self.pending.append(node)
                node.set_state(SCons.Node.pending)
                self.candidates.pop()
                continue
            else:
                self.candidates.pop()
                self.ready = node
                break

    def next_task(self):
        """Return the next task to be executed."""
        
        self._find_next_ready_node()

        node = self.ready
        
        if node is None:
            return None
        
        self.executing.append(node)
        try:
            tlist = node.builder.targets(node)
        except AttributeError:
            tlist = [node]
        task = self.tasker(self, tlist, node in self.targets, node) 
        task.make_ready()
        self.ready = None
        
        return task
            
    def is_blocked(self):
        self._find_next_ready_node()

        return not self.ready and self.pending

    def stop(self):
        """Stop the current build completely."""
        self.candidates = []
        self.ready = None
        self.pending = []

    def executed(self, node):
        self.executing.remove(node)
        
        # move the current pending nodes to the candidates list:
        # (they may not all be ready to build, but _find_next_ready_node()
        #  will figure out which ones are really ready)
        for node in self.pending:
            node.set_state(None)
        self.pending.reverse()
        self.candidates.extend(self.pending)
        self.pending = []

