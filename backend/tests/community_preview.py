"""Seed an isolated SQLite database for manual community UI verification.

Run only with DATABASE_URL pointing to a disposable /tmp database.
"""
import os
import subprocess

from app.db.session import SessionLocal
from app.models.community import CommunityUpload, EcoSubmission, FoodPolicy, FoodSubmission
from app.models.spot import ScenicSpot
from app.models.user import MiniProgramUser, UserSpotUnlock
from app.services.bootstrap import create_tables, seed_initial_data
from app.services.community import policy_out
from app.services.media_storage import LOCAL_UPLOAD_BASE
import json


if __name__ == "__main__":
    if not os.environ.get("DATABASE_URL", "").startswith("sqlite:////tmp/gz-community-"):
        raise SystemExit("Refusing to seed a non-preview database")
    create_tables()
    seed_initial_data()
    with SessionLocal() as db:
        user = MiniProgramUser(openid="community-preview-only", nickname="环保测试用户", explore_points=0, benefit_points=0)
        db.add(user); db.flush()
        spot = ScenicSpot(name_zh="测试环保秘境", name_en="Eco Preview", summary_zh="测试", summary_en="Test", city="测试", county="测试", latitude=26, longitude=106,
                          recommendation_level=2, required_explore_points=1, review_status="approved")
        db.add(spot); db.flush()
        db.add(UserSpotUnlock(user_id=user.id, spot_id=spot.id, status="active"))
        video = LOCAL_UPLOAD_BASE / "community-preview" / "test.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25", "-t", "3", "-pix_fmt", "yuv420p", str(video)], check=True)
        media = CommunityUpload(user_id=user.id, purpose="eco", media_type="video", media_url="/media/community-preview/test.mp4", duration=3, width=320, height=240, size_bytes=video.stat().st_size, used=True)
        db.add(media); db.flush()
        db.add(EcoSubmission(user_id=user.id, spot_id=spot.id, level=2, category="A", upload_id=media.id, ai_status="manual_required", ai_note="测试环境未接入真实大模型，等待人工复核"))
        policy = FoodPolicy(name="预览美食规则", all_users=True, reward_points=5)
        db.add(policy); db.flush()
        db.add(FoodSubmission(user_id=user.id, policy_id=policy.id, policy_json=json.dumps(policy_out(policy)), title="测试美食", content="仅供本地功能验收", upload_ids_json="[]", reward_points=5))
        db.commit()
        print("Preview fixtures created", user.id, spot.id)
