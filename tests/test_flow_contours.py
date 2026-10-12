import tempfile
import unittest
from pathlib import Path
import wing_optimizer
from flow_contours import read_flow_field

class FlowFieldTests(unittest.TestCase):
    def parse(self,rows):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"field.txt"
            p.write_text("VARIABLES=x y vx vy v Cp\nZONE I=3, J=3\n"+"\n".join(rows))
            return read_flow_field(p,[[(-.2,-.2),(.2,-.2),(.2,.2),(-.2,.2)]])
    def rows(self):
        return [f"{x} {y} 1 0 1 -0.37" for x in [-1,0,1] for y in [-1,0,1]]
    def test_preserves_native_pressure_and_masks_solid(self):
        field=self.parse(self.rows())
        self.assertAlmostEqual(field["cp"][0,0],-.37)
        self.assertTrue(field["cp"].mask[1,1])
        self.assertFalse(field["cp"].mask[0,0])
    def test_rejects_truncated_grid(self):
        with self.assertRaisesRegex(ValueError,"Incomplete"):self.parse(self.rows()[:-1])
    def test_rejects_duplicate_grid_point(self):
        rows=self.rows();rows[0]=rows[1]
        with self.assertRaisesRegex(ValueError,"Duplicate"):self.parse(rows)
    def test_rejects_nonfinite_external_value(self):
        rows=self.rows();rows[0]="-1 -1 1 0 1 nan"
        with self.assertRaisesRegex(ValueError,"Non-finite"):self.parse(rows)
