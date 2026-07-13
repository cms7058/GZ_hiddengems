import time
from datetime import datetime, timedelta

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models.admin import AdminUser
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.integration import IntegrationSetting
from app.models.spot import ScenicSpot, SpotChildPoint, Tag
from app.models.user import (
    CheckinRecord,
    MembershipPlan,
    MiniProgramUser,
    PassLevelSetting,
    UserMembership,
)
from app.services.security import hash_password
from app.services.integrations import seed_integration_settings


def wait_for_database(max_attempts: int = 30, delay_seconds: int = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError:
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


def create_tables() -> None:
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns()


def ensure_runtime_columns() -> None:
    column_specs = {
        "travel_notes": {"image_url": "VARCHAR(512) NULL"},
        "user_comments": {"image_url": "VARCHAR(512) NULL"},
        "lifestyle_recommendations": {
            "image_url": "VARCHAR(512) NULL",
            "spot_id": "INT NULL",
        },
        "spot_images": {
            "media_type": "VARCHAR(32) NOT NULL DEFAULT 'image'",
        },
        "mini_program_users": {
            "avatar_url": "VARCHAR(512) NULL",
            "explore_points": "INT NOT NULL DEFAULT 0",
            "can_upload_image": "BOOLEAN NOT NULL DEFAULT TRUE",
            "can_upload_video": "BOOLEAN NOT NULL DEFAULT TRUE",
            "can_comment": "BOOLEAN NOT NULL DEFAULT TRUE",
            "can_checkin": "BOOLEAN NOT NULL DEFAULT TRUE",
        },
        "checkin_records": {
            "media_url": "VARCHAR(512) NULL",
            "media_type": "VARCHAR(32) NULL",
        },
        "pass_level_settings": {
            "marker_color": "VARCHAR(16) NOT NULL DEFAULT '#2f6b4f'",
            "required_explore_points": "INT NOT NULL DEFAULT 0",
        },
        "membership_plans": {
            "required_explore_points": "INT NOT NULL DEFAULT 0",
        },
        "scenic_spots": {
            "required_explore_points": "INT NOT NULL DEFAULT 0",
            "river_name": "VARCHAR(128) NULL",
            "river_upstream_latitude": "DOUBLE NULL",
            "river_upstream_longitude": "DOUBLE NULL",
        },
    }
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, specs in column_specs.items():
            if table not in table_names:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table)}
            for column_name, column_type in specs.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))
        if "lifestyle_recommendations" in table_names:
            connection.execute(
                text("UPDATE lifestyle_recommendations SET spot_id = 1 WHERE spot_id IS NULL")
            )


def seed_initial_data() -> None:
    with Session(engine) as db:
        seed_admin(db)
        seed_tags_and_spots(db)
        seed_users(db)
        seed_pass_settings(db)
        seed_memberships(db)
        seed_checkins(db)
        seed_content(db)
        seed_integration_settings(db)
        db.commit()


def seed_admin(db: Session) -> None:
    exists = db.scalar(
        select(AdminUser).where(AdminUser.username == settings.initial_admin_username)
    )
    if exists:
        return

    db.add(
        AdminUser(
            username=settings.initial_admin_username,
            password_hash=hash_password(settings.initial_admin_password),
            role="super_admin",
            is_active=True,
        )
    )


def seed_tags_and_spots(db: Session) -> None:
    if db.scalar(select(Tag).limit(1)):
        return

    photo = Tag(id=1, name_zh="摄影", name_en="Photography", icon="camera", sort_order=10)
    hiking = Tag(id=2, name_zh="徒步", name_en="Hiking", icon="footprints", sort_order=20)
    camping = Tag(id=3, name_zh="露营", name_en="Camping", icon="tent", sort_order=30)
    waterfall = Tag(id=4, name_zh="瀑布", name_en="Waterfall", icon="waves", sort_order=40)
    village = Tag(id=5, name_zh="古寨", name_en="Ancient Village", icon="landmark", sort_order=50)
    easy = Tag(id=6, name_zh="低难度", name_en="Easy", icon="leaf", sort_order=60)

    spot_one = ScenicSpot(
        id=1,
        name_zh="加榜梯田晨雾点",
        name_en="Jiabang Rice Terraces Mist Viewpoint",
        summary_zh="适合清晨摄影的梯田观景点，云雾和村寨层次明显。",
        summary_en="A quiet rice terrace viewpoint known for morning mist and layered village scenery.",
        description_zh="建议日出前抵达，雨后或秋收季更容易拍到云雾层次。请避开村民耕作区域。",
        description_en="Arrive before sunrise. Mist is more likely after rain or during harvest season. Keep away from active farmland.",
        city="黔东南州",
        county="从江县",
        latitude=25.7436,
        longitude=108.5062,
        visibility_level="public",
        review_status="approved",
        recommendation_level=5,
        required_explore_points=0,
        checkin_radius_meters=300,
        tags=[photo, easy],
    )
    spot_two = ScenicSpot(
        id=2,
        name_zh="乌蒙山隐秘露营地",
        name_en="Wumeng Mountain Hidden Campsite",
        summary_zh="适合有经验玩家的高海拔露营地，天气变化快。",
        summary_en="A high-altitude campsite for experienced travelers, with fast-changing weather.",
        description_zh="需提前确认天气和道路情况，夜间温差大，不建议新手单独前往。",
        description_en="Check weather and road conditions in advance. Nights are cold and solo beginner trips are not recommended.",
        city="六盘水市",
        county="盘州市",
        latitude=26.1068,
        longitude=104.6341,
        visibility_level="protected",
        review_status="approved",
        recommendation_level=4,
        required_explore_points=120,
        checkin_radius_meters=500,
        tags=[hiking, camping],
    )

    db.add_all([photo, hiking, camping, waterfall, village, easy, spot_one, spot_two])


