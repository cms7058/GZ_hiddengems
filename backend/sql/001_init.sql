SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name_zh VARCHAR(64) NOT NULL,
    name_en VARCHAR(64) NOT NULL,
    icon VARCHAR(64) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_tags_name_zh (name_zh),
    KEY ix_tags_active_sort (is_active, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scenic_spots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    spot_code VARCHAR(8) NULL UNIQUE,
    name_zh VARCHAR(128) NOT NULL,
    name_en VARCHAR(128) NOT NULL,
    locked_name_zh VARCHAR(128) NULL,
    locked_name_en VARCHAR(128) NULL,
    summary_zh VARCHAR(512) NOT NULL,
    summary_en VARCHAR(512) NOT NULL,
    description_zh TEXT NULL,
    description_en TEXT NULL,
    city VARCHAR(64) NOT NULL,
    county VARCHAR(64) NOT NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    river_name VARCHAR(128) NULL,
    river_upstream_latitude DOUBLE NULL,
    river_upstream_longitude DOUBLE NULL,
    visibility_level VARCHAR(32) NOT NULL DEFAULT 'public',
    review_status VARCHAR(32) NOT NULL DEFAULT 'draft',
    recommendation_level INT NOT NULL DEFAULT 1,
    required_explore_points INT NOT NULL DEFAULT 0,
    checkin_radius_meters INT NOT NULL DEFAULT 300,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_spots_map (is_active, review_status, recommendation_level),
    KEY ix_spots_location (latitude, longitude),
    KEY ix_spots_visibility (visibility_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS spot_tags (
    spot_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (spot_id, tag_id),
    CONSTRAINT fk_spot_tags_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id) ON DELETE CASCADE,
    CONSTRAINT fk_spot_tags_tag FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_admin_users_username (username),
    KEY ix_admin_users_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `group` VARCHAR(32) NOT NULL,
    `key` VARCHAR(96) NOT NULL,
    value TEXT NULL,
    label_zh VARCHAR(128) NOT NULL,
    label_en VARCHAR(128) NOT NULL,
    input_type VARCHAR(32) NOT NULL DEFAULT 'text',
    is_secret BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_integration_group_key (`group`, `key`),
    KEY ix_integration_settings_group (`group`),
    KEY ix_integration_settings_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mini_program_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(128) NOT NULL,
    nickname VARCHAR(64) NOT NULL,
    avatar_url VARCHAR(512) NULL,
    phone VARCHAR(32) NULL,
    language VARCHAR(16) NOT NULL DEFAULT 'zh-CN',
    explorer_level INT NOT NULL DEFAULT 0,
    explore_points INT NOT NULL DEFAULT 0,
    checkin_count INT NOT NULL DEFAULT 0,
    contribution_count INT NOT NULL DEFAULT 0,
    eco_credit INT NOT NULL DEFAULT 100,
    is_member BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_mini_program_users_openid (openid),
    KEY ix_mini_program_users_level (explorer_level),
    KEY ix_mini_program_users_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pass_level_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level INT NOT NULL,
    name_zh VARCHAR(64) NOT NULL,
    name_en VARCHAR(64) NOT NULL,
    required_checkins INT NOT NULL DEFAULT 0,
    required_contributions INT NOT NULL DEFAULT 0,
    required_eco_credit INT NOT NULL DEFAULT 0,
    requires_membership BOOLEAN NOT NULL DEFAULT FALSE,
    unlock_benefit_zh VARCHAR(512) NOT NULL,
    unlock_benefit_en VARCHAR(512) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_pass_level_settings_level (level),
    KEY ix_pass_level_settings_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS membership_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name_zh VARCHAR(64) NOT NULL,
    name_en VARCHAR(64) NOT NULL,
    duration_days INT NOT NULL DEFAULT 30,
    price_cents INT NOT NULL DEFAULT 0,
    benefits_zh VARCHAR(512) NOT NULL,
    benefits_en VARCHAR(512) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_membership_plans_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_memberships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    started_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_user_memberships_user (user_id),
    KEY ix_user_memberships_plan (plan_id),
    CONSTRAINT fk_user_memberships_user FOREIGN KEY (user_id) REFERENCES mini_program_users(id),
    CONSTRAINT fk_user_memberships_plan FOREIGN KEY (plan_id) REFERENCES membership_plans(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS checkin_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    spot_id INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    latitude VARCHAR(32) NULL,
    longitude VARCHAR(32) NULL,
    image_url VARCHAR(512) NULL,
    media_url VARCHAR(512) NULL,
    media_type VARCHAR(32) NULL,
    note VARCHAR(512) NULL,
    review_note VARCHAR(512) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_checkin_records_user (user_id),
    KEY ix_checkin_records_spot (spot_id),
    KEY ix_checkin_records_status (status),
    CONSTRAINT fk_checkin_records_user FOREIGN KEY (user_id) REFERENCES mini_program_users(id),
    CONSTRAINT fk_checkin_records_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS spot_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    spot_id INT NOT NULL,
    image_url VARCHAR(512) NOT NULL,
    caption VARCHAR(256) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_cover BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_spot_images_spot (spot_id),
    CONSTRAINT fk_spot_images_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS spot_wechat_channel_videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    spot_id INT NOT NULL,
    media_type VARCHAR(32) NOT NULL DEFAULT 'wechat_channel',
    finder_user_name VARCHAR(128) NOT NULL,
    feed_id VARCHAR(256) NOT NULL,
    title VARCHAR(256) NOT NULL,
    cover_url VARCHAR(512) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_spot_wechat_channel_video (spot_id, finder_user_name, feed_id),
    KEY ix_spot_wechat_channel_videos_spot (spot_id),
    KEY ix_spot_wechat_channel_videos_finder (finder_user_name),
    CONSTRAINT fk_spot_wechat_channel_videos_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS travel_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    spot_id INT NULL,
    title VARCHAR(128) NOT NULL,
    content TEXT NOT NULL,
    image_url VARCHAR(512) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_travel_notes_user (user_id),
    KEY ix_travel_notes_spot (spot_id),
    KEY ix_travel_notes_status (status),
    CONSTRAINT fk_travel_notes_user FOREIGN KEY (user_id) REFERENCES mini_program_users(id),
    CONSTRAINT fk_travel_notes_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    spot_id INT NULL,
    content VARCHAR(512) NOT NULL,
    image_url VARCHAR(512) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_user_comments_user (user_id),
    KEY ix_user_comments_spot (spot_id),
    KEY ix_user_comments_status (status),
    CONSTRAINT fk_user_comments_user FOREIGN KEY (user_id) REFERENCES mini_program_users(id),
    CONSTRAINT fk_user_comments_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lifestyle_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    spot_id INT NULL,
    category VARCHAR(32) NOT NULL,
    name_zh VARCHAR(128) NOT NULL,
    name_en VARCHAR(128) NOT NULL,
    summary_zh VARCHAR(512) NOT NULL,
    summary_en VARCHAR(512) NOT NULL,
    city VARCHAR(64) NOT NULL,
    county VARCHAR(64) NOT NULL,
    address VARCHAR(256) NULL,
    contact VARCHAR(128) NULL,
    image_url VARCHAR(512) NULL,
    price_level VARCHAR(32) NOT NULL DEFAULT 'mid',
    recommendation_level INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_lifestyle_recommendations_category (category),
    KEY ix_lifestyle_recommendations_active (is_active),
    KEY ix_lifestyle_recommendations_spot (spot_id),
    CONSTRAINT fk_lifestyle_recommendations_spot FOREIGN KEY (spot_id) REFERENCES scenic_spots(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO integration_settings (`group`, `key`, value, label_zh, label_en, input_type, is_secret, sort_order) VALUES
    ('weather', 'QWEATHER_API_HOST', '', '和风天气 API Host', 'QWeather API Host', 'text', FALSE, 10),
    ('weather', 'QWEATHER_PROJECT_ID', '', '和风项目 ID', 'QWeather Project ID', 'text', FALSE, 20),
    ('weather', 'QWEATHER_KEY_ID', '', '和风凭据 ID', 'QWeather Key ID', 'text', FALSE, 30),
    ('weather', 'QWEATHER_PRIVATE_KEY_FILE', '', 'Ed25519 私钥文件路径', 'Ed25519 Private Key File', 'text', FALSE, 40),
    ('weather', 'QWEATHER_PRIVATE_KEY', '', 'Ed25519 私钥内容', 'Ed25519 Private Key', 'textarea', TRUE, 50),
    ('weather', 'QWEATHER_API_KEY', '', '和风 API KEY', 'QWeather API Key', 'password', TRUE, 60),
    ('weather', 'QWEATHER_JWT_EXPIRE_SECONDS', '900', 'JWT 有效期秒', 'JWT Expire Seconds', 'number', FALSE, 70),
    ('ai', 'AI_PROVIDER', '', '大模型服务商', 'AI Provider', 'text', FALSE, 10),
    ('ai', 'AI_API_BASE', '', '大模型 API 地址', 'AI API Base URL', 'text', FALSE, 20),
    ('ai', 'AI_MODEL', '', '模型名称', 'Model Name', 'text', FALSE, 30),
    ('ai', 'AI_API_KEY', '', '大模型 API KEY', 'AI API Key', 'password', TRUE, 40),
    ('flood', 'FLOOD_API_PROVIDER', '', '洪水接口服务商', 'Flood API Provider', 'text', FALSE, 10),
    ('flood', 'FLOOD_API_BASE', '', '洪水接口地址', 'Flood API Base URL', 'text', FALSE, 20),
    ('flood', 'FLOOD_API_KEY', '', '洪水接口 API KEY', 'Flood API Key', 'password', TRUE, 30);

INSERT INTO tags (id, name_zh, name_en, icon, sort_order, is_active) VALUES
    (1, '摄影', 'Photography', 'camera', 10, TRUE),
    (2, '徒步', 'Hiking', 'footprints', 20, TRUE),
    (3, '露营', 'Camping', 'tent', 30, TRUE),
    (4, '瀑布', 'Waterfall', 'waves', 40, TRUE),
    (5, '古寨', 'Ancient Village', 'landmark', 50, TRUE),
    (6, '低难度', 'Easy', 'leaf', 60, TRUE)
ON DUPLICATE KEY UPDATE
    name_en = VALUES(name_en),
    icon = VALUES(icon),
    sort_order = VALUES(sort_order),
    is_active = VALUES(is_active);

INSERT INTO scenic_spots (
    id,
    name_zh,
    name_en,
    summary_zh,
    summary_en,
    description_zh,
    description_en,
    city,
    county,
    latitude,
    longitude,
    visibility_level,
    review_status,
    recommendation_level,
    required_explore_points,
    checkin_radius_meters,
    is_active
) VALUES
    (
        1,
        '加榜梯田晨雾点',
        'Jiabang Rice Terraces Mist Viewpoint',
        '适合清晨摄影的梯田观景点，云雾和村寨层次明显。',
        'A quiet rice terrace viewpoint known for morning mist and layered village scenery.',
        '建议日出前抵达，雨后或秋收季更容易拍到云雾层次。请避开村民耕作区域。',
        'Arrive before sunrise. Mist is more likely after rain or during harvest season. Keep away from active farmland.',
        '黔东南州',
        '从江县',
        25.7436,
        108.5062,
        'public',
        'approved',
        5,
        0,
        300,
        TRUE
    ),
    (
        2,
        '乌蒙山隐秘露营地',
        'Wumeng Mountain Hidden Campsite',
        '适合有经验玩家的高海拔露营地，天气变化快。',
        'A high-altitude campsite for experienced travelers, with fast-changing weather.',
        '需提前确认天气和道路情况，夜间温差大，不建议新手单独前往。',
        'Check weather and road conditions in advance. Nights are cold and solo beginner trips are not recommended.',
        '六盘水市',
        '盘州市',
        26.1068,
        104.6341,
        'protected',
        'approved',
        4,
        120,
        500,
        TRUE
    )
ON DUPLICATE KEY UPDATE
    review_status = VALUES(review_status),
    is_active = VALUES(is_active);

INSERT IGNORE INTO spot_tags (spot_id, tag_id) VALUES
    (1, 1),
    (1, 6),
    (2, 2),
    (2, 3);

INSERT INTO mini_program_users (
    id,
    openid,
    nickname,
    phone,
    language,
    explorer_level,
    explore_points,
    checkin_count,
    contribution_count,
    eco_credit,
    is_member,
    is_active
) VALUES
    (1, 'demo-openid-001', '山野摄影师', '13800000001', 'zh-CN', 2, 180, 8, 3, 96, TRUE, TRUE),
    (2, 'demo-openid-002', 'HiddenGem Fan', NULL, 'en-US', 1, 40, 2, 0, 100, FALSE, TRUE)
ON DUPLICATE KEY UPDATE
    nickname = VALUES(nickname),
    explorer_level = VALUES(explorer_level),
    explore_points = VALUES(explore_points),
    is_active = VALUES(is_active);

INSERT INTO pass_level_settings (
    level,
    name_zh,
    name_en,
    required_checkins,
    required_contributions,
    required_eco_credit,
    requires_membership,
    unlock_benefit_zh,
    unlock_benefit_en,
    is_active
) VALUES
    (0, '初识者', 'Newcomer', 0, 0, 0, FALSE, '可浏览公开秘境和基础标签。', 'Browse public hidden gems and basic tags.', TRUE),
    (1, '探索者', 'Explorer', 1, 0, 80, FALSE, '解锁基础打卡任务和更多推荐理由。', 'Unlock basic check-in tasks and richer recommendations.', TRUE),
    (2, '行者', 'Wayfarer', 5, 1, 85, FALSE, '可查看部分会员级秘境的更精确区域。', 'View more accurate areas for selected member-level spots.', TRUE),
    (3, '寻境师', 'Pathfinder', 15, 3, 90, TRUE, '可申请查看保护级秘境，并参与内容共创。', 'Request protected spots and join content co-creation.', TRUE),
    (4, '秘境猎人', 'Hidden Gem Hunter', 35, 8, 92, TRUE, '优先体验高阶路线和达人任务。', 'Get early access to advanced routes and expert tasks.', TRUE),
    (5, '守护者', 'Guardian', 60, 15, 95, TRUE, '参与敏感秘境守护、审核和保护策略建议。', 'Join sensitive spot stewardship, review, and protection planning.', TRUE)
ON DUPLICATE KEY UPDATE
    name_zh = VALUES(name_zh),
    name_en = VALUES(name_en),
    is_active = VALUES(is_active);

INSERT INTO membership_plans (
    id,
    name_zh,
    name_en,
    duration_days,
    price_cents,
    benefits_zh,
    benefits_en,
    is_active
) VALUES
    (1, '月度探索会员', 'Monthly Explorer', 30, 1900, '解锁会员秘境区域、会员任务和路线建议。', 'Unlock member spot areas, member tasks, and route suggestions.', TRUE),
    (2, '年度守护会员', 'Annual Guardian', 365, 19900, '包含全年会员权益、保护级秘境申请和达人共创资格。', 'Includes annual benefits, protected spot requests, and expert co-creation access.', TRUE)
ON DUPLICATE KEY UPDATE
    name_zh = VALUES(name_zh),
    price_cents = VALUES(price_cents),
    is_active = VALUES(is_active);

INSERT IGNORE INTO user_memberships (
    id,
    user_id,
    plan_id,
    status,
    started_at,
    expires_at
) VALUES
    (1, 1, 1, 'active', DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_ADD(NOW(), INTERVAL 25 DAY));

INSERT IGNORE INTO checkin_records (
    id,
    user_id,
    spot_id,
    status,
    latitude,
    longitude,
    image_url,
    note,
    review_note
) VALUES
    (1, 1, 1, 'pending', '25.7431', '108.5060', 'https://example.com/checkins/jiabang-demo.jpg', '清晨到达，天气多云，有晨雾。', NULL),
    (2, 2, 2, 'rejected', '26.1000', '104.6300', NULL, '定位距离较远。', '未进入打卡范围。');

INSERT IGNORE INTO spot_images (id, spot_id, image_url, caption, sort_order, is_cover, is_active) VALUES
    (1, 1, '/media/spots/demo-jiabang.jpg', '加榜梯田晨雾示意图', 1, TRUE, TRUE),
    (2, 2, '/media/spots/demo-wumeng.jpg', '乌蒙山露营地示意图', 1, TRUE, TRUE);

INSERT IGNORE INTO travel_notes (id, user_id, spot_id, title, content, image_url, status, is_featured) VALUES
    (1, 1, 1, '加榜梯田清晨路线记录', '日出前抵达观景点，路面湿滑但视野很好，建议带防滑鞋。', '/media/travel-notes/demo-note.jpg', 'pending', FALSE);

INSERT IGNORE INTO user_comments (id, user_id, spot_id, content, image_url, status) VALUES
    (1, 1, 1, '适合摄影，但不要踩进梯田。', '/media/comments/demo-comment.jpg', 'approved'),
    (2, 2, 2, '想知道夜间是否安全露营？', NULL, 'pending');

INSERT IGNORE INTO lifestyle_recommendations (
    id,
    spot_id,
    category,
    name_zh,
    name_en,
    summary_zh,
    summary_en,
    city,
    county,
    address,
    contact,
    image_url,
    price_level,
    recommendation_level,
    is_active
) VALUES
    (1, 1, 'clothing', '山地速干防滑装备', 'Mountain Quick-Dry Gear', '适合梯田、瀑布和雨后徒步场景，建议搭配防滑鞋。', 'For terraces, waterfalls, and wet trails. Anti-slip shoes are recommended.', '黔东南州', '从江县', NULL, NULL, '/media/recommendations/demo-gear.jpg', 'mid', 4, TRUE),
    (2, 1, 'food', '从江酸汤鱼本地小馆', 'Congjiang Sour Soup Fish', '适合加榜梯田返程用餐，口味偏酸辣。', 'A sour and spicy local meal after visiting Jiabang terraces.', '黔东南州', '从江县', '从江县城区', NULL, '/media/recommendations/demo-food.jpg', 'mid', 4, TRUE),
    (3, 1, 'hotel', '梯田观景民宿', 'Terrace View Homestay', '靠近观景点，适合日出摄影用户。', 'Near the viewpoint and suitable for sunrise photographers.', '黔东南州', '从江县', NULL, NULL, NULL, 'mid', 3, TRUE),
    (4, 1, 'transport', '从江包车向导', 'Congjiang Local Driver Guide', '适合山路不熟的新用户，建议提前一天预约。', 'Useful for first-time visitors unfamiliar with mountain roads. Book one day ahead.', '黔东南州', '从江县', NULL, '提前预约', NULL, 'high', 4, TRUE);

CREATE TABLE IF NOT EXISTS archive_requirements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    title VARCHAR(160) NOT NULL,
    module VARCHAR(96) NOT NULL DEFAULT '待确认模块',
    category VARCHAR(32) NOT NULL,
    version VARCHAR(16) NOT NULL DEFAULT 'V1',
    priority VARCHAR(16) NOT NULL DEFAULT '中',
    status VARCHAR(32) NOT NULL DEFAULT '待确认',
    owner VARCHAR(64) NULL,
    requester VARCHAR(96) NULL,
    requester_user_id INT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
    source_date DATE NOT NULL,
    source_text TEXT NOT NULL,
    description TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    planned_release DATE NULL,
    created_by_admin_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_archive_requirement_code (code),
    INDEX ix_archive_requirement_source_date (source_date),
    INDEX ix_archive_requirement_category (category),
    INDEX ix_archive_requirement_status (status),
    CONSTRAINT fk_archive_requirement_user FOREIGN KEY (requester_user_id) REFERENCES mini_program_users(id),
    CONSTRAINT fk_archive_requirement_admin FOREIGN KEY (created_by_admin_id) REFERENCES admin_users(id)
);

CREATE TABLE IF NOT EXISTS archive_development_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    requirement_id INT NOT NULL,
    sub_requirement_code VARCHAR(40) NOT NULL,
    round_number INT NOT NULL DEFAULT 0,
    title VARCHAR(200) NOT NULL,
    task_type VARCHAR(32) NOT NULL DEFAULT '综合开发',
    owner VARCHAR(64) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    status VARCHAR(32) NOT NULL DEFAULT '待开始',
    progress INT NOT NULL DEFAULT 0,
    self_test_result VARCHAR(16) NULL,
    self_test_detail TEXT NULL,
    acceptance_result VARCHAR(16) NULL,
    acceptance_detail TEXT NULL,
    acceptance_notified_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_archive_task_round_title (requirement_id, sub_requirement_code, title),
    INDEX ix_archive_task_code (code),
    INDEX ix_archive_task_requirement (requirement_id),
    INDEX ix_archive_task_sub_requirement (sub_requirement_code),
    INDEX ix_archive_task_status (status),
    CONSTRAINT fk_archive_task_requirement FOREIGN KEY (requirement_id) REFERENCES archive_requirements(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS archive_chat_imports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'wechat_personal',
    contact VARCHAR(96) NULL,
    raw_text TEXT NOT NULL,
    message_count INT NOT NULL DEFAULT 0,
    recognized_count INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'processed',
    imported_by_admin_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_archive_import_admin (imported_by_admin_id),
    CONSTRAINT fk_archive_import_admin FOREIGN KEY (imported_by_admin_id) REFERENCES admin_users(id)
);

CREATE TABLE IF NOT EXISTS archive_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requirement_id INT NOT NULL,
    task_id INT NULL,
    event_type VARCHAR(48) NOT NULL,
    actor_type VARCHAR(32) NOT NULL,
    actor_name VARCHAR(96) NULL,
    detail TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_archive_event_requirement (requirement_id),
    INDEX ix_archive_event_task (task_id),
    INDEX ix_archive_event_type (event_type),
    CONSTRAINT fk_archive_event_requirement FOREIGN KEY (requirement_id) REFERENCES archive_requirements(id) ON DELETE CASCADE,
    CONSTRAINT fk_archive_event_task FOREIGN KEY (task_id) REFERENCES archive_development_tasks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS archive_internal_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_type VARCHAR(32) NOT NULL,
    title VARCHAR(160) NOT NULL,
    content TEXT NOT NULL,
    related_requirement_id INT NULL,
    target_role VARCHAR(32) NOT NULL DEFAULT 'admin',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_archive_message_type (message_type),
    INDEX ix_archive_message_requirement (related_requirement_id),
    INDEX ix_archive_message_read (is_read),
    CONSTRAINT fk_archive_message_requirement FOREIGN KEY (related_requirement_id) REFERENCES archive_requirements(id) ON DELETE CASCADE
);
