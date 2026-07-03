# 贵州秘境后台

FastAPI 后台服务，第一阶段支撑小程序地图首页、标签筛选、秘境详情和管理后台基础数据维护。

## 本地开发

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

管理后台页面：

```text
http://127.0.0.1:8000/admin
```

## Docker 部署

```bash
cd backend
cp .env.example .env
docker compose up -d --build
```

MySQL 首次启动会自动执行 `sql/001_init.sql`，创建标签、秘境和关联表，并写入少量演示数据。

默认管理员：

- 用户名：`admin`
- 密码：`admin123456`

生产环境首次登录后应立即修改默认密码，并替换 `.env` 中的 `JWT_SECRET_KEY`。

## 当前 API

- `GET /health`
- `POST /api/v1/admin/login`
- `GET /api/v1/admin/me`
- `GET /api/v1/tags`
- `GET /api/v1/spots/map`
- `GET /api/v1/spots/{spot_id}`
- `GET /api/v1/admin/spots`
- `POST /api/v1/admin/spots`
- `GET /api/v1/admin/spots/{spot_id}`
- `PATCH /api/v1/admin/spots/{spot_id}`
- `PATCH /api/v1/admin/spots/{spot_id}/review`
- `DELETE /api/v1/admin/spots/{spot_id}`
- `GET /api/v1/admin/tags`
- `POST /api/v1/admin/tags`
- `PATCH /api/v1/admin/tags/{tag_id}`
- `DELETE /api/v1/admin/tags/{tag_id}`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/{user_id}`
- `PATCH /api/v1/admin/users/{user_id}`
- `GET /api/v1/admin/pass-settings`
- `PATCH /api/v1/admin/pass-settings/{setting_id}`
- `GET /api/v1/admin/memberships/plans`
- `PATCH /api/v1/admin/memberships/plans/{plan_id}`
- `GET /api/v1/admin/memberships/records`
- `GET /api/v1/admin/checkins`
- `PATCH /api/v1/admin/checkins/{checkin_id}/review`
- `GET /api/v1/admin/content/spots/{spot_id}/images`
- `POST /api/v1/admin/content/spots/{spot_id}/images`
- `PATCH /api/v1/admin/content/spot-images/{image_id}`
- `GET /api/v1/admin/content/travel-notes`
- `PATCH /api/v1/admin/content/travel-notes/{note_id}/status`
- `GET /api/v1/admin/content/comments`
- `PATCH /api/v1/admin/content/comments/{comment_id}/status`
- `GET /api/v1/admin/content/recommendations`
- `POST /api/v1/admin/content/recommendations`
- `PATCH /api/v1/admin/content/recommendations/{recommendation_id}`

管理后台接口需要 `Authorization: Bearer <token>`。