def seed_users(db: Session) -> None:
    if db.scalar(select(MiniProgramUser).limit(1)):
        return

    db.add_all(
        [
            MiniProgramUser(
                openid="demo-openid-001",
                nickname="山野摄影师",
                phone="13800000001",
                language="zh-CN",
                explorer_level=2,
                explore_points=180,
                checkin_count=8,
                contribution_count=3,
                eco_credit=96,
                is_member=True,
            ),
            MiniProgramUser(
                openid="demo-openid-002",
                nickname="HiddenGem Fan",
                language="en-US",
                explorer_level=1,
                explore_points=40,
                checkin_count=2,
                contribution_count=0,
                eco_credit=100,
                is_member=False,
            ),
        ]
    )


def seed_pass_settings(db: Session) -> None:
    if db.scalar(select(PassLevelSetting).limit(1)):
        return

    db.add_all(
        [
            PassLevelSetting(
                level=0,
                name_zh="初识者",
                name_en="Newcomer",
                required_explore_points=0,
                required_checkins=0,
                required_contributions=0,
                required_eco_credit=0,
                marker_color="#7a8179",
                unlock_benefit_zh="可浏览公开秘境和基础标签。",
                unlock_benefit_en="Browse public hidden gems and basic tags.",
            ),
            PassLevelSetting(
                level=1,
                name_zh="探索者",
                name_en="Explorer",
                required_explore_points=0,
                required_checkins=1,
                required_contributions=0,
                required_eco_credit=80,
                marker_color="#2f6b4f",
                unlock_benefit_zh="解锁基础打卡任务和更多推荐理由。",
                unlock_benefit_en="Unlock basic check-in tasks and richer recommendations.",
            ),
            PassLevelSetting(
                level=2,
                name_zh="行者",
                name_en="Wayfarer",
                required_explore_points=0,
                required_checkins=5,
                required_contributions=1,
                required_eco_credit=85,
                marker_color="#2f7fb8",
                unlock_benefit_zh="可查看部分会员级秘境的更精确区域。",
                unlock_benefit_en="View more accurate areas for selected member-level spots.",
            ),
            PassLevelSetting(
                level=3,
                name_zh="寻境师",
                name_en="Pathfinder",
                required_explore_points=0,
                required_checkins=15,
                required_contributions=3,
                required_eco_credit=90,
                requires_membership=True,
                marker_color="#7a5ccf",
                unlock_benefit_zh="可申请查看保护级秘境，并参与内容共创。",
                unlock_benefit_en="Request protected spots and join content co-creation.",
            ),
            PassLevelSetting(
                level=4,
                name_zh="秘境猎人",
                name_en="Hidden Gem Hunter",
                required_explore_points=0,
                required_checkins=35,
                required_contributions=8,
                required_eco_credit=92,
                requires_membership=True,
                marker_color="#c27a2c",
                unlock_benefit_zh="优先体验高阶路线和达人任务。",
                unlock_benefit_en="Get early access to advanced routes and expert tasks.",
            ),
            PassLevelSetting(
                level=5,
                name_zh="守护者",
                name_en="Guardian",
                required_explore_points=0,
                required_checkins=60,
                required_contributions=15,
                required_eco_credit=95,
                requires_membership=True,
                marker_color="#c43d3d",
                unlock_benefit_zh="参与敏感秘境守护、审核和保护策略建议。",
                unlock_benefit_en="Join sensitive spot stewardship, review, and protection planning.",
            ),
        ]
    )


