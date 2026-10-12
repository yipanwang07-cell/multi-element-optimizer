import unittest
from coordinate_search import refinement_window,refinement_points

class RefinementWindowTests(unittest.TestCase):
    def test_positive_negative_and_zero(self):
        for center,lo,hi,expected in ((200,100,300,(195,205,.5)),(-20,-40,0,(-21,-19,.1)),(0,-10,10,(-.5,.5,.05))):
            window=refinement_window(center,lo,hi,.25)
            self.assertAlmostEqual(window["low"],expected[0])
            self.assertAlmostEqual(window["high"],expected[1])
            self.assertAlmostEqual(window["step"],expected[2])
            points=refinement_points(window)
            self.assertIn(center,points)
            self.assertTrue(all(window["low"]<=p<=window["high"] for p in points))
            self.assertEqual(points[0],window["low"])
            self.assertEqual(points[-1],window["high"])
    def test_user_step_and_clipping(self):
        a=refinement_window(198,198,203,.25)
        b=refinement_window(198,198,203,.1)
        self.assertEqual((a["low"],a["high"]),(198,198.125))
        self.assertEqual(b["step"],.005)
        self.assertGreater(len(refinement_points(b)),len(refinement_points(a)))
    def test_edges_included_for_nondivisible_step(self):
        w=refinement_window(200,100,300,.3)
        p=refinement_points(w)
        self.assertEqual((p[0],p[-1]),(195,205))
        self.assertIn(200,p)
