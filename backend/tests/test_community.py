import json
import subprocess
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from sqlalchemy import func, select

from tests.test_api import ApiTest
from app.models.admin import AdminRole, AdminUser
from app.models.community import CommunityUpload, EcoCredit, EcoMilestone, EcoSubmission, EcoWarning, FoodSubmission
from app.models.spot import ScenicSpot
from app.models.user import BenefitPointLedger, MiniProgramUser, UserSpotUnlock
from app.services.community import review_eco
from app.services.community_media import inspect_media, run_eco_ai
from app.services.security import create_access_token


class CommunityTest(unittest.TestCase):
    def setUp(self):
        self.fixture = ApiTest()
        self.fixture.setUp()
        self.client = self.fixture.client
        self.db = self.fixture.SessionLocal
        self.admin = self.fixture.login_headers()
        self.mini = {"Authorization": "Bearer " + create_access_token("mini:1")}

    def tearDown(self):
        self.fixture.tearDown()

    def spot(self, level=2, unlocked=True):
        with self.db() as db:
            row = ScenicSpot(name_zh="测试秘境", name_en="Test", summary_zh="简介", summary_en="Summary", city="测试", county="测试", latitude=26, longitude=106,
                             required_explore_points=1, recommendation_level=level, review_status="approved", is_active=True)
            db.add(row)
            db.flush()
            if unlocked:
                db.add(UserSpotUnlock(user_id=1, spot_id=row.id, status="active"))
            db.commit()
            return row.id

    def upload(self, purpose="eco", media_type="video", user_id=1, **kwargs):
        with self.db() as db:
            values = {"media_url": "/media/community/test.mp4", "duration": 3 if media_type == "video" else 0,
                      "width": 320, "height": 240, "size_bytes": 100, "frames_json": "[]"}
            values.update(kwargs)
            row = CommunityUpload(user_id=user_id, purpose=purpose, media_type=media_type, **values)
            db.add(row)
            db.commit()
            return row.id

    def submit(self, spot_id, category="B", upload_id=None):
        return self.client.post("/api/v1/mini/community/eco", headers=self.mini,
                                json={"spot_id": spot_id, "category": category, "upload_id": upload_id or self.upload()})

    def review(self, item_id, verdict="approved"):
        return self.client.patch(f"/api/v1/admin/community/eco/{item_id}", headers=self.admin, json={"verdict": verdict, "note": "人工审核结论"})

    def test_authenticated_owner_and_eligibility(self):
        self.assertEqual(self.client.get("/api/v1/mini/community/summary").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/mini/community/summary", headers=self.admin).status_code, 401)
        self.assertEqual(self.submit(self.spot(1)).status_code, 403)
        self.assertEqual(self.submit(self.spot(2, False)).status_code, 403)
        with self.db() as db:
            other = MiniProgramUser(openid="other-community-user", nickname="Other")
            db.add(other); db.commit(); other_id = other.id
        self.assertEqual(self.submit(self.spot(), upload_id=self.upload(user_id=other_id)).status_code, 400)

    def test_latest_only_reupload_and_duplicate_credit(self):
        spot_id = self.spot()
        first = self.submit(spot_id)
        self.assertEqual(first.status_code, 201, first.text)
        item_id = first.json()["id"]
        self.assertEqual(first.json()["status"], "pending")
        self.assertEqual(self.submit(spot_id).status_code, 409)
        self.assertEqual(self.review(item_id, "other").status_code, 200)
        with patch("app.api.v1.routers.community.delete_media") as delete:
            second = self.submit(spot_id)
            self.assertEqual(second.status_code, 201, second.text)
            delete.assert_called_once()
        items = self.client.get("/api/v1/mini/community/eco", headers=self.mini).json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], second.json()["id"])
        self.assertEqual(self.review(second.json()["id"]).status_code, 200)
        self.assertEqual(self.review(second.json()["id"]).status_code, 409)
        self.assertEqual(self.submit(spot_id).status_code, 409)
        summary = self.client.get("/api/v1/mini/community/summary", headers=self.mini).json()
        self.assertEqual(summary["levels"]["2"], 1)
        self.assertEqual(summary["checkin_count"], 1)
        with self.db() as db:
            self.assertEqual(db.scalar(select(func.count(EcoSubmission.id))), 2)

    def test_penalties_and_threshold_snapshot(self):
        # 29 credits plus one newly approved video unlock only the current L3 catalog.
        target = self.spot(3, False)
        for _ in range(29):
            sid = self.spot()
            with self.db() as db:
                video = EcoSubmission(user_id=1, spot_id=sid, level=2, category="C", upload_id=self.upload(), status="approved", verdict="approved")
                db.add(video); db.flush()
                db.add(EcoCredit(user_id=1, spot_id=sid, level=2, submission_id=video.id)); db.commit()
        item_id = self.submit(self.spot()).json()["id"]
        self.assertEqual(self.review(item_id).status_code, 200)
        later = self.spot(3, False)
        with self.db() as db:
            self.assertIsNotNone(db.scalar(select(UserSpotUnlock).where(UserSpotUnlock.user_id == 1, UserSpotUnlock.spot_id == target)))
            self.assertIsNone(db.scalar(select(UserSpotUnlock).where(UserSpotUnlock.user_id == 1, UserSpotUnlock.spot_id == later)))
            self.assertEqual(db.scalar(select(func.count(EcoMilestone.id))), 1)
        bad = self.submit(self.spot()).json()["id"]
        self.assertEqual(self.review(bad, "unrelated").status_code, 200)
        summary = self.client.get("/api/v1/mini/community/summary", headers=self.mini).json()
        self.assertEqual((summary["credit"], summary["checkin_count"], summary["warning_count"]), (0, 0, 1))
        self.assertEqual(self.review(bad, "unrelated").status_code, 409)
        with self.db() as db:
            self.assertIsNotNone(db.scalar(select(UserSpotUnlock).where(UserSpotUnlock.spot_id == target)))

    def test_four_unclear_clear_credit_but_not_count(self):
        good = self.submit(self.spot()).json()["id"]
        self.review(good)
        for index in range(4):
            item = self.submit(self.spot()).json()["id"]
            self.assertEqual(self.review(item, "unclear_garbage").status_code, 200)
            summary = self.client.get("/api/v1/mini/community/summary", headers=self.mini).json()
            self.assertEqual(summary["credit"], 1 if index < 3 else 0)
        self.assertEqual(summary["checkin_count"], 1)
        self.assertEqual(summary["warning_count"], 1)
        self.review(self.submit(self.spot()).json()["id"])
        self.assertEqual(self.client.get("/api/v1/mini/community/summary", headers=self.mini).json()["warning_count"], 1)

    def test_a_ai_is_advisory_and_failure_keeps_pending(self):
        upload_id = self.upload(frames_json=json.dumps(["data:image/jpeg;base64,dGVzdA=="] * 6))
        config_payload = {
            "provider": "test provider", "api_base": "https://ai.example.test/v1", "model": "test-model",
            "api_key": "test-secret", "enabled": True,
        }
        configured = self.client.put("/api/v1/admin/community/eco-ai/config", headers=self.admin, json=config_payload)
        self.assertEqual(configured.status_code, 200, configured.text)
        self.assertTrue(configured.json()["enabled"])
        self.assertNotIn("test-secret", configured.text)
        with patch("app.api.v1.routers.community.run_eco_ai") as task:
            response = self.submit(self.spot(), "A", upload_id)
            self.assertEqual(response.status_code, 201)
            task.assert_called_once_with(response.json()["id"])
        ai_settings = {
            "ECO_AI_ENABLED": "true", "ECO_AI_PROVIDER": "test provider", "ECO_AI_API_BASE": "https://ai.example.test/v1",
            "ECO_AI_MODEL": "test-model", "ECO_AI_API_KEY": "test-secret",
        }
        with patch("app.db.session.SessionLocal", self.db), \
             patch("app.services.integrations.get_group_config", return_value=ai_settings), \
             patch("app.services.admin_assistant.call_ai", return_value='{"recommendation":"qualified","analysis":"可见垃圾袋投入垃圾桶"}'):
            run_eco_ai(response.json()["id"])
        with self.db() as db:
            row = db.get(EcoSubmission, response.json()["id"])
            self.assertEqual(row.status, "pending")
            self.assertEqual(row.ai_status, "completed")
            self.assertEqual(row.ai_recommendation, "qualified")
            self.assertIn("垃圾袋投入垃圾桶", row.ai_note)
        admin_list = self.client.get("/api/v1/admin/community/eco?status=pending", headers=self.admin).json()
        self.assertEqual(admin_list["items"][0]["ai_recommendation"], "qualified")
        self.assertIn("垃圾袋投入垃圾桶", admin_list["items"][0]["ai_note"])

    def test_eco_ai_config_is_super_admin_only_and_disabled_by_default(self):
        config_url = "/api/v1/admin/community/eco-ai/config"
        initial = self.client.get(config_url, headers=self.admin)
        self.assertEqual(initial.status_code, 200)
        self.assertFalse(initial.json()["enabled"])
        invalid = self.client.put(config_url, headers=self.admin, json={
            "provider": "provider", "api_base": "", "model": "model", "api_key": "key", "enabled": True,
        })
        self.assertEqual(invalid.status_code, 400)
        with self.db() as db:
            role = AdminRole(code="eco_reviewer", name="环保审核员", permissions_json=json.dumps(["checkins:read", "checkins:update"]))
            admin = AdminUser(username="eco-reviewer", password_hash="unused", role=role.code)
            db.add(role); db.add(admin); db.commit(); reviewer_id = admin.id
        reviewer = {"Authorization": "Bearer " + create_access_token(str(reviewer_id))}
        self.assertEqual(self.client.get(config_url, headers=reviewer).status_code, 403)
        denied = self.client.put(config_url, headers=reviewer, json={"enabled": False})
        self.assertEqual(denied.status_code, 403)

    def test_a_video_waits_for_human_when_eco_ai_is_disabled(self):
        with patch("app.api.v1.routers.community.run_eco_ai") as task:
            response = self.submit(self.spot(), "A")
        self.assertEqual(response.status_code, 201)
        task.assert_not_called()
        admin_list = self.client.get("/api/v1/admin/community/eco?status=pending", headers=self.admin).json()
        self.assertEqual(admin_list["items"][0]["ai_status"], "manual_required")
        self.assertIn("尚未启用", admin_list["items"][0]["ai_note"])
        self.assertNotIn("ai_recommendation", response.json())

    def test_food_binding_snapshot_limits_and_exactly_once_reward(self):
        summary = self.client.get("/api/v1/mini/community/summary", headers=self.mini).json()
        self.assertIsNone(summary["food_policy"])
        payload = {"title": "推荐", "content": "内容", "upload_ids": [self.upload("food", "image")]}
        self.assertEqual(self.client.post("/api/v1/mini/community/food", headers=self.mini, json=payload).status_code, 403)
        rule = {"name": "美食规则", "all_users": True, "reward_points": 7, "max_width": 200}
        self.assertEqual(self.client.post("/api/v1/admin/community/food-policies", headers=self.admin, json=rule).status_code, 201)
        self.assertEqual(self.client.post("/api/v1/mini/community/food", headers=self.mini, json=payload).status_code, 400)
        rule["max_width"] = 4096
        self.client.post("/api/v1/admin/community/food-policies", headers=self.admin, json=rule)
        with self.db() as db:
            before = db.get(MiniProgramUser, 1).benefit_points
        result = self.client.post("/api/v1/mini/community/food", headers=self.mini, json=payload)
        self.assertEqual(result.status_code, 201, result.text)
        rule["reward_points"] = 99
        rule["all_users"] = False; rule["user_ids"] = [1]; rule["is_active"] = False
        self.client.post("/api/v1/admin/community/food-policies", headers=self.admin, json=rule)
        self.assertIsNone(self.client.get("/api/v1/mini/community/summary", headers=self.mini).json()["food_policy"])
        url = f"/api/v1/admin/community/food/{result.json()['id']}"
        self.assertEqual(self.client.patch(url, headers=self.admin, json={"approved": True, "note": "通过"}).status_code, 200)
        self.assertEqual(self.client.patch(url, headers=self.admin, json={"approved": True, "note": "通过"}).status_code, 409)
        with self.db() as db:
            self.assertEqual(db.get(MiniProgramUser, 1).benefit_points, before + 7)
            self.assertEqual(db.scalar(select(func.count(BenefitPointLedger.id)).where(BenefitPointLedger.reference_type == "food_submission")), 1)


class MediaInspectionTest(unittest.TestCase):
    def test_image_dimensions_are_read_from_file(self):
        buffer = BytesIO(); Image.new("RGB", (320, 240)).save(buffer, "JPEG")
        result = inspect_media(buffer.getvalue(), "image")
        self.assertEqual((result["width"], result["height"]), (320, 240))

    def test_real_three_second_video_and_reject_long_video(self):
        from fastapi import HTTPException
        with tempfile.TemporaryDirectory() as folder:
            for duration in (3, 5):
                path = Path(folder) / f"{duration}.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=green:s=320x240:r=25", "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True, timeout=20)
                if duration == 3:
                    result = inspect_media(path.read_bytes(), "video", eco=True)
                    self.assertEqual(len(json.loads(result["frames_json"])), 6)
                else:
                    with self.assertRaises(HTTPException): inspect_media(path.read_bytes(), "video", eco=True)
