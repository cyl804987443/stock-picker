import unittest

from app.jobs import calculate_progress


class JobProgressTests(unittest.TestCase):
    def test_progress_is_bounded_and_finishes_at_one_hundred(self):
        self.assertEqual(calculate_progress(0, 0), 0)
        self.assertEqual(calculate_progress(25, 100), 25)
        self.assertEqual(calculate_progress(120, 100), 100)


if __name__ == "__main__":
    unittest.main()
