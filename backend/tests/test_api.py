import unittest
import json
from unittest.mock import PropertyMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.admin import AdminUser
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.integration import IntegrationSetting
from app.models.spot import ScenicSpot, Tag
from app.models.user import CheckinRecord, MembershipPlan, MiniProgramUser, PassLevelSetting, UserMembership
from app.services.security import hash_password
from app.services.integrations import seed_integration_settings
from app.services.qweather import QWeatherClient


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.seed_data()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def seed_data(self):
        db = self.SessionLocal()
        photo = Tag(id=1, name_zh="摄影", name_en="Photography", icon="camera", sort_order=10)
        hiking = Tag(id=2, name_zh="徒步", name_en="Hiking", icon="footprints", sort_order=20)
        spot = ScenicSpot(
            id=1,
            name_zh="加榜梯田晨雾点",
            name_en="Jiabang Rice Terraces Mist Viewpoint",
            summary_zh="适合清晨摄影的梯田观景点。",
            summary_en="A quiet viewpoint for morning photography.",
            description_zh="建议日出前抵达。",
            description_en="Arrive before sunrise.",
            city="黔东南州",
            county="从江县",
            latitude=25.7436,
            longitude=108.5062,
            visibility_level="protected",
            review_status="approved",
            recommendation_level=5,
            required_explore_points=100,
            tags=[photo, hiking],
        )
        admin = AdminUser(
            id=1,
            username="admin",
            password_hash=hash_password("admin123456"),
            role="super_admin",
        )
        user = MiniProgramUser(
            id=1,
            openid="demo-openid-001",
            nickname="山野摄影师",
            phone="13800000001",
            language="zh-CN",
            explore_points=120,
            checkin_count=8,
            contribution_count=3,
            eco_credit=96,
            is_member=True,
        )
        pass_setting = PassLevelSetting(
            id=1,
            level=2,
            name_zh="行者",
            name_en="Wayfarer",
            checkin_points=25,
            unlock_benefit_zh="可查看部分会员级秘境的更精确区域。",
            unlock_benefit_en="View more accurate areas for selected member-level spots.",
        )
        plan = MembershipPlan(
            id=1,
            name_zh="月度探索会员",
            name_en="Monthly Explorer",
            duration_days=30,
            price_cents=1900,
            benefits_zh="解锁会员秘境区域。",
            benefits_en="Unlock member spot areas.",
        )
        membership = UserMembership(
            id=1,
            user_id=1,
            plan_id=1,
            status="active",
        )
        checkin = CheckinRecord(
            id=1,
            user_id=1,
            spot_id=1,
            status="pending",
            latitude="25.7431",
            longitude="108.5060",
            note="清晨到达。",
        )
        image = SpotImage(
            id=1,
            spot_id=1,
            image_url="/media/spots/demo.jpg",
            caption="演示图片",
            is_cover=True,
        )
        note = TravelNote(
            id=1,
            user_id=1,
            spot_id=1,
            title="路线记录",
            content="清晨抵达。",
            status="approved",
        )
        comment = UserComment(
            id=1,
            user_id=1,
            spot_id=1,
            content="很适合摄影。",
            status="pending",
        )
        recommendation = LifestyleRecommendation(
            id=1,
            category="food",
            name_zh="酸汤鱼",
            name_en="Sour Soup Fish",
            summary_zh="返程适合用餐。",
            summary_en="Good after the trip.",
            spot_id=1,
            city="黔东南州",
            county="从江县",
        )
        db.add_all(
            [
                spot,
                admin,
                user,
                pass_setting,
                plan,
                membership,
                checkin,
                image,
                note,
                comment,
                recommendation,
            ]
        )
        seed_integration_settings(db)
        db.commit()
        db.close()

    def login_headers(self):
        response = self.client.post(
            "/api/v1/admin/login",
            json={"username": "admin", "password": "admin123456"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_tags_support_english(self):
        response = self.client.get("/api/v1/tags?lang=en-US")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Photography")

    def test_root_serves_admin_login_page_without_redirect(self):
        response = self.client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn("贵州秘境管理后台", response.text)
        self.assertNotIn('value="admin"', response.text)

    def test_map_spots_mask_protected_location_for_regular_user(self):
        response = self.client.get("/api/v1/spots/map?tag_ids=1&lang=zh-CN&explore_points=120")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertFalse(data[0]["is_precise_location"])
        self.assertTrue(data[0]["is_unlocked"])
        self.assertEqual(data[0]["required_explore_points"], 100)
        self.assertEqual(data[0]["latitude"], 25.74)
        self.assertEqual(data[0]["longitude"], 108.51)

    def test_map_spots_accepts_high_explorer_levels(self):
        response = self.client.get("/api/v1/spots/map?lang=zh-CN&user_level=7&explore_points=120")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], 1)

    def test_map_spot_uses_pass_level_marker_color_even_when_level_is_inactive(self):
        db = self.SessionLocal()
        setting = db.get(PassLevelSetting, 1)
        setting.level = 5
        setting.marker_color = "#C63D52"
        setting.is_active = False
        db.add(setting)
        db.commit()
        db.close()

        response = self.client.get("/api/v1/spots/map?lang=zh-CN&explore_points=120")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["marker_color"], "#C63D52")

    def test_spot_detail_supports_english(self):
        response = self.client.get("/api/v1/spots/1?lang=en-US&user_level=3&is_member=true&explore_points=120")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Jiabang Rice Terraces Mist Viewpoint")
        self.assertEqual(data["description"], "Arrive before sunrise.")
        self.assertTrue(data["is_precise_location"])
        self.assertTrue(data["is_unlocked"])
        self.assertEqual(data["images"][0]["image_url"], "/media/spots/demo.jpg")
        self.assertTrue(data["images"][0]["is_cover"])
        self.assertEqual(data["travel_notes"][0]["title"], "路线记录")
        self.assertEqual(data["comments"], [])
        self.assertEqual(data["lifestyle_recommendations"][0]["name_zh"], "酸汤鱼")

    def test_spot_detail_requires_enough_explore_points(self):
        response = self.client.get("/api/v1/spots/1?lang=zh-CN&explore_points=20")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["required_explore_points"], 100)

    def test_spot_detail_includes_only_current_users_pending_submissions(self):
        response = self.client.get("/api/v1/spots/1?lang=zh-CN&user_id=1&explore_points=120")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["comments"][0]["content"], "很适合摄影。")
        self.assertEqual(data["comments"][0]["status"], "pending")
        self.assertEqual(data["my_checkins"][0]["note"], "清晨到达。")
        self.assertEqual(data["my_checkins"][0]["status"], "pending")

    def test_mini_program_can_submit_checkin_note_and_comment(self):
        checkin = self.client.post(
            "/api/v1/mini/checkins",
            json={
                "user_id": 1,
                "spot_id": 1,
                "latitude": "25.7436",
                "longitude": "108.5062",
                "note": "到达观景台。",
            },
        )
        self.assertEqual(checkin.status_code, 201)
        self.assertEqual(checkin.json()["status"], "approved")
        self.assertGreaterEqual(checkin.json()["awarded_explore_points"], 0)
        self.assertLessEqual(checkin.json()["checkin_distance_meters"], 300)

        note = self.client.post(
            "/api/v1/mini/travel-notes",
            json={
                "user_id": 1,
                "spot_id": 1,
                "title": "晨雾记录",
                "content": "早上六点云雾最好。",
                "media": [
                    {"media_url": "/media/mini-shares/note-one.jpg", "media_type": "image"},
                    {"media_url": "/media/mini-shares/note-two.mp4", "media_type": "video"},
                ],
            },
        )
        self.assertEqual(note.status_code, 201)
        self.assertEqual(note.json()["status"], "pending")
        self.assertEqual(len(note.json()["media"]), 2)

        rejected_checkin = self.client.post(
            "/api/v1/mini/checkins",
            json={
                "user_id": 1,
                "spot_id": 1,
                "latitude": "26.7436",
                "longitude": "109.5062",
            },
        )
        self.assertEqual(rejected_checkin.status_code, 201)
        self.assertEqual(rejected_checkin.json()["status"], "rejected")
        self.assertGreater(rejected_checkin.json()["checkin_distance_meters"], 300)

        comment = self.client.post(
            "/api/v1/mini/comments",
            json={
                "user_id": 1,
                "spot_id": 1,
                "content": "雨后路面湿滑。",
            },
        )
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(comment.json()["status"], "pending")

    def test_mini_content_requires_successful_checkin_for_same_spot(self):
        note = self.client.post(
            "/api/v1/mini/travel-notes",
            json={"user_id": 1, "spot_id": 1, "title": "未打卡游记", "content": "不应提交成功。"},
        )
        self.assertEqual(note.status_code, 403)
        self.assertIn("Successful check-in", note.json()["detail"])

        comment = self.client.post(
            "/api/v1/mini/comments",
            json={"user_id": 1, "spot_id": 1, "content": "不应提交成功。"},
        )
        self.assertEqual(comment.status_code, 403)
        self.assertIn("Successful check-in", comment.json()["detail"])

    def test_spot_safety_returns_unconfigured_placeholder(self):
        response = self.client.get("/api/v1/spots/1/safety?lang=zh-CN")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["configured"])
        self.assertEqual(data["source"], "QWeather")
        self.assertEqual(data["alerts"], [])
        self.assertEqual(data["river_warning"]["level"], "unknown")

    def test_spot_safety_returns_upstream_weather_and_alerts(self):
        db = self.SessionLocal()
        spot = db.get(ScenicSpot, 1)
        spot.river_name = "都柳江支流"
        spot.river_upstream_latitude = 25.9
        spot.river_upstream_longitude = 108.7
        db.commit()
        db.close()

        with (
            patch.object(QWeatherClient, "is_configured", new_callable=PropertyMock, return_value=True),
            patch.object(
                QWeatherClient,
                "get_weather_now",
                side_effect=[
                    {"now": {"text": "多云", "temp": "24", "precip": "0"}, "updateTime": "2026-07-09T12:00+08:00"},
                    {"now": {"text": "暴雨", "temp": "21", "precip": "12"}, "updateTime": "2026-07-09T12:05+08:00"},
                ],
            ) as weather_mock,
            patch.object(
                QWeatherClient,
                "get_weather_alerts",
                side_effect=[
                    {"alerts": []},
                    {"alerts": [{"id": "upstream-alert", "headline": "上游暴雨预警", "description": "上游强降雨。"}]},
                ],
            ) as alerts_mock,
        ):
            response = self.client.get("/api/v1/spots/1/safety?lang=zh-CN")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["configured"])
        self.assertEqual(data["river_warning"]["river_name"], "都柳江支流")
        self.assertEqual(data["river_warning"]["upstream_location"]["latitude"], 25.9)
        self.assertEqual(data["river_warning"]["upstream_weather"]["weather"]["text"], "暴雨")
        self.assertEqual(data["river_warning"]["upstream_alerts"][0]["headline"], "上游暴雨预警")
        self.assertEqual(data["river_warning"]["level"], "high")
        self.assertEqual(weather_mock.call_count, 2)
        self.assertEqual(alerts_mock.call_count, 2)

    def test_admin_endpoint_requires_token(self):
        response = self.client.get("/api/v1/admin/tags")

        self.assertEqual(response.status_code, 401)

    def test_admin_can_update_username_and_password(self):
        headers = self.login_headers()

        response = self.client.patch(
            "/api/v1/admin/me",
            headers=headers,
            json={
                "username": "operator",
                "current_password": "admin123456",
                "new_password": "newpass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "operator")

        old_login = self.client.post(
            "/api/v1/admin/login",
            json={"username": "admin", "password": "admin123456"},
        )
        self.assertEqual(old_login.status_code, 401)

        new_login = self.client.post(
            "/api/v1/admin/login",
            json={"username": "operator", "password": "newpass123"},
        )
        self.assertEqual(new_login.status_code, 200)

    def test_admin_can_update_integration_settings_with_masked_secret(self):
        headers = self.login_headers()

        response = self.client.patch(
            "/api/v1/admin/integrations/weather",
            headers=headers,
            json={
                "settings": {
                    "QWEATHER_API_HOST": "abc.qweatherapi.com",
                    "QWEATHER_API_KEY": "secret-key-123456",
                    "QWEATHER_JWT_EXPIRE_SECONDS": "900",
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        settings = {item["key"]: item for item in response.json()["settings"]}
        self.assertEqual(settings["QWEATHER_API_HOST"]["value"], "abc.qweatherapi.com")
        self.assertEqual(settings["QWEATHER_API_KEY"]["value"], "sec****456")
        self.assertTrue(settings["QWEATHER_API_KEY"]["is_configured"])

    def test_admin_can_test_weather_integration(self):
        headers = self.login_headers()
        db = self.SessionLocal()
        setting = db.scalars(
            select(IntegrationSetting).where(
                IntegrationSetting.group == "weather",
                IntegrationSetting.key == "QWEATHER_API_KEY",
            )
        ).one()
        setting.value = "test-key"
        host = db.scalars(
            select(IntegrationSetting).where(
                IntegrationSetting.group == "weather",
                IntegrationSetting.key == "QWEATHER_API_HOST",
            )
        ).one()
        host.value = "api.qweather.com"
        db.commit()
        db.close()

        with (
            patch.object(QWeatherClient, "get_weather_now", return_value={"now": {"text": "晴", "temp": "26", "obsTime": "2026-07-14T10:00+08:00"}}),
            patch.object(QWeatherClient, "get_weather_alerts", return_value={"alerts": []}),
        ):
            response = self.client.post("/api/v1/admin/integrations/weather/test", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["weather"]["text"], "晴")

    def test_admin_can_test_ai_integration(self):
        headers = self.login_headers()
        response = self.client.patch(
            "/api/v1/admin/integrations/ai",
            headers=headers,
            json={
                "settings": {
                    "AI_PROVIDER": "Test Provider",
                    "AI_API_BASE": "https://ai.example.test/v1",
                    "AI_MODEL": "test-model",
                    "AI_API_KEY": "test-key",
                }
            },
        )
        self.assertEqual(response.status_code, 200)

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode("utf-8")

        with patch("app.api.v1.routers.admin_integrations.urlopen", return_value=FakeResponse()) as urlopen_mock:
            response = self.client.post("/api/v1/admin/integrations/ai/test", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "OK")
        self.assertEqual(urlopen_mock.call_args.args[0].full_url, "https://ai.example.test/v1/chat/completions")

    def test_admin_assistant_returns_knowledge_base_answer_without_ai_config(self):
        response = self.client.post(
            "/api/v1/admin/assistant/chat",
            headers=self.login_headers(),
            json={"mode": "guide", "message": "如何新增一个秘境并设置解锁积分？"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "knowledge_base")
        self.assertIn("待审", response.json()["answer"])
        self.assertIn("checkins", response.json()["pending"])

    def test_admin_assistant_returns_ai_answer_when_model_is_configured(self):
        headers = self.login_headers()
        response = self.client.patch(
            "/api/v1/admin/integrations/ai",
            headers=headers,
            json={
                "settings": {
                    "AI_PROVIDER": "MiniMax",
                    "AI_API_BASE": "https://api.minimaxi.com/v1",
                    "AI_MODEL": "MiniMax-M2.7",
                    "AI_API_KEY": "test-key",
                }
            },
        )
        self.assertEqual(response.status_code, 200)

        with patch("app.services.admin_assistant.call_ai", return_value="MiniMax response"):
            response = self.client.post(
                "/api/v1/admin/assistant/chat",
                headers=headers,
                json={"mode": "guide", "message": "如何新增秘境？"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "ai")
        self.assertEqual(response.json()["answer"], "MiniMax response")

    def test_admin_assistant_can_create_content_review_suggestion(self):
        response = self.client.post(
            "/api/v1/admin/assistant/review",
            headers=self.login_headers(),
            json={"content_type": "travel_note", "content_id": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content_id"], 1)
        self.assertEqual(response.json()["source"], "knowledge_base")

    def test_qweather_prefers_jwt_when_both_auth_configs_exist(self):
        client = QWeatherClient(
            {
                "QWEATHER_API_HOST": "abc.qweatherapi.com",
                "QWEATHER_PROJECT_ID": "project-id",
                "QWEATHER_KEY_ID": "key-id",
                "QWEATHER_PRIVATE_KEY": "private-key",
                "QWEATHER_API_KEY": "api-key",
                "QWEATHER_JWT_EXPIRE_SECONDS": "900",
            }
        )

        self.assertTrue(client.is_configured)
        self.assertEqual(client.auth_mode, "jwt")

    def test_admin_login_and_me(self):
        headers = self.login_headers()
        response = self.client.get("/api/v1/admin/me", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "admin")

    def test_admin_can_update_tag(self):
        response = self.client.patch(
            "/api/v1/admin/tags/1",
            headers=self.login_headers(),
            json={"name_en": "Photo Spots", "sort_order": 5},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name_en"], "Photo Spots")
        self.assertEqual(data["sort_order"], 5)

    def test_admin_tag_sort_order_is_unique_and_delete_detaches_spots(self):
        headers = self.login_headers()
        duplicate_response = self.client.post(
            "/api/v1/admin/tags",
            headers=headers,
            json={"name_zh": "重复排序", "name_en": "Duplicate Sort", "sort_order": 10},
        )
        self.assertEqual(duplicate_response.status_code, 409)

        delete_response = self.client.delete("/api/v1/admin/tags/2", headers=headers)
        self.assertEqual(delete_response.status_code, 204)
        spot_response = self.client.get("/api/v1/admin/spots/1", headers=headers)
        self.assertEqual(spot_response.status_code, 200)
        self.assertNotIn(2, spot_response.json()["tag_ids"])

    def test_admin_can_review_spot(self):
        headers = self.login_headers()
        create_response = self.client.post(
            "/api/v1/admin/spots",
            headers=headers,
            json={
                "name_zh": "新秘境",
                "name_en": "New Hidden Gem",
                "summary_zh": "待审核秘境。",
                "summary_en": "A pending hidden gem.",
                "city": "贵阳市",
                "county": "花溪区",
                "latitude": 26.41,
                "longitude": 106.67,
                "visibility_level": "public",
                "review_status": "draft",
                "recommendation_level": 2,
                "tag_ids": [1],
            },
        )
        self.assertEqual(create_response.status_code, 201)
        spot_id = create_response.json()["id"]

        before_review = self.client.get("/api/v1/spots/map?tag_ids=1&explore_points=120")
        self.assertEqual(len(before_review.json()), 1)

        review_response = self.client.patch(
            f"/api/v1/admin/spots/{spot_id}/review",
            headers=headers,
            json={"review_status": "approved"},
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["review_status"], "approved")

        after_review = self.client.get("/api/v1/spots/map?tag_ids=1&explore_points=120")
        self.assertEqual(len(after_review.json()), 2)

    def test_roles_enforce_module_crud_permissions(self):
        super_headers = self.login_headers()
        role_response = self.client.post(
            "/api/v1/admin/roles",
            headers=super_headers,
            json={"code": "tag_viewer", "name": "标签查看员", "permissions": ["tags:read"]},
        )
        self.assertEqual(role_response.status_code, 201)
        self.assertEqual(role_response.json()["permissions"], ["tags:read"])

        admin_response = self.client.post(
            "/api/v1/admin/roles/admins",
            headers=super_headers,
            json={"username": "tagviewer", "password": "viewer-pass-123", "role": "tag_viewer"},
        )
        self.assertEqual(admin_response.status_code, 201)

        login_response = self.client.post(
            "/api/v1/admin/login",
            json={"username": "tagviewer", "password": "viewer-pass-123"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["admin"]["permissions"], ["tags:read"])
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        self.assertEqual(self.client.get("/api/v1/admin/tags", headers=headers).status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/v1/admin/tags",
                headers=headers,
                json={"name_zh": "测试", "name_en": "Test", "sort_order": 99},
            ).status_code,
            403,
        )

    def test_super_admin_can_update_admin_username_and_reset_password(self):
        super_headers = self.login_headers()
        create_response = self.client.post(
            "/api/v1/admin/roles/admins",
            headers=super_headers,
            json={"username": "reviewer", "password": "reviewer-pass-123", "role": "super_admin"},
        )
        self.assertEqual(create_response.status_code, 201)
        admin_id = create_response.json()["id"]

        update_response = self.client.patch(
            f"/api/v1/admin/roles/admins/{admin_id}",
            headers=super_headers,
            json={"username": "content_reviewer", "password": "reset-pass-456"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["username"], "content_reviewer")

        old_login = self.client.post(
            "/api/v1/admin/login",
            json={"username": "reviewer", "password": "reviewer-pass-123"},
        )
        self.assertEqual(old_login.status_code, 401)
        new_login = self.client.post(
            "/api/v1/admin/login",
            json={"username": "content_reviewer", "password": "reset-pass-456"},
        )
        self.assertEqual(new_login.status_code, 200)

    def test_admin_spot_requires_existing_pass_level(self):
        response = self.client.patch(
            "/api/v1/admin/spots/1",
            headers=self.login_headers(),
            json={"recommendation_level": 99},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Selected pass level does not exist")

    def test_admin_normalizes_wgs84_coordinates_and_rejects_swapped_values(self):
        headers = self.login_headers()
        response = self.client.patch(
            "/api/v1/admin/spots/1",
            headers=headers,
            json={"latitude": 25.7436, "longitude": 108.5062, "coordinate_system": "wgs84"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotEqual(data["latitude"], 25.7436)
        self.assertNotEqual(data["longitude"], 108.5062)

        swapped_response = self.client.patch(
            "/api/v1/admin/spots/1",
            headers=headers,
            json={"latitude": 108.5062, "longitude": 25.7436, "coordinate_system": "gcj02"},
        )
        self.assertEqual(swapped_response.status_code, 400)
        self.assertIn("纬度、经度", swapped_response.json()["detail"])

    def test_admin_can_permanently_delete_spot_and_related_content(self):
        headers = self.login_headers()
        response = self.client.delete("/api/v1/admin/spots/1", headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/v1/admin/spots/1", headers=headers).status_code, 404)
        self.assertEqual(
            self.client.get("/api/v1/admin/content/travel-notes", headers=headers).json()["total"],
            0,
        )
        self.assertEqual(
            self.client.get("/api/v1/admin/content/comments", headers=headers).json()["total"],
            0,
        )

    def test_admin_can_manage_registered_users(self):
        headers = self.login_headers()
        list_response = self.client.get("/api/v1/admin/users", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["nickname"], "山野摄影师")
        self.assertEqual(list_response.json()["total"], 1)
        self.assertEqual(list_response.json()["page"], 1)

        update_response = self.client.patch(
            "/api/v1/admin/users/1",
            headers=headers,
            json={
                "explore_points": 160,
                "avatar_url": "/media/avatars/test.jpg",
                "is_member": False,
                "is_active": False,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        data = update_response.json()
        self.assertEqual(data["explore_points"], 160)
        self.assertEqual(data["avatar_url"], "/media/avatars/test.jpg")
        self.assertTrue(data["is_member"])
        self.assertFalse(data["is_active"])

        create_response = self.client.post(
            "/api/v1/admin/users",
            headers=headers,
            json={"openid": "openid-new", "nickname": "新用户", "avatar_url": "/media/avatars/new.jpg"},
        )
        self.assertEqual(create_response.status_code, 201)
        user_id = create_response.json()["id"]

        delete_response = self.client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
        self.assertEqual(delete_response.status_code, 204)
        deleted_response = self.client.get(f"/api/v1/admin/users/{user_id}", headers=headers)
        self.assertFalse(deleted_response.json()["is_active"])

    def test_admin_can_update_pass_settings(self):
        response = self.client.patch(
            "/api/v1/admin/pass-settings/1",
            headers=self.login_headers(),
            json={
                "checkin_points": 6,
                "requires_membership": True,
                "unlock_benefit_zh": "更新后的解锁权益。",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["checkin_points"], 6)
        self.assertTrue(data["requires_membership"])
        self.assertEqual(data["unlock_benefit_zh"], "更新后的解锁权益。")

    def test_admin_can_change_pass_level_without_duplicates(self):
        headers = self.login_headers()
        create_response = self.client.post(
            "/api/v1/admin/pass-settings",
            headers=headers,
            json={
                "level": 5,
                "name_zh": "守护者",
                "name_en": "Guardian",
                "unlock_benefit_zh": "高级秘境解锁",
                "unlock_benefit_en": "Unlock advanced gems",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        setting_id = create_response.json()["id"]

        update_response = self.client.patch(
            f"/api/v1/admin/pass-settings/{setting_id}",
            headers=headers,
            json={"level": 6},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["level"], 6)

        spot_response = self.client.get("/api/v1/admin/spots/1", headers=headers)
        self.assertEqual(spot_response.status_code, 200)
        self.assertEqual(spot_response.json()["recommendation_level"], 6)

        duplicate_response = self.client.patch(
            "/api/v1/admin/pass-settings/1",
            headers=headers,
            json={"level": 6},
        )
        self.assertEqual(duplicate_response.status_code, 409)

    def test_pass_setting_explore_points_controls_spot_unlock(self):
        headers = self.login_headers()
        create_response = self.client.post(
            "/api/v1/admin/pass-settings",
            headers=headers,
            json={
                "level": 5,
                "name_zh": "守护者",
                "name_en": "Guardian",
                "required_explore_points": 180,
                "unlock_benefit_zh": "高级秘境解锁",
                "unlock_benefit_en": "Unlock advanced gems",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["required_explore_points"], 180)

        locked_response = self.client.get("/api/v1/spots/map?user_id=1&lang=zh-CN")
        self.assertEqual(locked_response.status_code, 200)
        self.assertEqual(locked_response.json(), [])

        user_response = self.client.patch(
            "/api/v1/admin/users/1",
            headers=headers,
            json={"explore_points": 180},
        )
        self.assertEqual(user_response.status_code, 200)

        unlocked_response = self.client.get("/api/v1/spots/1?user_id=1&lang=zh-CN")
        self.assertEqual(unlocked_response.status_code, 200)
        self.assertTrue(unlocked_response.json()["is_unlocked"])

    def test_admin_can_delete_unlinked_pass_setting(self):
        headers = self.login_headers()
        create_response = self.client.post(
            "/api/v1/admin/pass-settings",
            headers=headers,
            json={
                "level": 9,
                "name_zh": "测试等级",
                "name_en": "Test Level",
                "unlock_benefit_zh": "测试权益",
                "unlock_benefit_en": "Test benefit",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        delete_response = self.client.delete(
            f"/api/v1/admin/pass-settings/{create_response.json()['id']}",
            headers=headers,
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_admin_can_manage_membership_plans(self):
        headers = self.login_headers()
        list_response = self.client.get("/api/v1/admin/memberships/plans", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["name_zh"], "月度探索会员")

        update_response = self.client.patch(
            "/api/v1/admin/memberships/plans/1",
            headers=headers,
            json={"price_cents": 2900, "required_explore_points": 80, "is_active": False},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["price_cents"], 2900)
        self.assertEqual(update_response.json()["required_explore_points"], 80)
        self.assertFalse(update_response.json()["is_active"])

        upgrade_plan_response = self.client.post(
            "/api/v1/admin/memberships/plans",
            headers=headers,
            json={
                "name_zh": "积分守护会员",
                "name_en": "Points Guardian",
                "duration_days": 365,
                "price_cents": 0,
                "required_explore_points": 200,
                "benefits_zh": "积分自动升级权益。",
                "benefits_en": "Points-based upgrade benefits.",
            },
        )
        self.assertEqual(upgrade_plan_response.status_code, 201)

        user_response = self.client.patch(
            "/api/v1/admin/users/1",
            headers=headers,
            json={"explore_points": 220},
        )
        self.assertEqual(user_response.status_code, 200)
        self.assertTrue(user_response.json()["is_member"])

        records_response = self.client.get("/api/v1/admin/memberships/records", headers=headers)
        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(records_response.json()["items"][0]["nickname"], "山野摄影师")
        self.assertEqual(records_response.json()["items"][0]["plan_name_zh"], "积分守护会员")

        unused_plan_response = self.client.post(
            "/api/v1/admin/memberships/plans",
            headers=headers,
            json={
                "name_zh": "未使用套餐",
                "name_en": "Unused Plan",
                "duration_days": 30,
                "price_cents": 0,
                "required_explore_points": 999,
                "benefits_zh": "测试。",
                "benefits_en": "Test.",
            },
        )
        self.assertEqual(unused_plan_response.status_code, 201)
        delete_response = self.client.delete(
            f"/api/v1/admin/memberships/plans/{unused_plan_response.json()['id']}",
            headers=headers,
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_admin_can_review_checkins_and_update_user_count(self):
        headers = self.login_headers()
        db = self.SessionLocal()
        checkin = db.get(CheckinRecord, 1)
        checkin.media_url = "/media/mini-shares/checkin-photo.jpg"
        checkin.media_type = "image"
        db.add(checkin)
        db.commit()
        db.close()
        setting_response = self.client.post(
            "/api/v1/admin/pass-settings",
            headers=headers,
            json={
                "level": 5,
                "name_zh": "守护者",
                "name_en": "Guardian",
                "checkin_points": 25,
                "unlock_benefit_zh": "高级秘境解锁",
                "unlock_benefit_en": "Unlock advanced gems",
            },
        )
        self.assertEqual(setting_response.status_code, 201)
        list_response = self.client.get("/api/v1/admin/checkins", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["status"], "pending")

        approve_response = self.client.patch(
            "/api/v1/admin/checkins/1/review",
            headers=headers,
            json={"status": "approved", "review_note": "定位和图片通过。"},
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")
        self.assertEqual(approve_response.json()["awarded_explore_points"], 25)
        self.assertIsNotNone(approve_response.json()["promoted_spot_image_id"])

        spot_checkins_response = self.client.get("/api/v1/admin/spots/1/checkins", headers=headers)
        self.assertEqual(spot_checkins_response.status_code, 200)
        self.assertEqual(spot_checkins_response.json()["items"][0]["media_type"], "image")
        self.assertEqual(spot_checkins_response.json()["items"][0]["promoted_spot_image_id"], approve_response.json()["promoted_spot_image_id"])

        detail_response = self.client.get("/api/v1/spots/1?lang=zh-CN&user_id=1&explore_points=120")
        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(any(item["image_url"] == "/media/mini-shares/checkin-photo.jpg" for item in detail_response.json()["images"]))

        user_response = self.client.get("/api/v1/admin/users/1", headers=headers)
        self.assertEqual(user_response.json()["checkin_count"], 9)
        self.assertEqual(user_response.json()["explore_points"], 145)

        approve_again_response = self.client.patch(
            "/api/v1/admin/checkins/1/review",
            headers=headers,
            json={"status": "approved", "review_note": "重复审核。"},
        )
        self.assertEqual(approve_again_response.status_code, 200)
        user_again_response = self.client.get("/api/v1/admin/users/1", headers=headers)
        self.assertEqual(user_again_response.json()["checkin_count"], 9)
        self.assertEqual(user_again_response.json()["explore_points"], 145)

    def test_admin_can_manage_spot_images(self):
        headers = self.login_headers()
        list_response = self.client.get("/api/v1/admin/content/spots/1/images", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["caption"], "演示图片")

        upload_response = self.client.post(
            "/api/v1/admin/content/spots/1/images",
            headers=headers,
            data={"caption": "上传图片", "is_cover": "true", "sort_order": "2"},
            files={"file": ("spot.png", b"fake-image", "image/png")},
        )
        self.assertEqual(upload_response.status_code, 201)
        self.assertTrue(upload_response.json()["image_url"].startswith("/media/spots/"))
        self.assertTrue(upload_response.json()["is_cover"])

    def test_mini_upload_accepts_media_type_when_temp_file_has_no_suffix(self):
        response = self.client.post(
            "/api/v1/mini/uploads",
            data={"user_id": "1", "media_type": "image"},
            files={"file": ("wxfile", b"fake-image", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["media_type"], "image")
        self.assertTrue(response.json()["media_url"].startswith("/media/mini-shares/"))

    def test_admin_can_review_notes_and_comments(self):
        headers = self.login_headers()
        notes_response = self.client.get("/api/v1/admin/content/travel-notes", headers=headers)
        self.assertEqual(notes_response.status_code, 200)
        self.assertEqual(notes_response.json()["items"][0]["title"], "路线记录")

        upload_response = self.client.post(
            "/api/v1/admin/content/uploads/travel-notes",
            headers=headers,
            files={"file": ("note.webp", b"fake-image", "image/webp")},
        )
        self.assertEqual(upload_response.status_code, 200)
        self.assertTrue(upload_response.json()["image_url"].startswith("/media/travel-notes/"))

        note_review = self.client.patch(
            "/api/v1/admin/content/travel-notes/1/status",
            headers=headers,
            json={"status": "approved", "is_featured": True},
        )
        self.assertEqual(note_review.status_code, 200)
        self.assertEqual(note_review.json()["status"], "approved")
        self.assertTrue(note_review.json()["is_featured"])

        comment_review = self.client.patch(
            "/api/v1/admin/content/comments/1/status",
            headers=headers,
            json={"status": "hidden"},
        )
        self.assertEqual(comment_review.status_code, 200)
        self.assertEqual(comment_review.json()["status"], "hidden")

        create_note = self.client.post(
            "/api/v1/admin/content/travel-notes",
            headers=headers,
            json={
                "user_id": 1,
                "spot_id": 1,
                "title": "后台新增游记",
                "content": "带图内容。",
                "image_url": "/media/travel-notes/new.jpg",
            },
        )
        self.assertEqual(create_note.status_code, 201)
        note_id = create_note.json()["id"]
        self.assertEqual(create_note.json()["image_url"], "/media/travel-notes/new.jpg")

        update_note = self.client.patch(
            f"/api/v1/admin/content/travel-notes/{note_id}",
            headers=headers,
            json={"title": "更新游记", "is_featured": True},
        )
        self.assertEqual(update_note.json()["title"], "更新游记")
        self.assertTrue(update_note.json()["is_featured"])

        delete_note = self.client.delete(f"/api/v1/admin/content/travel-notes/{note_id}", headers=headers)
        self.assertEqual(delete_note.status_code, 204)

        create_comment = self.client.post(
            "/api/v1/admin/content/comments",
            headers=headers,
            json={
                "user_id": 1,
                "spot_id": 1,
                "content": "后台新增留言。",
                "image_url": "/media/comments/new.jpg",
            },
        )
        self.assertEqual(create_comment.status_code, 201)
        comment_id = create_comment.json()["id"]
        self.assertEqual(create_comment.json()["image_url"], "/media/comments/new.jpg")

        update_comment = self.client.patch(
            f"/api/v1/admin/content/comments/{comment_id}",
            headers=headers,
            json={"content": "更新留言。", "status": "approved"},
        )
        self.assertEqual(update_comment.json()["content"], "更新留言。")
        self.assertEqual(update_comment.json()["status"], "approved")

        delete_comment = self.client.delete(f"/api/v1/admin/content/comments/{comment_id}", headers=headers)
        self.assertEqual(delete_comment.status_code, 204)

    def test_admin_can_manage_lifestyle_recommendations(self):
        headers = self.login_headers()
        list_response = self.client.get("/api/v1/admin/content/recommendations", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["name_zh"], "酸汤鱼")

        create_response = self.client.post(
            "/api/v1/admin/content/recommendations",
            headers=headers,
            json={
                "category": "hotel",
                "spot_id": 1,
                "name_zh": "观景民宿",
                "name_en": "View Homestay",
                "summary_zh": "靠近观景点。",
                "summary_en": "Near the viewpoint.",
                "city": "黔东南州",
                "county": "从江县",
                "image_url": "/media/recommendations/hotel.jpg",
                "price_level": "mid",
                "recommendation_level": 3,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        recommendation_id = create_response.json()["id"]
        self.assertEqual(create_response.json()["spot_name_zh"], "加榜梯田晨雾点")
        self.assertEqual(create_response.json()["image_url"], "/media/recommendations/hotel.jpg")

        update_response = self.client.patch(
            f"/api/v1/admin/content/recommendations/{recommendation_id}",
            headers=headers,
            json={"recommendation_level": 5, "image_url": "/media/recommendations/hotel-2.jpg", "is_active": False},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["recommendation_level"], 5)
        self.assertEqual(update_response.json()["image_url"], "/media/recommendations/hotel-2.jpg")
        self.assertFalse(update_response.json()["is_active"])

        delete_response = self.client.delete(
            f"/api/v1/admin/content/recommendations/{recommendation_id}",
            headers=headers,
        )
        self.assertEqual(delete_response.status_code, 204)


if __name__ == "__main__":
    unittest.main()