def seed_memberships(db: Session) -> None:
    if db.scalar(select(MembershipPlan).limit(1)):
        return

    monthly = MembershipPlan(
        id=1,
        name_zh="月度探索会员",
        name_en="Monthly Explorer",
        duration_days=30,
        price_cents=1900,
        required_explore_points=100,
        benefits_zh="解锁会员秘境区域、会员任务和路线建议。",
        benefits_en="Unlock member spot areas, member tasks, and route suggestions.",
    )
    yearly = MembershipPlan(
        id=2,
        name_zh="年度守护会员",
        name_en="Annual Guardian",
        duration_days=365,
        price_cents=19900,
        required_explore_points=500,
        benefits_zh="包含全年会员权益、保护级秘境申请和达人共创资格。",
        benefits_en="Includes annual benefits, protected spot requests, and expert co-creation access.",
    )
    db.add_all([monthly, yearly])
    db.flush()

    db.add(
        UserMembership(
            user_id=1,
            plan_id=1,
            status="active",
            started_at=datetime.utcnow() - timedelta(days=5),
            expires_at=datetime.utcnow() + timedelta(days=25),
        )
    )


def seed_checkins(db: Session) -> None:
    if db.scalar(select(CheckinRecord).limit(1)):
        return

    db.add_all(
        [
            CheckinRecord(
                user_id=1,
                spot_id=1,
                status="pending",
                latitude="25.7431",
                longitude="108.5060",
                image_url="https://example.com/checkins/jiabang-demo.jpg",
                note="清晨到达，天气多云，有晨雾。",
            ),
            CheckinRecord(
                user_id=2,
                spot_id=2,
                status="rejected",
                latitude="26.1000",
                longitude="104.6300",
                note="定位距离较远。",
                review_note="未进入打卡范围。",
            ),
        ]
    )


def seed_content(db: Session) -> None:
    if not db.scalar(select(SpotImage).limit(1)):
        db.add_all(
            [
                SpotImage(
                    spot_id=1,
                    image_url="/media/spots/demo-jiabang.jpg",
                    caption="加榜梯田晨雾示意图",
                    sort_order=1,
                    is_cover=True,
                ),
                SpotImage(
                    spot_id=2,
                    image_url="/media/spots/demo-wumeng.jpg",
                    caption="乌蒙山露营地示意图",
                    sort_order=1,
                    is_cover=True,
                ),
            ]
        )

    if not db.scalar(select(TravelNote).limit(1)):
        db.add(
            TravelNote(
                user_id=1,
                spot_id=1,
                title="加榜梯田清晨路线记录",
                content="日出前抵达观景点，路面湿滑但视野很好，建议带防滑鞋。",
                image_url="/media/travel-notes/demo-note.jpg",
                status="pending",
            )
        )

    if not db.scalar(select(UserComment).limit(1)):
        db.add_all(
            [
                UserComment(
                    user_id=1,
                    spot_id=1,
                    content="适合摄影，但不要踩进梯田。",
                    image_url="/media/comments/demo-comment.jpg",
                    status="approved",
                ),
                UserComment(
                    user_id=2,
                    spot_id=2,
                    content="想知道夜间是否安全露营？",
                    status="pending",
                ),
            ]
        )

    if db.scalar(select(LifestyleRecommendation).limit(1)):
        return

    db.add_all(
        [
            LifestyleRecommendation(
                spot_id=1,
                category="clothing",
                name_zh="山地速干防滑装备",
                name_en="Mountain Quick-Dry Gear",
                summary_zh="适合梯田、瀑布和雨后徒步场景，建议搭配防滑鞋。",
                summary_en="For terraces, waterfalls, and wet trails. Anti-slip shoes are recommended.",
                city="黔东南州",
                county="从江县",
                price_level="mid",
                recommendation_level=4,
                image_url="/media/recommendations/demo-gear.jpg",
            ),
            LifestyleRecommendation(
                spot_id=1,
                category="food",
                name_zh="从江酸汤鱼本地小馆",
                name_en="Congjiang Sour Soup Fish",
                summary_zh="适合加榜梯田返程用餐，口味偏酸辣。",
                summary_en="A sour and spicy local meal after visiting Jiabang terraces.",
                city="黔东南州",
                county="从江县",
                address="从江县城区",
                price_level="mid",
                recommendation_level=4,
                image_url="/media/recommendations/demo-food.jpg",
            ),
            LifestyleRecommendation(
                spot_id=1,
                category="hotel",
                name_zh="梯田观景民宿",
                name_en="Terrace View Homestay",
                summary_zh="靠近观景点，适合日出摄影用户。",
                summary_en="Near the viewpoint and suitable for sunrise photographers.",
                city="黔东南州",
                county="从江县",
                price_level="mid",
                recommendation_level=3,
            ),
            LifestyleRecommendation(
                spot_id=1,
                category="transport",
                name_zh="从江包车向导",
                name_en="Congjiang Local Driver Guide",
                summary_zh="适合山路不熟的新用户，建议提前一天预约。",
                summary_en="Useful for first-time visitors unfamiliar with mountain roads. Book one day ahead.",
                city="黔东南州",
                county="从江县",
                contact="提前预约",
                price_level="high",
                recommendation_level=4,
            ),
        ]
    )
