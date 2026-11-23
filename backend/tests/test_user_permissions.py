import unittest

from tests.test_api import ApiTest


class UserPermissionTest(unittest.TestCase):
    def setUp(self):
        self.fixture = ApiTest()
        self.fixture.setUp()
        self.client = self.fixture.client
        self.db = self.fixture.SessionLocal
        self.admin = self.fixture.login_headers()

    def tearDown(self):
        self.fixture.tearDown()

    def test_permission_filter_batch_update_and_detail_binding(self):
        with self.db() as db:
            from app.models.user import MiniProgramUser

            db.add(MiniProgramUser(openid="permission-user-2", nickname="筛选用户", safety_level="quality", explore_points=50, benefit_points=20, eco_credit=80))
            db.commit()

        filtered = self.client.get("/api/v1/admin/users?keyword=筛选&safety_level=quality&min_explore_points=10", headers=self.admin)
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(filtered.json()["items"][0]["nickname"], "筛选用户")

        policy = self.client.post(
            "/api/v1/admin/community/food-policies",
            headers=self.admin,
            json={"name": "权限测试规则", "all_users": False, "user_ids": [1], "reward_points": 2},
        )
        self.assertEqual(policy.status_code, 201, policy.text)
        result = self.client.post(
            "/api/v1/admin/users/permissions/batch",
            headers=self.admin,
            json={"user_ids": [1], "can_upload_image": True, "food_policy_id": policy.json()["id"]},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["updated_count"], 1)
        detail = self.client.get("/api/v1/admin/users/1", headers=self.admin)
        self.assertEqual(detail.json()["food_policy_id"], policy.json()["id"])

        cleared = self.client.patch("/api/v1/admin/users/1", headers=self.admin, json={"food_policy_id": 0})
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertIsNone(cleared.json()["food_policy_id"])
