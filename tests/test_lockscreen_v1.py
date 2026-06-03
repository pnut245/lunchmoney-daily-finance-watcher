import unittest

from src import lockscreen


class LockscreenV1Tests(unittest.TestCase):
    def test_positive_v1_lockscreen_uses_white_background(self):
        image = lockscreen.render_lockscreen(
            {
                "remaining_today": 55,
                "is_negative": False,
                "last_updated": "2026-06-02T23:00:00",
                "safe_to_spend": "$55",
                "spending_state": "V1",
                "week": "$250",
                "dopamine": "$35",
            }
        )

        self.assertEqual(image.getpixel((10, 10)), (255, 255, 255, 255))

    def test_negative_v1_lockscreen_uses_red_background(self):
        image = lockscreen.render_lockscreen(
            {
                "remaining_today": -12,
                "is_negative": True,
                "last_updated": "2026-06-02T23:00:00",
            }
        )

        self.assertEqual(image.getpixel((10, 10)), (215, 25, 32, 255))


if __name__ == "__main__":
    unittest.main()
