import math
import unittest

from software.protocol import parse_afe_row


class ProtocolTests(unittest.TestCase):
    def test_parses_five_sensor_frame(self):
        groups = []
        for sensor in range(5):
            groups.extend(
                [
                    str(100 + sensor),
                    f"{0.5 + sensor:.3f}",
                    f"{1.0 + sensor:.3f}",
                    f"{1.1 + sensor:.3f}",
                    "OK",
                ]
            )
        frame = parse_afe_row(",".join(["250", *groups]))

        self.assertIsNotNone(frame)
        self.assertEqual(frame.time_ms, 250)
        self.assertEqual(len(frame.filtered_mohm), 5)
        self.assertAlmostEqual(frame.filtered_ohm[0], 1.1e6)
        self.assertTrue(frame.is_valid)

    def test_accepts_nan_but_marks_frame_invalid(self):
        groups = ["100", "0.5", "1.0", "nan", "WARN:VOUT<=VREF"] * 5
        frame = parse_afe_row(",".join(["250", *groups]))
        self.assertIsNotNone(frame)
        self.assertTrue(math.isnan(frame.filtered_mohm[0]))
        self.assertFalse(frame.is_valid)

    def test_ignores_header_and_bad_rows(self):
        self.assertIsNone(parse_afe_row("t_ms,adc0"))
        self.assertIsNone(parse_afe_row("1,2,3"))


if __name__ == "__main__":
    unittest.main()
