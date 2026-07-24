import json
import unittest
from datetime import date
from unittest.mock import PropertyMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.admin import AdminRole, AdminUser
from app.models.archive import ArchiveDevelopmentTask, ArchiveEvent, ArchiveInternalMessage, ArchiveRequirement
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.integration import IntegrationSetting
from app.models.spot import ScenicSpot, Tag, WechatChannelVideo
from app.models.user import CheckinRecord, MembershipPlan, MiniProgramUser, PassLevelSetting, UserMembership
from app.services.security import hash_password
from app.services.integrations import seed_integration_settings
from app.services.bootstrap import seed_admin_roles
from app.services.permissions import ALL_PERMISSIONS
from app.services.points import seed_point_rules
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
        seed_point_rules(db)
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

    def test_super_admin_can_delete_requirement_and_related_records(self):
        db = self.SessionLocal()
        requirement = ArchiveRequirement(
            code="REQ-20260721-001",
            title="待删除的开发需求",
            module="开发需求",
            category="缺陷",
            source_date=date(2026, 7, 21),
            source_text="删除测试数据。",
            description="验证删除会清理关联记录。",
            acceptance_criteria="需求及关联记录均被删除。",
        )
        db.add(requirement)
        db.flush()
        task = ArchiveDevelopmentTask(
            code="DEV-20260721-001",
            requirement_id=requirement.id,
            sub_requirement_code=requirement.code,
            title="删除测试任务",
        )
        event = ArchiveEvent(
            requirement_id=requirement.id,
            event_type="test",
            actor_type="admin",
            detail="删除测试事件",
        )
        message = ArchiveInternalMessage(
            message_type="test",
            title="删除测试消息",
            content="关联开发需求的消息",
            related_requirement_id=requirement.id,
            target_role="admin",
        )
        db.add_all([task, event, message])
        db.commit()
        requirement_id, task_id, event_id, message_id = requirement.id, task.id, event.id, message.id
        db.close()

        response = self.client.delete(
            f"/api/v1/admin/archive/requirements/{requirement.code}",
            headers=self.login_headers(),
        )

        self.assertEqual(response.status_code, 204)
        db = self.SessionLocal()
        self.assertIsNone(db.get(ArchiveRequirement, requirement_id))
        self.assertIsNone(db.get(ArchiveDevelopmentTask, task_id))
        self.assertIsNone(db.get(ArchiveEvent, event_id))
        self.assertIsNone(db.get(ArchiveInternalMessage, message_id))
        db.close()

    def test_archive_import_uses_draft_and_saves_requirements(self):
        headers = self.login_headers()
        payload = {
            "source_name": "微信聊天粘贴",
            "source_type": "wechat_personal",
            "contact": "测试客户",
            "raw_text": "2026-07-21 客户：希望增加开发需求的新建按钮，并且导入截图后可以自动整理。",
            "evidence": [],
        }
        draft_response = self.client.post(
            "/api/v1/admin/archive/imports/draft",
            headers=headers,
            json=payload,
        )
        self.assertEqual(draft_response.status_code, 200)
        draft_result = draft_response.json()
        self.assertEqual(draft_result["source"], "fallback")
        self.assertGreaterEqual(len(draft_result["drafts"]), 1)

        drafts = [
            {
                "title": item["title"],
                "module": item["module"],
                "category": item["category"],
                "priority": item["priority"],
                "requester": item["requester"],
                "source_date": item["sourceDate"],
                "source_text": item["sourceText"],
                "description": item["description"],
                "acceptance_criteria": item["acceptance"],
                "owner": item["owner"],
                "planned_release": item["plannedRelease"],
                "evidence": item["evidence"],
                "confidence": item["confidence"],
            }
            for item in draft_result["drafts"]
        ]
        save_response = self.client.post(
            "/api/v1/admin/archive/imports/analyze",
            headers=headers,
            json={**payload, "drafts": drafts},
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(len(save_response.json()["requirements"]), len(drafts))

    @patch("app.api.v1.routers.admin_archive.save_media", return_value="/media/archive-evidence/test.png")
    @patch("app.services.archive.call_ai")
    def test_archive_can_send_screenshot_evidence_to_configured_ai(self, call_ai, _save_media):
        db = self.SessionLocal()
        for key, value in {
            "AI_API_BASE": "https://example.invalid/v1",
            "AI_MODEL": "test-model",
            "AI_API_KEY": "test-key",
            "AI_VISION_ENABLED": "true",
        }.items():
            setting = db.scalar(
                select(IntegrationSetting).where(
                    IntegrationSetting.group == "ai",
                    IntegrationSetting.key == key,
                )
            )
            setting.value = value
        db.commit()
        db.close()
        call_ai.return_value = json.dumps(
            {
                "requirements": [
                    {
                        "title": "截图中的开发需求",
                        "module": "开发需求",
                        "category": "新功能",
                        "priority": "中",
                        "source_date": "2026-07-21",
                        "source_text": "请识别截图中的需求",
                        "description": "根据截图整理需求。",
                        "acceptance_criteria": "可以保存为需求记录。",
                    }
                ]
            }
        )
        headers = self.login_headers()
        upload_response = self.client.post(
            "/api/v1/admin/archive/imports/attachments",
            headers=headers,
            files={"file": ("chat.png", b"fake-image", "image/png")},
        )
        self.assertEqual(upload_response.status_code, 200)
        self.assertEqual(upload_response.json()["url"], "/media/archive-evidence/test.png")

        with patch("app.services.archive._image_data_urls", return_value=["data:image/png;base64,ZmFrZQ=="]) as image_urls:
            draft_response = self.client.post(
                "/api/v1/admin/archive/imports/draft",
                headers=headers,
                json={
                    "source_name": "chat.png",
                    "source_type": "image",
                    "contact": "测试客户",
                    "raw_text": "[上传截图：chat.png]",
                    "evidence": [upload_response.json()["url"]],
                },
            )
        self.assertEqual(draft_response.status_code, 200)
        self.assertEqual(draft_response.json()["source"], "ai")
        self.assertEqual(draft_response.json()["drafts"][0]["title"], "截图中的开发需求")
        image_urls.assert_called_once()
        self.assertTrue(call_ai.call_args.args[3][0].startswith("data:image/png"))

    @patch("app.services.archive.call_ai")
    def test_archive_ai_draft_normalizes_null_date_and_text_confidence(self, call_ai):
        db = self.SessionLocal()
        for key, value in {"AI_API_BASE": "https://example.invalid/v1", "AI_MODEL": "test-model", "AI_API_KEY": "test-key"}.items():
            setting = db.scalar(select(IntegrationSetting).where(IntegrationSetting.group == "ai", IntegrationSetting.key == key))
            setting.value = value
        db.commit()
        db.close()
        call_ai.return_value = json.dumps(
            {"requirements": [{
                "title": "展示完整识别错误",
                "category": "新功能",
                "priority": "高",
                "source_date": None,
                "source_text": "识别失败时需要显示完整错误。",
                "description": "新增独立错误弹窗。",
                "acceptance_criteria": "管理员可以看到完整错误详情。",
                "confidence": "高",
            }]}
        )

        response = self.client.post(
            "/api/v1/admin/archive/imports/draft",
            headers=self.login_headers(),
            json={"raw_text": "识别失败时显示完整错误", "contact": "测试客户"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "ai")
        self.assertEqual(response.json()["drafts"][0]["sourceDate"], date.today().isoformat())
        self.assertEqual(response.json()["drafts"][0]["confidence"], 88)

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

    def test_map_spot_uses_same_origin_media_proxy_for_oss_cover(self):
        db = self.SessionLocal()
        values = {
            "MEDIA_STORAGE_PROVIDER": "aliyun_oss",
            "ALIYUN_OSS_ENDPOINT": "oss-cn-chengdu.aliyuncs.com",
            "ALIYUN_OSS_REGION": "cn-chengdu",
            "ALIYUN_OSS_BUCKET": "hiddengems",
        }
        for key, value in values.items():
            setting = db.scalar(
                select(IntegrationSetting).where(
                    IntegrationSetting.group == "object_storage",
                    IntegrationSetting.key == key,
                )
            )
            setting.value = value
        image = db.get(SpotImage, 1)
        image.image_url = "https://hiddengems.oss-cn-chengdu.aliyuncs.com/spots/2026/07/cover.jpg"
        db.commit()
        db.close()

        response = self.client.get("/api/v1/spots/map?lang=zh-CN&explore_points=120")

        self.assertEqual(response.status_code, 200)
        cover_url = response.json()[0]["cover_image_url"]
        self.assertTrue(
            cover_url.startswith("https://hiddengems.oss-cn-chengdu.aliyuncs.com/spots/2026/07/cover.jpg?")
            or cover_url == "/api/v1/media/spots/2026/07/cover.jpg?v=1"
        )

    @patch("app.api.v1.routers.admin_spots.cache_remote_image", side_effect=lambda _db, url: url)
    def test_spot_update_keeps_existing_wechat_channel_video(self, _cache_remote_image):
        db = self.SessionLocal()
        video = WechatChannelVideo(
            spot_id=1,
            finder_user_name="finder-user",
            feed_id="feed-id",
            title="原始标题",
            cover_url="https://example.com/cover.jpg",
        )
        db.add(video)
        db.commit()
        db.close()

        response = self.client.patch(
            "/api/v1/admin/spots/1",
            headers=self.login_headers(),
            json={
                "wechat_channel_videos": [
                    {
                        "media_type": "wechat_channel",
                        "finder_user_name": "finder-user",
                        "feed_id": "feed-id",
                        "title": "更新后的标题",
                        "cover_url": "https://example.com/cover.jpg",
                        "sort_order": 1,
                        "is_active": True,
                    }
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        db = self.SessionLocal()
        videos = db.scalars(select(WechatChannelVideo).where(WechatChannelVideo.spot_id == 1)).all()
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].title, "更新后的标题")
        self.assertEqual(videos[0].sort_order, 1)
        db.close()

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

    def test_locked_nearby_spots_hide_coordinates_and_include_preview_media(self):
        db = self.SessionLocal()
        user = db.get(MiniProgramUser, 1)
        user.explore_points = 20
        spot = db.get(ScenicSpot, 1)
        spot.summary_zh = "云海景观很适合远观。入口在黔东南州方向。"
        spot.description_zh = "请尊重自然环境。坐标：25.7436, 108.5062。"
        image = db.get(SpotImage, 1)
        image.caption = "从江县停车入口附近。"
        db.add(user)
        db.add(spot)
        db.add(image)
        db.commit()
        db.close()

        response = self.client.get(
            "/api/v1/spots/locked-nearby?user_id=1&lang=zh-CN&latitude=25.7436&longitude=108.5062&radius_km=5"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], 1)
        self.assertNotIn("latitude", data[0])
        self.assertNotIn("longitude", data[0])
        self.assertEqual(data[0]["images"][0]["image_url"], "/media/spots/demo.jpg")

        count_response = self.client.get(
            "/api/v1/spots/locked-nearby/count?user_id=1&latitude=25.7436&longitude=108.5062&radius_km=5"
        )
        self.assertEqual(count_response.status_code, 200)
        self.assertEqual(count_response.json()["count"], len(data))

        detail_response = self.client.get("/api/v1/spots/locked-preview/1?user_id=1&lang=zh-CN")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["id"], 1)
        self.assertEqual(detail["images"][0]["image_url"], "/media/spots/demo.jpg")
        self.assertIsNone(detail["images"][0]["caption"])
        self.assertEqual(detail["summary"], "云海景观很适合远观。")
        self.assertEqual(detail["description"], "请尊重自然环境。")
        self.assertNotIn("latitude", detail)
        self.assertNotIn("longitude", detail)
        self.assertNotIn("city", detail)
        self.assertNotIn("county", detail)
        self.assertNotIn("distance_km", detail)

        db = self.SessionLocal()
        user = db.get(MiniProgramUser, 1)
        user.explore_points = 120
        db.add(user)
        db.commit()
        db.close()
        unlocked_response = self.client.get("/api/v1/spots/locked-preview/1?user_id=1&lang=zh-CN")
        self.assertEqual(unlocked_response.status_code, 403)

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
                "image_url": "/media/mini-shares/checkin-photo.jpg",
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
                "image_url": "/media/mini-shares/checkin-far.jpg",
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

    def test_admin_can_configure_checkin_route_risk_settings(self):
        headers = self.login_headers()
        response = self.client.patch(
            "/api/v1/admin/checkins/risk-settings",
            headers=headers,
            json={
                "tencent_lbs_web_service_key": "test-route-key",
                "tencent_lbs_base_url": "https://apis.map.qq.com",
                "route_warn_ratio": 0.65,
                "route_suspicious_ratio": 0.85,
                "warning_limit": 4,
                "suspicious_limit": 6,
                "watch_limit": 11,
                "repeat_window_hours": 36,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["web_service_key_configured"])
        self.assertEqual(response.json()["warning_limit"], 4)

        response = self.client.get("/api/v1/admin/checkins/risk-settings", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["repeat_window_hours"], 36)

    def test_repeated_checkin_is_recorded_as_watch_risk(self):
        payload = {
            "user_id": 1,
            "spot_id": 1,
            "latitude": "25.7436",
            "longitude": "108.5062",
            "image_url": "/media/checkins/test.jpg",
        }
        first = self.client.post("/api/v1/mini/checkins", json=payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["risk_status"], "normal")

        second = self.client.post("/api/v1/mini/checkins", json=payload)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["risk_status"], "watch")
        self.assertIn("重点关注", second.json()["risk_reason"])

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

        spot_role_response = self.client.post(
            "/api/v1/admin/roles",
            headers=super_headers,
            json={
                "code": "spot_manager",
                "name": "秘境管理员",
                "permissions": ["spots:read", "spots:create", "spots:update", "spots:delete"],
            },
        )
        self.assertEqual(spot_role_response.status_code, 201)
        admin_response = self.client.post(
            "/api/v1/admin/roles/admins",
            headers=super_headers,
            json={"username": "spotmanager", "password": "manager-pass-123", "role": "spot_manager"},
        )
        self.assertEqual(admin_response.status_code, 201)
        login_response = self.client.post(
            "/api/v1/admin/login",
            json={"username": "spotmanager", "password": "manager-pass-123"},
        )
        spot_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        self.assertEqual(self.client.get("/api/v1/admin/spots", headers=spot_headers).status_code, 200)
        self.assertEqual(
            self.client.patch(
                "/api/v1/admin/spots/1",
                headers=spot_headers,
                json={"summary_zh": "管理员可编辑。"},
            ).status_code,
            200,
        )
        image_response = self.client.post(
            "/api/v1/admin/content/spots/1/images",
            headers=spot_headers,
            data={"caption": "管理员上传", "sort_order": "3"},
            files={"file": ("spot.png", b"fake-image", "image/png")},
        )
        self.assertEqual(image_response.status_code, 201)
        self.assertEqual(
            self.client.delete(
                f"/api/v1/admin/content/spot-images/{image_response.json()['id']}",
                headers=spot_headers,
            ).status_code,
            204,
        )

    def test_spot_video_channel_urls_are_returned_in_detail(self):
        headers = self.login_headers()
        urls = [
            "https://channels.weixin.qq.com/platform/post/example-one",
            "https://channels.weixin.qq.com/platform/post/example-two",
        ]
        update_response = self.client.patch(
            "/api/v1/admin/spots/1",
            headers=headers,
            json={"video_channel_urls": urls},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["video_channel_urls"], urls)

        detail_response = self.client.get("/api/v1/spots/1?lang=zh-CN&user_id=1&explore_points=120")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["video_channel_urls"], urls)

    def test_seed_admin_roles_adds_spot_permissions_to_existing_operator(self):
        db = self.SessionLocal()
        db.add(
            AdminRole(
                code="operator",
                name="运营管理员",
                permissions_json=json.dumps(["tags:read"]),
                is_active=True,
            )
        )
        db.commit()
        seed_admin_roles(db)
        db.commit()
        role = db.scalar(select(AdminRole).where(AdminRole.code == "operator"))
        db.close()

        self.assertEqual(set(json.loads(role.permissions_json)), set(ALL_PERMISSIONS))

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
                "unlock_rule_zh": "完成推荐和好友注册后可解锁。",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["checkin_points"], 6)
        self.assertTrue(data["requires_membership"])
        self.assertEqual(data["unlock_benefit_zh"], "更新后的解锁权益。")
        self.assertEqual(data["unlock_rule_zh"], "完成推荐和好友注册后可解锁。")

        rules_response = self.client.get("/api/v1/spots/pass-level-rules?lang=zh-CN")
        self.assertEqual(rules_response.status_code, 200)
        level_rule = next(item for item in rules_response.json() if item["level"] == 2)
        self.assertEqual(level_rule["description"], "完成推荐和好友注册后可解锁。")

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
        self.assertEqual(approve_response.json()["awarded_explore_points"], 10)
        self.assertIsNotNone(approve_response.json()["promoted_spot_image_id"])

        checkin_detail = self.client.get("/api/v1/admin/checkins/1", headers=headers)
        self.assertEqual(checkin_detail.status_code, 200)
        self.assertEqual(checkin_detail.json()["spot"]["name_zh"], "加榜梯田晨雾点")
        self.assertEqual(checkin_detail.json()["user"]["checkin_risk_level"], "normal")
        self.assertEqual(checkin_detail.json()["risk_rating"]["level"], "normal")
        self.assertEqual(len(checkin_detail.json()["risk_rating"]["rules"]), 3)

        spot_checkins_response = self.client.get("/api/v1/admin/spots/1/checkins", headers=headers)
        self.assertEqual(spot_checkins_response.status_code, 200)
        self.assertEqual(spot_checkins_response.json()["items"][0]["media_type"], "image")
        self.assertEqual(spot_checkins_response.json()["items"][0]["promoted_spot_image_id"], approve_response.json()["promoted_spot_image_id"])

        detail_response = self.client.get("/api/v1/spots/1?lang=zh-CN&user_id=1&explore_points=120")
        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(any(item["image_url"] == "/media/mini-shares/checkin-photo.jpg" for item in detail_response.json()["images"]))

        user_response = self.client.get("/api/v1/admin/users/1", headers=headers)
        self.assertEqual(user_response.json()["checkin_count"], 9)
        self.assertEqual(user_response.json()["explore_points"], 130)
        self.assertEqual(user_response.json()["checkin_risk_level"], "normal")

        approve_again_response = self.client.patch(
            "/api/v1/admin/checkins/1/review",
            headers=headers,
            json={"status": "approved", "review_note": "重复审核。"},
        )
        self.assertEqual(approve_again_response.status_code, 200)
        user_again_response = self.client.get("/api/v1/admin/users/1", headers=headers)
        self.assertEqual(user_again_response.json()["checkin_count"], 9)
        self.assertEqual(user_again_response.json()["explore_points"], 130)

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
