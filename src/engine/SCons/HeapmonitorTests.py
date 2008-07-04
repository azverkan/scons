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

import unittest
import TestCmd
import tempfile

from os import tempnam, remove
from SCons.Heapmonitor import *

class Foo:
    def __init__(self):
        self.foo = 'foo'

class Bar(Foo):
    def __init__(self):
        Foo.__init__(self)
        self.bar = 'bar'

class FooNew(object):
    def __init__(self):
        self.foo = 'foo'

class BarNew(FooNew):
    def __init__(self):
        super(BarNew, self).__init__()


class TrackObjectTestCase(unittest.TestCase):

    def setUp(self):
        detach_all()

    def test_track_object(self):
        """Test object registration.
        """
        foo = Foo()
        bar = Bar()

        track_object(foo)
        track_object(bar)

        assert id(foo) in tracked_objects
        assert id(bar) in tracked_objects

        assert 'Foo' in tracked_index
        assert 'Bar' in tracked_index

        assert tracked_objects[id(foo)].ref() == foo
        assert tracked_objects[id(bar)].ref() == bar

    def test_type_errors(self):
        """Test intrackable objects.
        """
        i = 42
        j = 'Foobar'
        k = [i,j]
        l = {i: j}

        self.assertRaises(TypeError, track_object, i)
        self.assertRaises(TypeError, track_object, j)
        self.assertRaises(TypeError, track_object, k)
        self.assertRaises(TypeError, track_object, l)

        assert id(i) not in tracked_objects
        assert id(j) not in tracked_objects
        assert id(k) not in tracked_objects
        assert id(l) not in tracked_objects

    def test_track_by_name(self):
        """Test registering objects by name.
        """
        foo = Foo()

        track_object(foo, name='Foobar')

        assert 'Foobar' in tracked_index        
        assert tracked_index['Foobar'][0].ref() == foo

    def test_keep(self):
        """Test lifetime of tracked objects.
        """
        foo = Foo()
        bar = Bar()

        track_object(foo, keep=1)
        track_object(bar)
       
        idfoo = id(foo)
        idbar = id(bar)

        del foo
        del bar

        assert tracked_objects[idfoo].ref() is not None
        assert tracked_objects[idbar].ref() is None

    def test_dump(self):
        """Test serialization of log data.
        """
        foo = Foo()

        track_object(foo, resolution_level=4)
        create_snapshot('Footest')

        f1 = tempfile.TemporaryFile()
        print_stats(file=f1)

        tmp = tempnam() # FIXME tempnam is deprecated
        dump_stats(tmp)

        clear()

        stats = MemStats()
        assert stats.tracked_index is None
        assert stats.footprint is None
        stats.load(tmp)
        remove(tmp)
        assert 'Foo' in stats.tracked_index

        f2 = tempfile.TemporaryFile()
        stats.print_stats(file=f2)

        f1.seek(0)
        f2.seek(0)

        assert f1.read() == f2.read()

        f1.close()
        f2.close()


    def test_recurse(self):
        """Test recursive sizing and saving of referents.
        """
        foo = Foo()
        bar = Bar()

        track_object(foo, resolution_level=1)
        create_snapshot()

        fp = tracked_objects[id(foo)].footprint[-1]
        refs = fp[1].refs
        dref = [r for r in refs if r.name == '__dict__']
        assert len(dref) == 1
        dref = dref[0]
        assert dref.size > 0
        assert dref.flat > 0
        assert dref.refs == ()

        # Test track_change and more fine-grained resolution
        track_change(foo, resolution_level=2)
        create_snapshot()

        fp = tracked_objects[id(foo)].footprint[-1]
        refs = fp[1].refs
        dref = [r for r in refs if r.name == '__dict__']
        assert len(dref) == 1
        dref = dref[0]
        namerefs = [r.name for r in dref.refs]
        assert '[K] foo' in namerefs
        assert "[V] foo: 'foo'" in namerefs        

class SnapshotTestCase(unittest.TestCase):

    def setUp(self):
        clear()

    def test_timestamp(self):
        """Test timestamp of snapshots.
        """
        foo = Foo()
        bar = Bar()

        track_object(foo)
        track_object(bar)

        create_snapshot()
        create_snapshot()
        create_snapshot()

        refts = [fp.timestamp for fp in footprint]
        for to in tracked_objects.values():
            ts = [t for (t,sz) in to.footprint[1:]]
            assert ts == refts

    def test_desc(self):
        """Test footprint description.
        """
        create_snapshot()
        create_snapshot('alpha')
        create_snapshot(description='beta')
        create_snapshot(42)

        assert len(footprint) == 4
        assert footprint[0].desc == ''
        assert footprint[1].desc == 'alpha'
        assert footprint[2].desc == 'beta'
        assert footprint[3].desc == '42'

class TrackClassTestCase(unittest.TestCase):

    def setUp(self):
        detach_all()

    def test_track_class(self):
        """Test tracking objects through classes.
        """
        track_class(Foo)
        track_class(Bar)

        foo = Foo()
        bar = Bar()

        assert id(foo) in tracked_objects
        assert id(bar) in tracked_objects

    def test_track_class_new(self):
        """Test tracking new style classes.
        """
        track_class(FooNew)
        track_class(BarNew)

        foo = FooNew()
        bar = BarNew()

        assert id(foo) in tracked_objects
        assert id(bar) in tracked_objects

    def test_track_by_name(self):
        """Test registering objects by name.
        """
        track_class(Foo, name='Foobar')

        foo = Foo()

        assert 'Foobar' in tracked_index        
        assert tracked_index['Foobar'][0].ref() == foo

    def test_keep(self):
        """Test lifetime of tracked objects.
        """
        track_class(Foo, keep=1)
        track_class(Bar)

        foo = Foo()
        bar = Bar()
       
        idfoo = id(foo)
        idbar = id(bar)

        del foo
        del bar

        assert tracked_objects[idfoo].ref() is not None
        assert tracked_objects[idbar].ref() is None

    def test_detach(self):
        """Test detaching from tracked classes.
        """
        track_class(Foo)
        track_class(Bar)

        foo = Foo()
        bar = Bar()

        assert id(foo) in tracked_objects
        assert id(bar) in tracked_objects

        detach_class(Foo)
        detach_class(Bar)

        foo2 = Foo()
        bar2 = Bar()
    
        assert id(foo2) not in tracked_objects
        assert id(bar2) not in tracked_objects

        self.assertRaises(KeyError, detach_class, Foo)

    def test_change_name(self):
        """Test modifying name.
        """
        track_class(Foo, name='Foobar')
        track_class(Foo, name='Baz')
        foo = Foo()

        assert 'Foobar' not in tracked_index
        assert 'Baz' in tracked_index
        assert tracked_index['Baz'][0].ref() == foo


if __name__ == "__main__":
    suite = unittest.TestSuite()
    tclasses = [ TrackObjectTestCase,
                 TrackClassTestCase,
                 SnapshotTestCase
                 # RecursionLevelTestCase,
               ]
    for tclass in tclasses:
        names = unittest.getTestCaseNames(tclass, 'test_')
        suite.addTests(map(tclass, names))
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        sys.exit(1)
