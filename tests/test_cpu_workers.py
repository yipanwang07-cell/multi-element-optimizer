import unittest
from cpu_workers import physical_core_cpus,worker_count,CoreSlots

class PhysicalCoreTests(unittest.TestCase):
    def test_requested_count_is_not_silently_reduced(self):
        self.assertEqual(worker_count(6,16),6)
        self.assertEqual(worker_count("16",16),16)
        for value in (17,0,-1,True,"1.5"):
            with self.subTest(value=value),self.assertRaises(ValueError):worker_count(value,16)
    def test_distinct_core_slots_are_returned_after_error(self):
        slots=CoreSlots([0,2,4])
        with self.assertRaises(RuntimeError):
            with slots.acquire() as first,slots.acquire() as second:
                self.assertNotEqual(first,second)
                raise RuntimeError("fixture")
        with slots.acquire() as a,slots.acquire() as b,slots.acquire() as c:
            self.assertEqual({a,b,c},{0,2,4})
    def test_topology_is_unique(self):
        cpus=physical_core_cpus()
        self.assertGreater(len(cpus),0)
        self.assertEqual(len(cpus),len(set(cpus)))
