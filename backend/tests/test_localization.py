import unittest

from app.services.localization import choose_text, normalize_language


class LocalizationServiceTest(unittest.TestCase):
    def test_normalize_language(self):
        self.assertEqual(normalize_language("en"), "en-US")
        self.assertEqual(normalize_language("zh"), "zh-CN")
        self.assertEqual(normalize_language("fr", default="zh-CN"), "zh-CN")

    def test_choose_text(self):
        self.assertEqual(choose_text("zh-CN", "摄影", "Photography"), "摄影")
        self.assertEqual(choose_text("en-US", "摄影", "Photography"), "Photography")
        self.assertEqual(choose_text("en-US", "摄影", None), "摄影")


if __name__ == "__main__":
    unittest.main()
