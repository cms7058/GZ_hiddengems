import unittest

from app.services.geo import (
    MEMBER_VISIBILITY,
    PROTECTED_VISIBILITY,
    PUBLIC_VISIBILITY,
    SECRET_VISIBILITY,
    can_view_precise_location,
    mask_coordinate,
)


class GeoServiceTest(unittest.TestCase):
    def test_public_spot_always_returns_precise_location(self):
        coordinate = mask_coordinate(25.7436, 108.5062, PUBLIC_VISIBILITY)

        self.assertTrue(coordinate.is_precise)
        self.assertEqual(coordinate.latitude, 25.7436)
        self.assertEqual(coordinate.longitude, 108.5062)

    def test_protected_spot_masks_location_for_regular_user(self):
        coordinate = mask_coordinate(26.1068, 104.6341, PROTECTED_VISIBILITY, decimals=2)

        self.assertFalse(coordinate.is_precise)
        self.assertEqual(coordinate.latitude, 26.11)
        self.assertEqual(coordinate.longitude, 104.63)

    def test_member_rules(self):
        self.assertTrue(can_view_precise_location(MEMBER_VISIBILITY, user_level=0, is_member=True))
        self.assertTrue(can_view_precise_location(MEMBER_VISIBILITY, user_level=2, is_member=False))
        self.assertFalse(can_view_precise_location(PROTECTED_VISIBILITY, user_level=3, is_member=False))
        self.assertTrue(can_view_precise_location(PROTECTED_VISIBILITY, user_level=3, is_member=True))
        self.assertTrue(can_view_precise_location(SECRET_VISIBILITY, user_level=5, is_member=False))


if __name__ == "__main__":
    unittest.main()
