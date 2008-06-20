"""SCons.Heapmonitor

Facility to introspect memory consumption of certain classes and objects.
Tracked objects are sized recursively to provide an overview of memory
distribution between the different tracked objects.

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

#
# The meta programming techniques used to trace object construction requires
# nested scopes introduced in Python 2.2. For Python 2.1 compliance,
# nested_scopes are imported from __future__.
#
from __future__ import nested_scopes

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import sys
import time

import weakref
import new
import inspect

import SCons.asizeof
import SCons.Debug

# Dictionaries of TrackedObject objects associated with the actual objects that
# are tracked. 'tracked_index' uses the class name as the key and associates a
# list of tracked objects. It contains all TrackedObject instances, including
# those of dead objects.
tracked_index = {}

# 'tracked_objects' uses the id (address) as the key and associates the tracked
# object with it. TrackedObject's referring to dead objects are replaced lazily,
# i.e. when the id is recycled by another tracked object.
tracked_objects = {}

# List of (timestamp, size_of_tracked_objects) tuples for each snapshot.
footprint = []

# Keep objects alive by holding a strong reference.
_keepalive = [] 

# Dictionary of class observers identified by classname.
_observers = {}

# Fixpoint for program start relative time stamp.
_local_start = time.time()

class _ClassObserver(object):
    """
    Stores options for tracked classes.
    The observer also keeps the original constructor of the observed class.
    """
    __slots__ = ('init', 'name', 'detail', 'keep', 'trace')

    def __init__(self, init, name, detail, keep, trace):
        self.init = init
        self.name = name
        self.detail = detail
        self.keep = keep
        self.trace = trace

    def modify(self, name, detail, keep, trace):
        self.name = name
        self.detail = detail
        self.keep = keep
        self.trace = trace

def _is_tracked(klass):
    """
    Determine if the class is tracked.
    """
    return _observers.has_key(klass)

def _track_modify(klass, name, detail, keep, trace):
    """
    Modify settings of a tracked class
    """
    _observers[klass].modify(name, detail, keep, trace)

def _inject_constructor(klass, f, name, resolution_level, keep, trace):
    """
    Modifying Methods in Place - after the recipe 15.7 in the Python
    Cookbook by Ken Seehof. The original constructors may be restored later.
    Therefore, prevent constructor chaining by multiple calls with the same
    class.
    """
    if _is_tracked(klass):
        return

    try:
        ki = klass.__init__
    except AttributeError:
        def ki(self, *args, **kwds):
            pass

    # Possible name clash between keyword arguments of the tracked class'
    # constructor and the curried arguments of the injected constructor.
    # Therefore, the additional arguments have 'magic' names to make it less
    # likely that an argument name clash occurs.
    _observers[klass] = _ClassObserver(ki, name, resolution_level, keep, trace)
    klass.__init__ = new.instancemethod(
        lambda *args, **kwds: f(_observers[klass], *args, **kwds), None, klass)

def _restore_constructor(klass):
    """
    Restore the original constructor, lose track of class.
    """
    klass.__init__ = _observers[klass].init
    del _observers[klass]


def _tracker(_observer_, self, *args, **kwds):
    """
    Injected constructor for tracked classes.
    Call the actual constructor of the object and track the object.
    Attach to the object before calling the constructor to track the object with
    the parameters of the most specialized class.
    """
    track_object(self, name=_observer_.name, resolution_level=_observer_.detail,
        keep=_observer_.keep, trace=_observer_.trace)
    _observer_.init(self, *args, **kwds)

def _trunc(s, max, left=0):
    """
    Convert 's' to string, eliminate newlines and truncate the string to 'max'
    characters. If there are more characters in the string add '...' to the
    string. With 'left=1', the string can be truncated at the beginning.
    """
    s = str(s)
    s = s.replace('\n', '|')
    if len(s) > max:
        if left:
            return '...'+s[len(s)-max+3:]
        else:
            return s[:(max-3)]+'...'
    else:
        return s

class TrackedObject(object):
    """
    Stores size and lifetime information of a tracked object. A weak reference is
    attached to monitor the object without preventing its deletion.
    """

    def __init__(self, instance, resolution_level=0, trace=0):
        """
        Create a weak reference for 'instance' to observe an object but which
        won't prevent its deletion (which is monitored by the finalize
        callback). The size of the object is recorded in 'footprint' as 
        (timestamp, size) tuples.
        """
        self.ref = weakref.ref(instance, self.finalize)
        self.name = instance.__class__
        self.birth = time.time()
        self.death = None
        self._resolution_level = resolution_level

        if trace:
            self._save_trace()

        #initial_size = SCons.asizeof.basicsize(instance)
        initial_size = SCons.asizeof.basicsize(instance) or 0
        so = SCons.asizeof.Asized(initial_size, initial_size)
        self.footprint = [(self.birth, so)]

    def _print_refs(self, file, refs, total, prefix='    ', level=1, 
        minsize=0, minpct=0.1):
        """
        Print individual referents recursively.
        """
        lcmp = lambda i, j: (i.size > j.size) and -1 or (i.size < j.size) and 1 or 0
        lrefs = list(refs)
        lrefs.sort(lcmp)
        for r in lrefs:
            if r.size > minsize and (r.size*100.0/total) > minpct:
                file.write('%-50s %-14s %3d%% [%d]\n' % (_trunc(prefix+str(r.name),50),
                    _pp(r.size),int(r.size*100.0/total), level))
                self._print_refs(file, r.refs, total, prefix=prefix+'  ', level=level+1)

    def _save_trace(self):
        """
        Save current stack trace as formatted string.
        """
        st = inspect.stack()
        try:
            self.trace = []
            for f in st[5:]: # eliminate our own overhead
                for l in f[4]:
                    self.trace.insert(0, '    '+l.strip()+'\n')
                self.trace.insert(0, '  %s:%d in %s\n' % (f[1], f[2], f[3]))
        finally:
            del st

    def print_text(self, file, full=0):
        """
        Print the gathered information in human-readable format to the specified
        file.
        """
        obj  = self.ref()
        if full:
            if obj is None:
                file.write('%-32s (FREE)\n' % _trunc(self.name, 32, left=1))
            else:
                repr = str(obj)
                file.write('%-32s 0x%08x %-35s\n' % (
                    _trunc(self.name, 32, left=1), id(obj), _trunc(repr, 35)))
            try:
                for line in self.trace:
                    file.write(line)
            except AttributeError:
                pass
            for (ts, size) in self.footprint:
                file.write('  %-30s %s\n' % (_get_timestamp(ts), _pp(size.size)))
                self._print_refs(file, size.refs, size.size)                    
            if self.death is not None:
                file.write('  %-30s finalize\n' % _get_timestamp(ts))
        else:
            # TODO Print size for largest snapshot (get_size_at_time)
            # Unused ATM: Maybe drop this type of reporting
            size = self.get_max_size()
            if obj is not None:
                file.write('%-64s %-14s\n' % (_trunc(repr(obj), 64), _pp(size)))
            else:
                file.write('%-64s %-14s\n' % (_trunc(self.name, 64), _pp(size)))       
        

    def track_size(self, ts, sizer):
        """
        Store timestamp and current size for later evaluation.
        The 'sizer' is a stateful sizing facility that excludes other tracked
        objects.
        """
        obj = self.ref()
        self.footprint.append( 
            (ts, sizer.asized(obj, detail=self._resolution_level)) 
        )

    def get_max_size(self):
        """
        Get the maximum of all sampled sizes, or return 0 if no samples were
        recorded.
        """
        try:
            return max([s.size for (t, s) in self.footprint])
        except ValueError:
            return 0

    def get_size_at_time(self, ts):
        """
        Get the size of the object at a specific time (snapshot).
        If the object was not alive/sized at that instant, return 0.
        """
        for (t, s) in self.footprint:
            if t == ts:
                return s.size
        return 0

    def set_resolution_level(self, resolution_level):
        """
        Set resolution level to a new value. The next size estimation will
        respect the new value. This is useful to set different levels for
        different instances of tracked classes.
        """
        self._resolution_level = resolution_level
    
    def finalize(self, ref):
        """
        Mark the reference as dead and remember the timestamp.
        It would be great if we could measure the pre-destruction size. 
        Unfortunately, the object is gone by the time the weakref callback is called.
        However, weakref callbacks are useful to be informed when tracked objects died
        without the need of destructors.

        If the object is destroyed at the end of the program execution, it's not
        possible to import modules anymore. Hence, the finalize callback just
        does nothing (self.death stays None).
        """
        try:
            import time
        except ImportError:
            pass
        else:
            self.death = time.time()


def track_change(instance, resolution_level=0):
    """
    Change tracking options for the already tracked object 'instance'.
    If instance is not tracked, a KeyError will be raised.
    """
    to = tracked_objects[id(instance)]
    to.set_resolution_level(resolution_level)


def track_object(instance, name=None, resolution_level=0, keep=0, trace=0):
    """
    Track object 'instance' and sample size and lifetime information.
    Not all objects can be tracked; trackable objects are class instances and
    other objects that can be weakly referenced. When an object cannot be
    tracked, a TypeError is raised.
    The 'resolution_level' is the recursion depth up to which referents are
    sized individually. Resolution level 0 (default) treats the object as an
    opaque entity, 1 sizes all direct referents individually, 2 also sizes the
    referents of the referents and so forth.
    To prevent the object's deletion a (strong) reference can be held with
    'keep'.
    """

    # Check if object is already tracked. This happens if track_object is called
    # multiple times for the same object or if an object inherits from multiple
    # tracked classes. In the latter case, the most specialized class wins.
    # To detect id recycling, the weak reference is checked. If it is 'None' a
    # tracked object is dead and another one takes the same 'id'. 
    if tracked_objects.has_key(id(instance)) and \
        tracked_objects[id(instance)].ref() is not None:
        return

    to = TrackedObject(instance, resolution_level=resolution_level, trace=trace)

    if name is None:
        name = instance.__class__.__name__
    if not tracked_index.has_key(name):
        tracked_index[name] = []
    tracked_index[name].append(to)
    tracked_objects[id(instance)] = to

    #print "DEBUG: Track %s (Keep=%d, Resolution=%d)" % (name, keep, resolution_level)

    if keep:
        _keepalive.append(instance)


def track_class(cls, name=None, resolution_level=0, keep=0, trace=0):
    """
    Track all objects of the class 'cls'. Objects of that type that already
    exist are _not_ tracked. If track_class is called for a class already
    tracked, the tracking parameters are modified. Instantiation traces can be
    generated with trace=1. 
    A constructor is injected to begin instance tracking on creation
    of the object. The constructor calls 'track_object' internally.
    """
    if _is_tracked(cls):
        _track_modify(cls, name, resolution_level, keep, trace)
    else:
        _inject_constructor(cls, _tracker, name, resolution_level, keep, trace)


def detach_class(klass):
    """ 
    Stop tracking class 'klass'. Any new objects of that type are not
    tracked anymore. Existing objects are still tracked.
    """
    _restore_constructor(klass)


def detach_all_classes():
    """
    Detach from all tracked classes.
    """
    for klass in _observers.keys():
        detach_class(klass) 


def detach_all():
    """
    Detach from all tracked classes and objects.
    Restore the original constructors and cleanse the tracking lists.
    """
    detach_all_classes()
    tracked_objects.clear()
    tracked_index.clear()
    _keepalive[:] = []

def clear():
    """
    Clear all gathered data and detach from all tracked objects/classes.
    """
    detach_all()
    footprint[:] = []

class Footprint:
    pass

def create_snapshot(description=''):
    """
    Collect current per instance statistics.
    Save total amount of memory consumption reported by asizeof and by the
    operating system. The overhead of the Heapmonitor structure is also
    computed.
    """

    ts = time.time()

    sizer = SCons.asizeof.Asizer()
    objs = [to.ref() for to in tracked_objects.values()]
    sizer.exclude_refs(*objs)

    # The objects need to be sized in a deterministic order. Sort the
    # objects by its creation date which should at least work for non-parallel
    # execution. The "proper" fix would be to handle shared data separately.
    sorttime = lambda i, j: (i.birth < j.birth) and -1 or (i.birth > j.birth) and 1 or 0
    tos = tracked_objects.values()
    tos.sort(sorttime)
    for to in tos:
        to.track_size(ts, sizer)

    fp = Footprint()

    fp.timestamp = ts
    fp.tracked_total = sizer.total
    if fp.tracked_total:
        fp.asizeof_total = SCons.asizeof.asizeof(all=True, code=True)
    else:
        fp.asizeof_total = 0
    fp.system_total = SCons.Debug.memory()
    fp.desc = str(description)

    # Compute overhead of all structures, use sizer to exclude tracked objects(!)
    if fp.tracked_total:
        fp.overhead = sizer.asizeof(tracked_index, tracked_objects, footprint)
        fp.asizeof_total -= fp.overhead

    footprint.append(fp)


def find_garbage():
    """
    Let the garbage collector identify ref cycles and check against tracked
    objects.
    WARNING: Prototype implementation.
    """
    import gc
    gc.enable()
    gc.set_debug(gc.DEBUG_LEAK)
    gc.collect()
    for x in gc.garbage:
        # print str(x)
        if tracked_objects.has_key(id(x)):
            print "WARNING: Tracked object is marked as garbage: %s" % repr(tracked_objects[id(x)].ref())

def _pp(i):
    degree = 0
    pattern = "%4d     %s"
    while i > 1024:
        pattern = "%7.2f %s"
        i = i / 1024.0
        degree += 1
    scales = ['B', 'KB', 'MB', 'GB', 'TB', 'EB']
    return pattern % (i, scales[degree])

def _get_timestamp(t):
    """
    Get a friendly timestamp (as returned by time.time) represented as a string.
    """
    rt = t - _local_start
    h, m, s = int(rt / 3600), int(rt / 60 % 60), rt % 60

    return "%02d:%02d:%05.2f" % (h, m, s)

def print_stats(file=sys.stdout, full=0):
    """
    Write tracked objects by class to stdout.
    """

    # Identify the snapshot that tracked the largest amount of memory.
    tmax = None
    maxsize = 0
    for fp in footprint:
        if fp.tracked_total > maxsize:
            tmax = fp.timestamp

    classlist = tracked_index.keys()
    classlist.sort()
    summary = []

    # Emit per-instance data
    for classname in classlist:
        if full:
            file.write('\n%s:\n' % classname)
        sum = 0
        sorted_index = tracked_index[classname]
        sortsize = lambda i, j: \
            (i.get_size_at_time(tmax) > j.get_size_at_time(tmax)) and -1 or \
            (i.get_size_at_time(tmax) < j.get_size_at_time(tmax)) and 1 or 0
        sorted_index.sort(sortsize)
        file.write('%s:\n' % classname)
        for to in sorted_index:
            to.print_text(file, full=1)

    # Emit class summaries for each snapshot
    file.write('---- SUMMARY '+'-'*66+'\n')
    for fp in footprint:
        file.write('%-35s %11s %12s %12s %5s\n' % \
            (_trunc(fp.desc, 35), 'active', _pp(fp.asizeof_total), 
             'average', 'pct'))
        for classname in classlist:
            sum = 0
            active = 0
            for to in tracked_index[classname]:
                sum += to.get_size_at_time(fp.timestamp)
                if to.ref() is not None:
                    active += 1
            try:
                pct = sum * 100 / fp.asizeof_total
            except ZeroDivisionError:
                pct = 0
            try:
                avg = sum / active
            except ZeroDivisionError:
                avg = 0
            file.write('  %-33s %11d %12s %12s %4d%%\n' % \
                (_trunc(classname, 33), active, _pp(sum), _pp(avg), pct))
    file.write('-'*79+'\n')

def print_snapshots(file=sys.stdout):
    """
    Print snapshot stats.
    """
    file.write('%-32s %15s (%11s) %15s\n' % ('SNAPSHOT LABEL', 'VIRTUAL TOTAL',
        'SIZEABLE', 'TRACKED TOTAL'))
    for fp in footprint:
        label = fp.desc
        if label == '':
            label = _get_timestamp(fp.timestamp)
        sample = "%-32s %15s (%11s) %15s\n" % \
            (label, _pp(fp.system_total), _pp(fp.asizeof_total), 
            _pp(fp.tracked_total))
        file.write(sample)
    #file.write('-'*80+'\n')

def attach_default():
    """
    Attach to a set of default classes.
    """
    import SCons.Node

    track_class(SCons.Node.FS.Base, name='Node.FS.Base')
    track_class(SCons.Node.FS.Dir, name='Node.FS.Dir')
    track_class(SCons.Node.FS.RootDir, name='Node.FS.RootDir')
    track_class(SCons.Node.FS.File, name='Node.FS.File')
    track_class(SCons.Node.Node, name='Node.Node')

    import SCons.Executor

    track_class(SCons.Executor.Executor, name='Executor.Executor')
    track_class(SCons.Executor.Null, name='Executor.Null')

    import SCons.Environment

    track_class(SCons.Environment.Base, name='Environment.Base')
    track_class(SCons.Environment.SubstitutionEnvironment,
        name='Environment.SubstitutionEnvironment')
    # track_class(SCons.Environment.EnvironmentClone) # TODO
    track_class(SCons.Environment.OverrideEnvironment,
        name='Environment.OverrideEnvironment')

    import SCons.Action

    track_class(SCons.Action.CommandAction, name='Action.CommandAction')
    track_class(SCons.Action.CommandGeneratorAction,
        name='Action.CommandGeneratorAction')
    track_class(SCons.Action.LazyAction, name='Action.LazyAction')
    track_class(SCons.Action.FunctionAction, name='Action.FunctionAction')
    track_class(SCons.Action.ListAction, name='Action.ListAction')

    import SCons.Builder

    track_class(SCons.Builder.BuilderBase, name='Builder.BuilderBase')
    track_class(SCons.Builder.OverrideWarner, name='Builder.OverrideWarner')
    track_class(SCons.Builder.CompositeBuilder, name='Builder.CompositeBuilder')

    import SCons.SConsign
    
    track_class(SCons.SConsign.DB, name='SConsign.DB')
