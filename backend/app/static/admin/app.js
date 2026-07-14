const API = "/api/v1";

const state = {
  token: localStorage.getItem("gz_admin_token") || "",
  lang: localStorage.getItem("gz_admin_lang") || "zh-CN",
  admin: null,
  tags: [],
  spots: [],
  users: [],
  passSettings: [],
  membershipPlans: [],
  membershipRecords: [],
  checkins: [],
  travelNotes: [],
  comments: [],
  recommendations: [],
  integrations: [],
  currentSpotImages: [],
  currentSpotCheckins: [],
  currentSpotComments: [],
  currentSpotChildPoints: [],
  pagination: {},
  editingSpotId: null,
  editingTagId: null,
  editingUserId: null,
  editingPassSettingId: null,
  editingMembershipPlanId: null,
  editingCheckinId: null,
  editingTravelNoteId: null,
  editingCommentId: null,
  editingRecommendationId: null,
  checkinFilters: {},
  assistantPending: { checkins: 0, travel_notes: 0, comments: 0, media: 0 },
  assistantMode: "guide",
  assistantMessages: [],
  assistantThinking: false,
};

const PAGE_SIZE = 10;
const MAX_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024;
const MAX_VIDEO_UPLOAD_BYTES = 8 * 1024 * 1024;
const PAGE_SIZE_BY_KEY = {
  tags: 100,
  passSettings: 100,
};

const DEFAULT_SECTION = "spotsSection";
const SECTION_IDS = new Set([
  "spotsSection",
  "tagsSection",
  "usersSection",
  "passSettingsSection",
  "membershipsSection",
  "checkinsSection",
  "communitySection",
  "recommendationsSection",
  "integrationsSection",
]);

const I18N = {
  "贵州秘境管理后台": "Guizhou Hidden Gems Admin",
  "秘境点位、双语内容、标签和审核状态维护": "Manage hidden gem locations, bilingual content, tags, and review states",
  "用户名": "Username",
  "密码": "Password",
  "登录": "Sign In",
  "贵州秘境": "Guizhou Gems",
  "秘境管理": "Hidden Gems",
  "标签管理": "Tags",
  "用户管理": "Users",
  "通关设置": "Pass Settings",
  "会员管理": "Memberships",
  "打卡审核": "Check-ins",
  "游记留言": "Notes & Comments",
  "衣食住行": "Lifestyle",
  "接口管理": "Integrations",
  "退出登录": "Sign Out",
  "内容运营台": "Content Operations",
  "刷新": "Refresh",
  "账号设置": "Account Settings",
  "新增秘境": "New Spot",
  "秘境总数": "Total Spots",
  "已审核": "Approved",
  "标签数": "Tags",
  "保护坐标": "Protected",
  "注册用户": "Users",
  "通关等级": "Pass Levels",
  "会员套餐": "Plans",
  "待审打卡": "Pending Check-ins",
  "待审内容": "Pending Content",
  "推荐条目": "Recommendations",
  "维护中英文内容、坐标、标签、可见级别和审核状态。": "Maintain bilingual content, coordinates, tags, visibility levels, and review states.",
  "标签会用于小程序首页地图筛选和秘境推荐。": "Tags are used for mini program map filtering and spot recommendations.",
  "管理小程序注册用户、会员状态、探秘积分、贡献数和环保信用。": "Manage registered users, membership status, explore points, contribution count, and eco credit.",
  "配置 L0-L5 探索等级的通关条件、会员要求和解锁权益。": "Configure L0-L5 pass requirements, membership rules, and unlock benefits.",
  "配置探索等级的通关条件、会员要求、地图标识颜色和解锁权益。": "Configure pass requirements, membership rules, map marker colors, and unlock benefits.",
  "配置探索等级的探秘积分、打卡、贡献、环保信用、会员要求和解锁权益。": "Configure explore points, check-ins, contributions, eco credit, membership, and unlock benefits.",
  "配置景点解锁积分、每次审核通过打卡可获得的积分、会员要求和解锁权益。": "Configure spot unlock points, points awarded for each approved check-in, membership rules, and unlock benefits.",
  "积分规则": "Points Rules",
  "新增等级": "New Level",
  "标识颜色": "Marker Color",
  "请先配置通关等级": "Configure a pass level first",
  "新增会员套餐": "New Membership Plan",
  "升级积分": "Upgrade Points",
  "删除后数据不可恢复，确认删除吗？": "Deleted data cannot be recovered. Continue?",
  "删除失败": "Delete failed",
  "维护会员套餐、价格、周期、权益，并查看用户会员记录。": "Maintain membership plans, prices, periods, benefits, and user membership records.",
  "审核用户 GPS + 图片打卡记录，通过后同步增加用户打卡数。": "Review GPS and image check-ins; approvals increase user check-in counts.",
  "审核用户游记和留言，支持推荐精选游记或隐藏违规内容。": "Review user notes and comments, feature good notes, or hide inappropriate content.",
  "维护装备、美食、住宿和交通推荐，为秘境探索提供配套信息。": "Maintain gear, food, lodging, and transport recommendations.",
  "统一管理天气接口、大模型接口、河流洪水接口配置。敏感字段留空表示不修改。": "Manage weather, AI model, and flood API settings. Leave sensitive fields empty to keep existing values.",
  "天气接口管理": "Weather API",
  "大模型接口管理": "AI Model API",
  "河流洪水接口管理": "Flood API",
  "小程序数据时间管理": "Mini Program Data Hours",
  "对象存储管理": "Object Storage",
  "测试连接": "Test Connection",
  "AI 小助手": "AI Assistant",
  "操作指南": "Operation Guide",
  "生成中英文简介": "Generate Bilingual Summary",
  "获取坐标方法": "Get Coordinates",
  "内容初审建议": "Content Review Advice",
  "发送": "Send",
  "正在测试 OSS 连接...": "Testing OSS connection...",
  "OSS 连接失败": "OSS connection failed",
  "OSS 连接成功": "OSS connection successful",
  "配置和风天气实时天气、气象预警接口。敏感字段列表中会脱敏显示。": "Configure QWeather live weather and warning APIs. Sensitive values are masked in lists.",
  "配置智能小助手后续使用的大模型服务。": "Configure model service used by the AI assistant.",
  "配置河流、水文、洪水预警数据接口。未配置时以人工提示和气象预警为兜底。": "Configure river, hydrology, and flood warning APIs. Weather alerts are used as fallback when unconfigured.",
  "设置小程序后台数据的开放时间。启用后，超出时间范围的小程序请求会被拒绝并显示提示。": "Set the time window for mini program data access. When enabled, requests outside the window are rejected with a notice.",
  "配置图片和视频的存储位置。AccessKey 仅从服务器环境变量读取，不会保存到后台数据库。": "Configure media storage. Access keys are read only from server environment variables and are not saved in the admin database.",
  "新增标签": "New Tag",
  "新增用户": "New User",
  "新增游记": "New Note",
  "新增留言": "New Comment",
  "新增推荐": "New Recommendation",
  "名称": "Name",
  "地区": "Area",
  "坐标": "Coordinates",
  "标签": "Tags",
  "可见级别": "Visibility",
  "秘境等级": "Spot Level",
  "解锁积分": "Unlock Points",
  "审核": "Review",
  "打卡": "Check-ins",
  "贡献": "Contributions",
  "状态": "Status",
  "操作": "Actions",
  "中文": "Chinese",
  "英文": "English",
  "图标": "Icon",
  "排序": "Sort",
  "用户": "User",
  "头像": "Avatar",
  "语言": "Language",
  "等级": "Level",
  "数据": "Stats",
  "权限": "Permissions",
  "会员": "Member",
  "条件": "Rules",
  "解锁权益": "Benefits",
  "套餐": "Plan",
  "周期": "Period",
  "价格": "Price",
  "权益": "Benefits",
  "开始": "Start",
  "到期": "Expires",
  "定位": "Location",
  "说明": "Note",
  "游记": "Travel Note",
  "图片": "Image",
  "精选": "Featured",
  "取消精选": "Unfeature",
  "设为精选": "Feature",
  "留言": "Comment",
  "留言图片": "Comment Image",
  "分类": "Category",
  "推荐": "Level",
  "秘境": "Spot",
  "中文名称": "Chinese Name",
  "英文名称": "English Name",
  "中文简介": "Chinese Summary",
  "英文简介": "English Summary",
  "中文介绍": "Chinese Description",
  "英文介绍": "English Description",
  "市州": "City/Prefecture",
  "区县": "County",
  "纬度": "Latitude",
  "经度": "Longitude",
  "公开": "Public",
  "保护": "Protected",
  "守护者": "Guardian",
  "草稿": "Draft",
  "待审核": "Pending",
  "已通过": "Approved",
  "已拒绝": "Rejected",
  "推荐等级": "Recommendation Level",
  "L1 入门": "L1 Beginner",
  "L2 轻探秘": "L2 Light",
  "L3 深度": "L3 Deep",
  "L4 高阶": "L4 Advanced",
  "L5 守护者": "L5 Guardian",
  "探秘积分": "Explore Points",
  "打卡半径米": "Check-in Radius (m)",
  "启用": "Active",
  "秘境图片": "Spot Images",
  "秘境图片/视频": "Spot Images/Videos",
  "子景点坐标": "Sub-spot Coordinates",
  "为同一秘境维护多个子景点坐标、备注说明，并选择是否获取天气。": "Maintain multiple sub-spot coordinates, notes, and weather-fetch settings for one spot.",
  "点位名称": "Point Name",
  "备注说明": "Note",
  "获取天气": "Fetch Weather",
  "新增子景点": "Add Sub-spot",
  "暂无子景点坐标": "No sub-spot coordinates",
  "请先保存秘境，再新增子景点": "Save the spot before adding sub-spots",
  "子景点已新增": "Sub-spot added",
  "子景点已删除": "Sub-spot deleted",
  "天气": "Weather",
  "不获取天气": "No weather",
  "支持 JPG、PNG、WebP、GIF，上传后可设为封面。": "Supports JPG, PNG, WebP, and GIF. Uploaded images can be set as cover.",
  "图片支持 JPG、PNG、WebP、GIF，最大 2MB；视频支持 MP4、MOV、M4V，最大 8MB。仅图片可设为封面。": "Images: JPG, PNG, WebP, GIF, max 2MB. Videos: MP4, MOV, M4V, max 8MB. Only images can be set as cover.",
  "上传图片": "Upload Image",
  "上传图片/视频": "Upload Image/Video",
  "图片说明": "Caption",
  "媒体说明": "Media Caption",
  "上传媒体": "Upload Media",
  "媒体": "Media",
  "视频": "Video",
  "设为封面": "Set as Cover",
  "取消": "Cancel",
  "保存": "Save",
  "中文标签": "Chinese Tag",
  "英文标签": "English Tag",
  "昵称": "Nickname",
  "手机号": "Phone",
  "微信头像 URL": "WeChat Avatar URL",
  "上传头像": "Upload Avatar",
  "允许上传图片": "Allow Image Upload",
  "允许上传视频": "Allow Video Upload",
  "允许留言游记": "Allow Notes/Comments",
  "允许打卡通关": "Allow Check-in/Pass",
  "图片权限": "Image",
  "视频权限": "Video",
  "留言权限": "Comment",
  "打卡权限": "Check-in",
  "中文权益": "Chinese Benefits",
  "英文权益": "English Benefits",
  "所需打卡": "Required Check-ins",
  "所需探秘积分": "Required Explore Points",
  "所需贡献": "Required Contributions",
  "环保信用": "Eco Credit",
  "所属秘境": "Linked Spot",
  "需要会员": "Requires Membership",
  "周期天数": "Duration Days",
  "价格分": "Price Cents",
  "审核状态": "Review Status",
  "通过": "Approve",
  "拒绝": "Reject",
  "审核备注": "Review Note",
  "用户 ID": "User ID",
  "秘境 ID": "Spot ID",
  "标题": "Title",
  "内容": "Content",
  "图片 URL": "Image URL",
  "隐藏": "Hide",
  "留言内容": "Comment",
  "衣": "Clothing",
  "食": "Food",
  "住": "Lodging",
  "行": "Transport",
  "地址": "Address",
  "联系方式": "Contact",
  "价格级别": "Price Level",
  "低": "Low",
  "中": "Mid",
  "高": "High",
  "编辑": "Edit",
  "停用": "Disable",
  "删除": "Delete",
  "普通": "Regular",
  "有效": "Active",
  "非有效": "Inactive",
  "允许": "Allowed",
  "不允许": "Denied",
  "需要": "Required",
  "不需要": "Not Required",
  "已隐藏": "Hidden",
  "未上传": "Not Uploaded",
  "未绑定手机": "No phone",
  "未设置": "Not Set",
  "暂无图片": "No Images",
  "暂无媒体": "No Media",
  "未填写说明": "No Caption",
  "封面": "Cover",
  "上一页": "Previous",
  "下一页": "Next",
  "编辑秘境": "Edit Spot",
  "编辑标签": "Edit Tag",
  "编辑用户": "Edit User",
  "编辑通关设置": "Edit Pass Setting",
  "新增通关等级": "New Pass Level",
  "编辑会员套餐": "Edit Membership Plan",
  "编辑游记": "Edit Note",
  "编辑留言": "Edit Comment",
  "编辑推荐": "Edit Recommendation",
  "推荐已保存": "Recommendation saved",
  "游记已保存": "Note saved",
  "留言已保存": "Comment saved",
  "用户已保存": "User saved",
  "保存失败": "Save failed",
  "秘境已保存": "Spot saved",
  "标签已保存": "Tag saved",
  "审核状态已更新": "Review status updated",
  "秘境已停用": "Spot disabled",
  "标签已停用": "Tag disabled",
  "用户状态已更新": "User status updated",
  "用户已删除": "User deleted",
  "打卡审核已更新": "Check-in review updated",
  "游记状态已更新": "Note status updated",
  "游记精选状态已更新": "Featured status updated",
  "游记已删除": "Note deleted",
  "留言状态已更新": "Comment status updated",
  "留言已删除": "Comment deleted",
  "推荐已删除": "Recommendation deleted",
  "封面已更新": "Cover updated",
  "图片已停用": "Image disabled",
  "媒体已删除": "Media deleted",
  "图片已上传": "Image uploaded",
  "请选择图片": "Please choose an image",
  "请先保存秘境，再上传图片": "Save the spot before uploading images",
  "媒体已上传": "Media uploaded",
  "已选择": "Selected",
  "未选择文件": "No file selected",
  "文件类型": "Type",
  "文件大小": "Size",
  "文件类型不支持": "Unsupported file type",
  "移除已选文件": "Remove Selected File",
  "上传进度": "Upload Progress",
  "正在上传": "Uploading",
  "上传完成": "Upload complete",
  "正在删除OSS文件": "Deleting OSS file",
  "OSS文件已删除": "OSS file deleted",
  "请选择图片或视频": "Please choose an image or video",
  "请先保存秘境，再上传媒体": "Save the spot before uploading media",
  "图片大小不能超过 2MB": "Image must not exceed 2MB",
  "视频大小不能超过 8MB": "Video must not exceed 8MB",
  "视频不能设为封面": "Video cannot be set as cover",
  "通关设置已保存": "Pass setting saved",
  "通关等级不可重复": "Pass level must be unique",
  "每次打卡积分": "Points Per Check-in",
  "会员套餐已保存": "Membership plan saved",
  "打卡审核已保存": "Check-in review saved",
  "已刷新": "Refreshed",
  "接口配置已保存": "Integration settings saved",
  "已配置": "Configured",
  "未配置": "Not configured",
  "留空表示不修改": "Leave blank to keep unchanged",
  "当前密码": "Current Password",
  "新密码": "New Password",
  "只修改用户名时可不填写密码；修改密码时必须填写当前密码和新密码。": "Leave password fields empty when only changing username. Current and new passwords are required when changing password.",
  "账号设置已保存": "Account settings saved",
  "两次密码不能相同": "New password must be different",
  "请输入当前密码": "Enter current password",
};

const I18N_REVERSE = Object.fromEntries(Object.entries(I18N).map(([zh, en]) => [en, zh]));

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function t(text) {
  return state.lang === "en-US" ? I18N[text] || text : text;
}

function applyLanguage(root = document.body) {
  document.documentElement.lang = state.lang;
  document.title = t("贵州秘境管理后台");
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach((node) => {
    const trimmed = node.nodeValue.trim();
    if (!trimmed) return;
    const leading = node.nodeValue.match(/^\s*/)[0];
    const trailing = node.nodeValue.match(/\s*$/)[0];
    const original = I18N_REVERSE[trimmed] || trimmed;
    const translated = state.lang === "en-US" ? I18N[original] || original : original;
    node.nodeValue = `${leading}${translated}${trailing}`;
  });
  const toggleText = state.lang === "en-US" ? "中文" : "English";
  ["#langToggleBtn", "#loginLangToggleBtn"].forEach((selector) => {
    const button = $(selector);
    if (button) button.textContent = toggleText;
  });
}

function setLanguage(lang) {
  state.lang = lang;
  localStorage.setItem("gz_admin_lang", lang);
  applyLanguage();
  renderAll();
}

function renderAll() {
  renderMetrics();
  renderTags();
  renderSpots();
  renderUsers();
  renderPassSettings();
  renderMemberships();
  renderCheckins();
  renderCommunity();
  renderRecommendations();
  renderIntegrations();
  renderChildPoints();
  applyLanguage();
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = t(message);
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  const duration = String(message).length > 80 ? 10000 : 3200;
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), duration);
}

function confirmDeletion() {
  return window.confirm(t("删除后数据不可恢复，确认删除吗？"));
}

function renderAdminInfo() {
  $("#adminInfo").textContent = state.admin ? `${state.admin.username} / ${state.admin.role}` : "-";
}

function getInitialSectionId() {
  const hashSection = window.location.hash.replace("#", "");
  const savedSection = localStorage.getItem("gz_admin_section") || "";
  if (SECTION_IDS.has(hashSection)) return hashSection;
  if (SECTION_IDS.has(savedSection)) return savedSection;
  return DEFAULT_SECTION;
}

function setActiveSection(sectionId, options = {}) {
  const nextSectionId = SECTION_IDS.has(sectionId) ? sectionId : DEFAULT_SECTION;
  $$(".nav-btn").forEach((button) => {
    button.classList.toggle("active", button.dataset.section === nextSectionId);
  });
  $$(".panel-section").forEach((section) => {
    section.classList.toggle("hidden", section.id !== nextSectionId);
  });
  localStorage.setItem("gz_admin_section", nextSectionId);
  if (!options.skipHash && window.location.hash !== `#${nextSectionId}`) {
    history.replaceState(null, "", `#${nextSectionId}`);
  }
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 204) {
    return null;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    if (detail && typeof detail === "object") {
      const messages = [detail.message, detail.weather_error, detail.alerts_error].filter(Boolean);
      throw new Error(messages.join("；") || `请求失败 ${response.status}`);
    }
    throw new Error(detail || `请求失败 ${response.status}`);
  }
  return data;
}

function setAuthenticated(isAuthenticated) {
  $("#loginView").classList.toggle("hidden", isAuthenticated);
  $("#appView").classList.toggle("hidden", !isAuthenticated);
  $("#adminAssistantToggle")?.classList.toggle("hidden", !isAuthenticated);
}

function statusPill(status) {
  const labels = {
    draft: t("草稿"),
    pending: t("待审核"),
    approved: t("已通过"),
    rejected: t("已拒绝"),
    hidden: t("已隐藏"),
  };
  const tone = status === "approved" ? "" : status === "rejected" ? "danger" : "warning";
  return `<span class="pill ${tone}">${labels[status] || status}</span>`;
}

function visibilityText(level) {
  return {
    public: t("公开"),
    member: t("会员"),
    protected: t("保护"),
    secret: t("守护者"),
  }[level] || level;
}

function spotLevelText(level) {
  const setting = state.passSettings.find((item) => Number(item.level) === Number(level));
  if (!setting) return `L${level}`;
  const name = state.lang === "en-US" ? setting.name_en : setting.name_zh;
  return `L${setting.level} ${name}`;
}

function activePill(active) {
  return active ? `<span class="pill">${t("启用")}</span>` : `<span class="pill danger">${t("停用")}</span>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMetrics() {
  const visibleUsers = state.users.filter((user) => user.is_active !== false);
  $("#spotCount").textContent = state.pagination.spots?.total ?? state.spots.length;
  $("#approvedCount").textContent = state.spots.filter((spot) => spot.review_status === "approved").length;
  $("#tagCount").textContent = state.pagination.tags?.total ?? state.tags.length;
  $("#protectedCount").textContent = state.spots.filter((spot) => spot.visibility_level !== "public").length;
  $("#userCount").textContent = state.pagination.users?.total ?? visibleUsers.length;
  $("#passLevelCount").textContent = state.pagination.passSettings?.total ?? state.passSettings.length;
  $("#membershipPlanCount").textContent = state.pagination.membershipPlans?.total ?? state.membershipPlans.length;
  $("#pendingCheckinCount").textContent = state.checkins.filter((checkin) => checkin.status === "pending").length;
  $("#pendingCommunityCount").textContent =
    state.travelNotes.filter((note) => note.status === "pending").length +
    state.comments.filter((comment) => comment.status === "pending").length;
  $("#recommendationCount").textContent = state.pagination.recommendations?.total ?? state.recommendations.length;
  renderAssistantPending();
}

function renderAssistantPending() {
  const pending = state.assistantPending || {};
  const total = Number(pending.checkins || 0) + Number(pending.travel_notes || 0) + Number(pending.comments || 0) + Number(pending.media || 0);
  const badge = $("#assistantPendingBadge");
  if (badge) {
    badge.textContent = total > 99 ? "99+" : String(total);
    badge.classList.toggle("hidden", total === 0);
  }
  const summary = $("#assistantPendingSummary");
  if (summary) {
    const items = [
      ["checkinsSection", "打卡", pending.checkins || 0],
      ["communitySection", "游记", pending.travel_notes || 0],
      ["communitySection", "留言", pending.comments || 0],
      ["communitySection", "图片/视频", pending.media || 0],
    ];
    summary.innerHTML = items
      .map(([section, label, count]) => `<button type="button" class="assistant-pending-link" data-assistant-pending-section="${section}">${label}待审 ${count}</button>`)
      .join("");
  }
}

function renderAssistantMessages() {
  const container = $("#assistantMessages");
  if (!container) return;
  const messages = [...state.assistantMessages];
  if (state.assistantThinking) messages.push({ role: "assistant thinking", content: "正在思考中..." });
  container.innerHTML = messages.length
    ? messages.map((item) => `<div class="assistant-message ${item.role}"><strong>${item.role === "user" ? "管理员" : "AI 小助手"}</strong>\n${escapeHtml(item.content)}</div>`).join("")
    : '<div class="muted">可询问菜单操作、字段配置、双语简介、坐标采集，或使用 AI 初审辅助审核。</div>';
  container.scrollTop = container.scrollHeight;
}

async function sendAssistantMessage(message, mode = state.assistantMode) {
  const content = String(message || "").trim();
  if (!content) return;
  state.assistantMessages.push({ role: "user", content });
  renderAssistantMessages();
  const button = $("#assistantSendBtn");
  button.disabled = true;
  state.assistantThinking = true;
  renderAssistantMessages();
  try {
    const result = await request("/admin/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message: content, mode }),
    });
    state.assistantPending = result.pending || state.assistantPending;
    state.assistantMessages.push({ role: "assistant", content: result.answer });
    renderAssistantPending();
    renderAssistantMessages();
  } catch (error) {
    state.assistantMessages.push({ role: "assistant", content: `请求失败：${error.message}` });
    renderAssistantMessages();
  } finally {
    state.assistantThinking = false;
    button.disabled = false;
    renderAssistantMessages();
  }
}

async function reviewWithAssistant(contentType, contentId) {
  const dialog = $("#adminAssistantDialog");
  state.assistantMode = "review";
  if (!dialog.open) dialog.showModal();
  state.assistantMessages.push({ role: "user", content: `请初审${contentType === "travel_note" ? "游记" : "留言"} #${contentId}` });
  state.assistantThinking = true;
  renderAssistantMessages();
  try {
    const result = await request("/admin/assistant/review", {
      method: "POST",
      body: JSON.stringify({ content_type: contentType, content_id: Number(contentId) }),
    });
    state.assistantMessages.push({ role: "assistant", content: result.answer });
  } catch (error) {
    state.assistantMessages.push({ role: "assistant", content: `初审请求失败：${error.message}` });
  } finally {
    state.assistantThinking = false;
  }
  renderAssistantMessages();
}

function memberPill(isMember) {
  return isMember ? `<span class="pill">${t("会员")}</span>` : `<span class="pill warning">${t("普通")}</span>`;
}

function imageCell(url, alt = "图片") {
  if (!url) return `<span class="muted">${t("未上传")}</span>`;
  const cleanUrl = String(url).split("?")[0].toLowerCase();
  const escapedUrl = escapeHtml(url);
  if (cleanUrl.endsWith(".mp4") || cleanUrl.endsWith(".mov") || cleanUrl.endsWith(".m4v")) {
    return `<video class="image-thumb" src="${escapedUrl}" controls preload="metadata"></video>`;
  }
  return `<img class="image-thumb" src="${escapedUrl}" alt="${escapeHtml(alt)}" />`;
}

function userAvatarCell(url, nickname = "用户") {
  const initial = escapeHtml(String(nickname).slice(0, 1) || "用");
  if (!url) return `<span class="default-avatar" aria-label="${escapeHtml(nickname)}">${initial}</span>`;
  return `
    <span class="avatar-cell">
      <img class="image-thumb" src="${escapeHtml(url)}" alt="${escapeHtml(nickname)}" onerror="this.hidden=true;this.nextElementSibling.hidden=false;" />
      <span class="default-avatar" hidden aria-label="${escapeHtml(nickname)}">${initial}</span>
    </span>
  `;
}

function displayMediaUrl(itemOrUrl) {
  if (!itemOrUrl) return "";
  if (typeof itemOrUrl === "object") {
    return itemOrUrl.display_url || itemOrUrl.image_url || "";
  }
  return itemOrUrl;
}

function mediaPreviewHtml(url, alt = "图片") {
  if (!url) return `<span class="muted">${t("未上传")}</span>`;
  const cleanUrl = String(url).split("?")[0].toLowerCase();
  const escapedUrl = escapeHtml(url);
  const caption = escapeHtml(alt);
  if (cleanUrl.endsWith(".mp4") || cleanUrl.endsWith(".mov") || cleanUrl.endsWith(".m4v")) {
    return `
      <article class="image-item form-media-card">
        <video class="image-thumb media-preview" src="${escapedUrl}" controls preload="metadata"></video>
        <div class="cell-title">
          <strong>${caption}</strong>
          <span class="muted">${t("视频")}</span>
        </div>
        <div class="row-actions">
          <button type="button" class="small-btn danger" data-delete-form-media="true">${t("删除")}</button>
        </div>
      </article>
    `;
  }
  return `
    <article class="image-item form-media-card">
      <a class="media-link" href="${escapedUrl}" target="_blank" rel="noopener">
        <img class="image-thumb media-preview" src="${escapedUrl}" alt="${caption}" />
      </a>
      <div class="cell-title">
        <strong>${caption}</strong>
        <span class="muted">${t("图片")}</span>
      </div>
      <div class="row-actions">
        <button type="button" class="small-btn danger" data-delete-form-media="true">${t("删除")}</button>
      </div>
    </article>
  `;
}

function renderFormMediaPreview(formSelector, previewSelector, alt = "图片") {
  const form = $(formSelector);
  const preview = $(previewSelector);
  if (!form || !preview) return;
  preview.innerHTML = mediaPreviewHtml(form.dataset.mediaDisplayUrl || form.elements.image_url.value, alt);
}

function renderTags() {
  $("#tagsTable").innerHTML = state.tags
    .map(
      (tag) => `
        <tr>
          <td>${escapeHtml(tag.name_zh)}</td>
          <td>${escapeHtml(tag.name_en)}</td>
          <td>${escapeHtml(tag.icon || "-")}</td>
          <td>${tag.sort_order}</td>
          <td>${activePill(tag.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-tag="${tag.id}">编辑</button>
              <button class="small-btn danger" data-delete-tag="${tag.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("tagsTable", "tags");
}

function renderSpots() {
  $("#spotsTable").innerHTML = state.spots
    .map((spot) => {
      const tags = spot.tags.length
        ? spot.tags.map((tag) => `<span class="pill">${escapeHtml(tag.name)}</span>`).join("")
        : `<span class="muted">${t("未设置")}</span>`;
      return `
        <tr>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(spot.name_zh)}</strong>
              <span class="muted">${escapeHtml(spot.name_en)}</span>
            </div>
          </td>
          <td>${escapeHtml(spot.city)} / ${escapeHtml(spot.county)}</td>
          <td>${Number(spot.latitude).toFixed(4)}, ${Number(spot.longitude).toFixed(4)}</td>
          <td><div class="pill-row">${tags}</div></td>
          <td>${visibilityText(spot.visibility_level)}</td>
          <td>${spotLevelText(spot.recommendation_level)}</td>
          <td>${spot.required_explore_points || 0}</td>
          <td>${statusPill(spot.review_status)}</td>
          <td>${activePill(spot.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-spot="${spot.id}">编辑</button>
              <button class="small-btn" data-review-spot="${spot.id}" data-review-status="approved">通过</button>
              <button class="small-btn" data-review-spot="${spot.id}" data-review-status="rejected">拒绝</button>
              <button class="small-btn danger" data-delete-spot="${spot.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
  renderPagination("spotsTable", "spots");
}

function renderUsers() {
  $("#usersTable").innerHTML = state.users
    .filter((user) => user.is_active !== false)
    .map(
      (user) => `
        <tr>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(user.nickname)}</strong>
              <span class="muted">${escapeHtml(user.phone || t("未绑定手机"))}</span>
            </div>
          </td>
          <td>${userAvatarCell(user.avatar_url, user.nickname)}</td>
          <td>${escapeHtml(user.openid)}</td>
          <td>${escapeHtml(user.language)}</td>
          <td>
            <div class="cell-title">
              <span>${t("打卡")} ${user.checkin_count} / ${t("贡献")} ${user.contribution_count}</span>
              <span class="muted">${t("探秘积分")} ${user.explore_points || 0}</span>
              <span class="muted">${t("环保信用")} ${user.eco_credit}</span>
            </div>
          </td>
          <td>
            <div class="cell-title">
              <span>${t("图片权限")}：${user.can_upload_image ? t("允许") : t("不允许")}</span>
              <span>${t("视频权限")}：${user.can_upload_video ? t("允许") : t("不允许")}</span>
              <span>${t("留言权限")}：${user.can_comment ? t("允许") : t("不允许")}</span>
              <span>${t("打卡权限")}：${user.can_checkin ? t("允许") : t("不允许")}</span>
            </div>
          </td>
          <td>${memberPill(user.is_member)}</td>
          <td>${activePill(user.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-user="${user.id}">${t("编辑")}</button>
              <button class="small-btn danger" data-toggle-user="${user.id}">${user.is_active ? t("停用") : t("启用")}</button>
              <button class="small-btn danger" data-delete-user="${user.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("usersTable", "users");
}

function renderPassSettings() {
  $("#passSettingsTable").innerHTML = state.passSettings
    .map(
      (setting) => `
        <tr>
          <td>L${setting.level}</td>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(setting.name_zh)}</strong>
              <span class="muted">${escapeHtml(setting.name_en)}</span>
            </div>
          </td>
          <td>
            <div class="cell-title">
              <span>${t("探秘积分")} ${setting.required_explore_points || 0}</span>
              <span class="muted">${t("每次打卡积分")} ${setting.checkin_points || 0}</span>
            </div>
          </td>
          <td>
            <span class="color-chip">
              <span class="color-swatch" style="background:${escapeHtml(setting.marker_color || "#2f6b4f")}"></span>
              ${escapeHtml(setting.marker_color || "#2f6b4f")}
            </span>
          </td>
          <td>${setting.requires_membership ? `<span class="pill warning">${t("需要")}</span>` : `<span class="pill">${t("不需要")}</span>`}</td>
          <td>
            <div class="cell-title">
              <span>${escapeHtml(setting.unlock_benefit_zh)}</span>
              <span class="muted">${escapeHtml(setting.unlock_benefit_en)}</span>
            </div>
          </td>
          <td>${activePill(setting.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-pass="${setting.id}">${t("编辑")}</button>
              <button class="small-btn danger" data-delete-pass="${setting.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("passSettingsTable", "passSettings");
}

function renderMemberships() {
  $("#membershipPlansTable").innerHTML = state.membershipPlans
    .map(
      (plan) => `
        <tr>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(plan.name_zh)}</strong>
              <span class="muted">${escapeHtml(plan.name_en)}</span>
            </div>
          </td>
          <td>${plan.duration_days} ${state.lang === "en-US" ? "days" : "天"}</td>
          <td>${plan.required_explore_points || 0}</td>
          <td>¥${(plan.price_cents / 100).toFixed(2)}</td>
          <td>
            <div class="cell-title">
              <span>${escapeHtml(plan.benefits_zh)}</span>
              <span class="muted">${escapeHtml(plan.benefits_en)}</span>
            </div>
          </td>
          <td>${activePill(plan.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-plan="${plan.id}">${t("编辑")}</button>
              <button class="small-btn danger" data-delete-plan="${plan.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("membershipPlansTable", "membershipPlans");

  $("#membershipRecordsTable").innerHTML = state.membershipRecords
    .map(
      (record) => `
        <tr>
          <td>${escapeHtml(record.nickname)}</td>
          <td>${escapeHtml(record.plan_name_zh)}</td>
          <td>${record.status === "active" ? `<span class="pill">${t("有效")}</span>` : `<span class="pill warning">${t("非有效")}</span>`}</td>
          <td>${escapeHtml(record.started_at || "-")}</td>
          <td>${escapeHtml(record.expires_at || "-")}</td>
        </tr>
      `,
    )
    .join("");
  renderPagination("membershipRecordsTable", "membershipRecords");
}

function renderCheckins() {
  $("#checkinsTable").innerHTML = state.checkins
    .map(
      (checkin) => `
        <tr>
          <td>${escapeHtml(checkin.nickname)}</td>
          <td>${escapeHtml(checkin.spot_name_zh)}</td>
          <td>${checkin.checkin_distance_meters == null ? "-" : `${checkin.checkin_distance_meters}m`}</td>
          <td>${escapeHtml(checkin.created_at ? new Date(checkin.created_at).toLocaleString() : "-")}</td>
          <td>${statusPill(checkin.status)}</td>
        </tr>
      `,
    )
    .join("");
  renderPagination("checkinsTable", "checkins");
}

function categoryText(category) {
  return {
    clothing: t("衣"),
    food: t("食"),
    hotel: t("住"),
    transport: t("行"),
  }[category] || category;
}

function renderCommunity() {
  $("#travelNotesTable").innerHTML = state.travelNotes
    .map(
      (note) => `
        <tr>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(note.title)}</strong>
              <span class="muted">${escapeHtml(note.content)}</span>
            </div>
          </td>
          <td>${imageCell(displayMediaUrl(note), note.title)}</td>
          <td>${escapeHtml(note.nickname)}</td>
          <td>${escapeHtml(note.spot_name_zh || "-")}</td>
          <td>${statusPill(note.status)}</td>
          <td>${note.is_featured ? `<span class="pill">${t("精选")}</span>` : `<span class="pill warning">${t("普通")}</span>`}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-note-status="${note.id}" data-status="approved">${t("通过")}</button>
              <button class="small-btn" data-note-status="${note.id}" data-status="hidden">${t("隐藏")}</button>
              <button class="small-btn" data-note-feature="${note.id}">${note.is_featured ? t("取消精选") : t("设为精选")}</button>
              <button class="small-btn" data-edit-note="${note.id}">${t("审核")}</button>
              <button class="small-btn" data-assistant-review="travel_note:${note.id}">AI 初审</button>
              <button class="small-btn danger" data-delete-note="${note.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("travelNotesTable", "travelNotes");

  $("#commentsTable").innerHTML = state.comments
    .map(
      (comment) => `
        <tr>
          <td>${escapeHtml(comment.content)}</td>
          <td>${imageCell(displayMediaUrl(comment), t("留言图片"))}</td>
          <td>${escapeHtml(comment.nickname)}</td>
          <td>${escapeHtml(comment.spot_name_zh || "-")}</td>
          <td>${statusPill(comment.status)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-comment-status="${comment.id}" data-status="approved">${t("通过")}</button>
              <button class="small-btn danger" data-comment-status="${comment.id}" data-status="hidden">${t("隐藏")}</button>
              <button class="small-btn" data-edit-comment="${comment.id}">${t("审核")}</button>
              <button class="small-btn" data-assistant-review="comment:${comment.id}">AI 初审</button>
              <button class="small-btn danger" data-delete-comment="${comment.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("commentsTable", "comments");
}

function renderRecommendations() {
  $("#recommendationsTable").innerHTML = state.recommendations
    .map(
      (item) => `
        <tr>
          <td>${categoryText(item.category)}</td>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(item.name_zh)}</strong>
              <span class="muted">${escapeHtml(item.name_en)}</span>
            </div>
          </td>
          <td>${imageCell(displayMediaUrl(item), item.name_zh)}</td>
          <td>${escapeHtml(item.spot_name_zh || t("未设置"))}</td>
          <td>${escapeHtml(item.city)} / ${escapeHtml(item.county)}</td>
          <td>${escapeHtml(item.price_level)}</td>
          <td>${item.recommendation_level}</td>
          <td>${activePill(item.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-recommendation="${item.id}">${t("编辑")}</button>
              <button class="small-btn danger" data-delete-recommendation="${item.id}">${t("删除")}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
  renderPagination("recommendationsTable", "recommendations");
}

function renderIntegrations() {
  const panel = $("#integrationsPanel");
  if (!panel) return;
  panel.innerHTML = state.integrations
    .map(
      (group) => `
        <form class="integration-card" data-integration-form="${group.group}">
          <div class="section-head compact-head">
            <div>
              <h3>${escapeHtml(t(group.title_zh))}</h3>
              <p class="muted">${escapeHtml(t(group.description_zh))}</p>
            </div>
          </div>
          <div class="form-grid">
            ${group.settings.map((setting) => renderIntegrationField(setting)).join("")}
          </div>
          <footer>
            ${group.group === "weather" ? '<button type="button" class="secondary-btn" data-test-weather="true">测试和风天气</button>' : ""}
            ${group.group === "ai" ? '<button type="button" class="secondary-btn" data-test-ai="true">测试大模型连接</button>' : ""}
            ${group.group === "object_storage" ? '<button type="button" class="secondary-btn" data-test-object-storage="true">测试连接</button>' : ""}
            <button type="submit" class="primary-btn">${t("保存")}</button>
          </footer>
        </form>
      `,
    )
    .join("");
}

function renderIntegrationField(setting) {
  const value = escapeHtml(setting.value || "");
  const label = escapeHtml(state.lang === "en-US" ? setting.label_en : setting.label_zh);
  const status = setting.is_configured ? t("已配置") : t("未配置");
  const placeholder = setting.is_secret && setting.is_configured ? `${status}，${t("留空表示不修改")}` : "";
  if (setting.input_type === "checkbox") {
    const checked = String(setting.value).toLowerCase() === "true" ? "checked" : "";
    return `
      <label class="switch-line">
        <input name="${setting.key}" type="checkbox" ${checked} />
        <span>${label}</span>
      </label>
    `;
  }
  if (setting.input_type === "textarea") {
    return `
      <label class="full">
        <span>${label} <small class="muted">${status}</small></span>
        <textarea name="${setting.key}" rows="4" placeholder="${placeholder}">${setting.is_secret ? "" : value}</textarea>
      </label>
    `;
  }
  return `
    <label class="${setting.key.includes("PRIVATE_KEY_FILE") || setting.key.includes("API_BASE") ? "full" : ""}">
      <span>${label} <small class="muted">${status}</small></span>
      <input
        name="${setting.key}"
        type="${setting.input_type === "password" ? "password" : setting.input_type}"
        ${setting.key === "PUBLIC_API_OPEN_HOUR" ? 'min="0" max="23" step="1"' : ""}
        ${setting.key === "PUBLIC_API_CLOSE_HOUR" ? 'min="1" max="24" step="1"' : ""}
        value="${setting.is_secret ? "" : value}"
        placeholder="${placeholder}"
      />
    </label>
  `;
}

function collectIntegrationSettings(form, groupData) {
  const formData = new FormData(form);
  const settings = {};
  (groupData?.settings || []).forEach((setting) => {
    if (setting.input_type === "checkbox") {
      settings[setting.key] = Boolean(form.elements[setting.key]?.checked) ? "true" : "false";
      return;
    }
    const value = formData.get(setting.key);
    if (setting.is_secret && !value) {
      settings[setting.key] = null;
      return;
    }
    settings[setting.key] = String(value || "").trim();
  });
  return settings;
}

function renderSpotMediaPreview(image) {
  const url = escapeHtml(displayMediaUrl(image));
  const caption = escapeHtml(image.caption || t("秘境图片/视频"));
  if (image.media_type === "video") {
    return `<video class="image-thumb media-preview" src="${url}" controls preload="metadata"></video>`;
  }
  return `
    <a class="media-link" href="${url}" target="_blank" rel="noopener">
      <img class="image-thumb media-preview" src="${url}" alt="${caption}" />
    </a>
  `;
}

function renderSpotImages() {
  $("#spotImagesList").innerHTML = state.currentSpotImages.length
    ? state.currentSpotImages
        .map(
          (image) => `
            <article class="image-item">
              ${renderSpotMediaPreview(image)}
              <div class="cell-title">
                <strong>${escapeHtml(image.caption || t("未填写说明"))}</strong>
                <span class="muted">${image.media_type === "video" ? t("视频") : t("图片")} / ${t("排序")} ${image.sort_order} ${image.is_cover ? ` / ${t("封面")}` : ""}</span>
              </div>
              <div class="row-actions">
                ${
                  image.media_type === "video"
                    ? ""
                    : `<button type="button" class="small-btn" data-cover-image="${image.id}">${t("设为封面")}</button>`
                }
                <button type="button" class="small-btn danger" data-delete-image="${image.id}">${t("删除")}</button>
              </div>
            </article>
          `,
        )
        .join("")
    : `<p class="muted">${t("暂无媒体")}</p>`;
  renderPagination("spotImagesList", "spotImages");
}

function renderSpotCheckins() {
  const container = $("#spotCheckinsList");
  if (!container) return;
  container.innerHTML = state.currentSpotCheckins.length
    ? state.currentSpotCheckins
        .map((checkin) => {
          const media = checkin.media_url || checkin.image_url;
          const mediaType = checkin.media_type || "image";
          return `
            <article class="image-item">
              ${media ? renderSpotMediaPreview({ image_url: media, media_type: mediaType, caption: t("用户打卡媒体") }) : `<div class="form-media-preview muted">${t("未上传媒体")}</div>`}
              <div class="cell-title">
                <strong>${escapeHtml(checkin.nickname || t("用户"))}</strong>
                <span class="muted">${statusPill(checkin.status)} ${escapeHtml(checkin.note || t("未填写说明"))}</span>
                ${checkin.review_note ? `<span class="muted">${escapeHtml(checkin.review_note)}</span>` : ""}
              </div>
              <div class="row-actions">
                ${checkin.status !== "approved" ? `<button type="button" class="small-btn" data-spot-checkin-review="${checkin.id}" data-status="approved">${t("通过")}</button>` : ""}
                ${checkin.status !== "rejected" ? `<button type="button" class="small-btn" data-spot-checkin-review="${checkin.id}" data-status="rejected">${t("拒绝")}</button>` : ""}
                <button type="button" class="small-btn danger" data-delete-spot-checkin="${checkin.id}">${t("删除")}</button>
              </div>
            </article>
          `;
        })
        .join("")
    : `<p class="muted">${t("暂无用户打卡媒体")}</p>`;
}

function renderSpotComments() {
  const container = $("#spotCommentsList");
  if (!container) return;
  container.innerHTML = state.currentSpotComments.length
    ? state.currentSpotComments
        .map(
          (comment) => `
            <article class="image-item">
              ${comment.display_url || comment.image_url ? renderSpotMediaPreview({ ...comment, media_type: "image", caption: t("留言媒体") }) : ""}
              <div class="cell-title">
                <strong>${escapeHtml(comment.nickname || t("用户"))}</strong>
                <span>${escapeHtml(comment.content || "")}</span>
                <span class="muted">${statusPill(comment.status)}</span>
              </div>
              <div class="row-actions">
                ${comment.status !== "approved" ? `<button type="button" class="small-btn" data-spot-comment-status="${comment.id}" data-status="approved">${t("通过")}</button>` : ""}
                ${comment.status !== "hidden" ? `<button type="button" class="small-btn" data-spot-comment-status="${comment.id}" data-status="hidden">${t("隐藏")}</button>` : ""}
                <button type="button" class="small-btn danger" data-delete-spot-comment="${comment.id}">${t("删除")}</button>
              </div>
            </article>
          `,
        )
        .join("")
    : `<p class="muted">${t("暂无互动留言")}</p>`;
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function validateUploadFile(file, allowVideo = true) {
  if (!file) {
    return { valid: false, message: t("未选择文件"), isImage: false, isVideo: false };
  }
  const isImage = file.type.startsWith("image/");
  const isVideo = file.type.startsWith("video/");
  if (!isImage && (!allowVideo || !isVideo)) {
    return { valid: false, message: allowVideo ? t("请选择图片或视频") : t("请选择图片"), isImage, isVideo };
  }
  if (isImage && file.size > MAX_IMAGE_UPLOAD_BYTES) {
    return { valid: false, message: t("图片大小不能超过 2MB"), isImage, isVideo };
  }
  if (isVideo && file.size > MAX_VIDEO_UPLOAD_BYTES) {
    return { valid: false, message: t("视频大小不能超过 8MB"), isImage, isVideo };
  }
  return { valid: true, message: "", isImage, isVideo };
}

function updateUploadFileStatus(fileInputSelector, statusSelector, clearButtonSelector, allowVideo = true) {
  const fileInput = $(fileInputSelector);
  const status = $(statusSelector);
  const clearButton = $(clearButtonSelector);
  if (!fileInput || !status) return false;
  const file = fileInput.files[0];
  if (!file) {
    status.textContent = t("未选择文件");
    status.classList.remove("ok", "error");
    if (clearButton) clearButton.classList.add("hidden");
    return false;
  }
  const validation = validateUploadFile(file, allowVideo);
  const typeText = file.type || t("文件类型不支持");
  const baseText = `${t("已选择")}：${file.name} / ${t("文件类型")}：${typeText} / ${t("文件大小")}：${formatFileSize(file.size)}`;
  status.textContent = validation.valid ? baseText : `${baseText} / ${validation.message}`;
  status.classList.toggle("ok", validation.valid);
  status.classList.toggle("error", !validation.valid);
  if (clearButton) clearButton.classList.remove("hidden");
  return validation.valid;
}

function clearUploadFile(fileInputSelector, statusSelector, clearButtonSelector) {
  const fileInput = $(fileInputSelector);
  if (fileInput) fileInput.value = "";
  updateUploadFileStatus(fileInputSelector, statusSelector, clearButtonSelector);
}

function setUploadStatus(statusSelector, message, stateClass = "") {
  const status = $(statusSelector);
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("ok", stateClass === "ok");
  status.classList.toggle("error", stateClass === "error");
}

function uploadWithProgress(url, formData, statusSelector) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("Authorization", `Bearer ${state.token}`);
    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        setUploadStatus(statusSelector, t("正在上传"), "ok");
        return;
      }
      const percent = Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100)));
      setUploadStatus(statusSelector, `${t("上传进度")}：${percent}%`, "ok");
    });
    xhr.addEventListener("load", () => {
      const data = (() => {
        try {
          return JSON.parse(xhr.responseText || "{}");
        } catch (error) {
          return {};
        }
      })();
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploadStatus(statusSelector, t("上传完成"), "ok");
        resolve(data);
        return;
      }
      reject(new Error(data.detail || "上传失败"));
    });
    xhr.addEventListener("error", () => reject(new Error("上传失败")));
    xhr.send(formData);
  });
}

function clearChildPointForm() {
  $("#childPointName").value = "";
  $("#childPointLatitude").value = "";
  $("#childPointLongitude").value = "";
  $("#childPointNote").value = "";
  $("#childPointSort").value = "0";
  $("#childPointWeather").checked = false;
}

function renderChildPoints() {
  $("#childPointsList").innerHTML = state.currentSpotChildPoints.length
    ? state.currentSpotChildPoints
        .map(
          (point) => `
            <article class="image-item">
              <div class="cell-title">
                <strong>${escapeHtml(point.name)}</strong>
                <span class="muted">${Number(point.latitude).toFixed(6)}, ${Number(point.longitude).toFixed(6)} / ${t("排序")} ${point.sort_order}</span>
                <span class="muted">${point.fetch_weather ? t("获取天气") : t("不获取天气")}${point.note ? ` / ${escapeHtml(point.note)}` : ""}</span>
              </div>
              <div class="row-actions">
                <button class="small-btn danger" data-delete-child-point="${point.id}">${t("删除")}</button>
              </div>
            </article>
          `,
        )
        .join("")
    : `<p class="muted">${t("暂无子景点坐标")}</p>`;
}

function renderPagination(anchorId, key) {
  const meta = state.pagination[key] || { page: 1, page_size: PAGE_SIZE, pages: 0, total: 0 };
  const anchor = $(`#${anchorId}`);
  const host = anchor.closest(".table-wrap") || anchor.parentElement;
  if (!host) return;
  let pager = host.querySelector(`[data-pagination="${key}"]`);
  if (!pager) {
    pager = document.createElement("div");
    pager.className = "pagination";
    pager.dataset.pagination = key;
    host.appendChild(pager);
  }
  const totalPages = Math.max(meta.pages || 0, 1);
  pager.innerHTML = `
    <span>${state.lang === "en-US" ? `Page ${meta.page || 1} / ${totalPages}, ${meta.total || 0} total` : `第 ${meta.page || 1} / ${totalPages} 页，共 ${meta.total || 0} 条`}</span>
    <div class="row-actions">
      <button class="small-btn" data-page-key="${key}" data-page-target="${Math.max((meta.page || 1) - 1, 1)}" ${(meta.page || 1) <= 1 ? "disabled" : ""}>${t("上一页")}</button>
      <button class="small-btn" data-page-key="${key}" data-page-target="${Math.min((meta.page || 1) + 1, totalPages)}" ${(meta.page || 1) >= totalPages ? "disabled" : ""}>${t("下一页")}</button>
    </div>
  `;
}

function renderTagChecks(selectedIds = []) {
  const selected = new Set(selectedIds);
  $("#spotTagChecks").innerHTML = state.tags
    .filter((tag) => tag.is_active)
    .map(
      (tag) => `
        <label>
          <input type="checkbox" value="${tag.id}" ${selected.has(tag.id) ? "checked" : ""} />
          <span>${escapeHtml(tag.name_zh)}</span>
        </label>
      `,
    )
    .join("");
}

function renderSpotOptions(select, selectedId = null) {
  select.innerHTML = state.spots
    .map(
      (spot) => `
        <option value="${spot.id}" ${Number(selectedId) === spot.id ? "selected" : ""}>
          ${escapeHtml(spot.name_zh)}
        </option>
      `,
    )
    .join("");
}

async function loadData() {
  const [
    tags,
    spots,
    users,
    passSettings,
    membershipPlans,
    membershipRecords,
    checkins,
    travelNotes,
    comments,
    recommendations,
    integrations,
    assistantPending,
  ] = await Promise.all([
    requestPage("tags", "/admin/tags"),
    requestPage("spots", "/admin/spots"),
    requestPage("users", "/admin/users?include_inactive=false"),
    requestPage("passSettings", "/admin/pass-settings"),
    requestPage("membershipPlans", "/admin/memberships/plans"),
    requestPage("membershipRecords", "/admin/memberships/records"),
    requestPage("checkins", `/admin/checkins${new URLSearchParams(state.checkinFilters).toString() ? `?${new URLSearchParams(state.checkinFilters).toString()}` : ""}`),
    requestPage("travelNotes", "/admin/content/travel-notes"),
    requestPage("comments", "/admin/content/comments"),
    requestPage("recommendations", "/admin/content/recommendations"),
    request("/admin/integrations"),
    request("/admin/assistant/pending-summary"),
  ]);
  state.tags = tags;
  state.spots = spots;
  state.users = users;
  state.passSettings = passSettings;
  state.membershipPlans = membershipPlans;
  state.membershipRecords = membershipRecords;
  state.checkins = checkins;
  state.travelNotes = travelNotes;
  state.comments = comments;
  state.recommendations = recommendations;
  state.integrations = integrations;
  state.assistantPending = assistantPending;
  renderAll();
}

async function loadPassSettings() {
  state.passSettings = await requestPage("passSettings", "/admin/pass-settings");
  renderPassSettings();
  renderMetrics();
}

async function requestPage(key, path) {
  const meta = state.pagination[key] || { page: 1 };
  const pageSize = meta.page_size || PAGE_SIZE_BY_KEY[key] || PAGE_SIZE;
  const separator = path.includes("?") ? "&" : "?";
  const data = await request(`${path}${separator}page=${meta.page || 1}&page_size=${pageSize}`);
  if (data.total > 0 && data.pages > 0 && data.page > data.pages) {
    state.pagination[key] = { ...meta, page: data.pages };
    return requestPage(key, path);
  }
  const pageData = {
    total: data.total,
    page: data.page,
    page_size: data.page_size,
    pages: data.pages,
  };
  state.pagination[key] = pageData;
  return data.items;
}

async function bootstrap() {
  if (!state.token) {
    setAuthenticated(false);
    applyLanguage();
    return;
  }
  try {
    state.admin = await request("/admin/me");
    renderAdminInfo();
    setAuthenticated(true);
    setActiveSection(getInitialSectionId(), { skipHash: Boolean(window.location.hash) });
    await loadData();
    applyLanguage();
  } catch (error) {
    localStorage.removeItem("gz_admin_token");
    state.token = "";
    setAuthenticated(false);
    applyLanguage();
  }
}

function formToObject(form) {
  const formData = new FormData(form);
  return Object.fromEntries(formData.entries());
}

function getSelectedSpotTagIds() {
  return $$("#spotTagChecks input:checked").map((input) => Number(input.value));
}

function fillAccountSettingsForm() {
  const form = $("#accountSettingsForm");
  form.reset();
  form.elements.username.value = state.admin?.username || "";
  form.elements.current_password.value = "";
  form.elements.new_password.value = "";
}

function fillSpotForm(spot = null) {
  const form = $("#spotForm");
  form.reset();
  state.editingSpotId = spot?.id || null;
  $("#spotDialogTitle").textContent = spot ? t("编辑秘境") : t("新增秘境");
  renderTagChecks(spot?.tag_ids || []);
  renderSpotLevelOptions(spot?.recommendation_level);

  if (!spot) {
    state.currentSpotImages = [];
    state.currentSpotCheckins = [];
    state.currentSpotComments = [];
    state.currentSpotChildPoints = [];
    renderSpotImages();
    renderSpotCheckins();
    renderSpotComments();
    renderChildPoints();
    clearChildPointForm();
    form.elements.review_status.value = "draft";
    form.elements.visibility_level.value = "public";
    form.elements.required_explore_points.value = 0;
    form.elements.checkin_radius_meters.value = 300;
    form.elements.river_name.value = "";
    form.elements.river_upstream_latitude.value = "";
    form.elements.river_upstream_longitude.value = "";
    form.elements.is_active.checked = true;
    return;
  }
  state.currentSpotChildPoints = spot.child_points || [];
  renderChildPoints();
  clearChildPointForm();

  [
    "name_zh",
    "name_en",
    "summary_zh",
    "summary_en",
    "description_zh",
    "description_en",
    "city",
    "county",
    "latitude",
    "longitude",
    "river_name",
    "river_upstream_latitude",
    "river_upstream_longitude",
    "visibility_level",
    "review_status",
    "recommendation_level",
    "required_explore_points",
    "checkin_radius_meters",
  ].forEach((field) => {
    form.elements[field].value = spot[field] ?? "";
  });
  form.elements.is_active.checked = Boolean(spot.is_active);
}

function renderSpotLevelOptions(selectedLevel = null) {
  const select = $("#spotForm").elements.recommendation_level;
  const settings = [...state.passSettings].sort((left, right) => Number(left.level) - Number(right.level));
  if (!settings.length) {
    select.disabled = true;
    select.innerHTML = `<option value="">${t("请先配置通关等级")}</option>`;
    return;
  }

  select.disabled = false;
  select.innerHTML = settings
    .map((setting) => {
      const name = state.lang === "en-US" ? setting.name_en : setting.name_zh;
      const status = setting.is_active ? "" : ` (${t("停用")})`;
      return `<option value="${setting.level}">L${setting.level} ${escapeHtml(name)}${status}</option>`;
    })
    .join("");

  const defaultLevel = settings.find((setting) => setting.is_active)?.level ?? settings[0].level;
  select.value = String(selectedLevel ?? defaultLevel);
}

function fillTagForm(tag = null) {
  const form = $("#tagForm");
  form.reset();
  state.editingTagId = tag?.id || null;
  $("#tagDialogTitle").textContent = tag ? t("编辑标签") : t("新增标签");
  if (!tag) {
    form.elements.sort_order.value = 0;
    form.elements.is_active.checked = true;
    return;
  }
  ["name_zh", "name_en", "icon", "sort_order"].forEach((field) => {
    form.elements[field].value = tag[field] ?? "";
  });
  form.elements.is_active.checked = Boolean(tag.is_active);
}

function fillUserForm(user) {
  const form = $("#userForm");
  form.reset();
  state.editingUserId = user?.id || null;
  $("#userDialogTitle").textContent = user ? `${t("编辑用户")}：${user.nickname}` : t("新增用户");
  if (!user) {
    $("#userAvatarPreview").innerHTML = '<span class="default-avatar">用</span><span class="muted">系统默认头像</span>';
    form.elements.language.value = "zh-CN";
    form.elements.explore_points.value = 0;
    form.elements.checkin_count.value = 0;
    form.elements.contribution_count.value = 0;
    form.elements.eco_credit.value = 100;
    form.elements.is_member.checked = false;
    form.elements.is_active.checked = true;
    form.elements.can_upload_image.checked = true;
    form.elements.can_upload_video.checked = true;
    form.elements.can_comment.checked = true;
    form.elements.can_checkin.checked = true;
    return;
  }
  [
    "openid",
    "nickname",
    "phone",
    "language",
    "explore_points",
    "checkin_count",
    "contribution_count",
    "eco_credit",
  ].forEach((field) => {
    form.elements[field].value = user[field] ?? "";
  });
  $("#userAvatarPreview").innerHTML = userAvatarCell(user.avatar_url, user.nickname);
  form.elements.is_member.checked = Boolean(user.is_member);
  form.elements.is_active.checked = Boolean(user.is_active);
  form.elements.can_upload_image.checked = user.can_upload_image !== false;
  form.elements.can_upload_video.checked = user.can_upload_video !== false;
  form.elements.can_comment.checked = user.can_comment !== false;
  form.elements.can_checkin.checked = user.can_checkin !== false;
}

function fillTravelNoteForm(note = null) {
  const form = $("#travelNoteForm");
  form.reset();
  form.dataset.mediaDisplayUrl = "";
  state.editingTravelNoteId = note?.id || null;
  $("#travelNoteDialogTitle").textContent = note ? `${t("审核")}：${note.title}` : t("新增游记");
  if (!note) {
    form.elements.status.value = "pending";
    form.elements.is_featured.checked = false;
    renderFormMediaPreview("#travelNoteForm", "#travelNoteMediaPreview", t("游记"));
    renderContentMediaReview("#travelNoteReviewMedia", []);
    return;
  }
  ["user_id", "spot_id", "title", "content", "image_url", "status"].forEach((field) => {
    form.elements[field].value = note[field] ?? "";
  });
  form.dataset.mediaDisplayUrl = displayMediaUrl(note);
  renderContentMediaReview("#travelNoteReviewMedia", note.media || []);
  form.elements.is_featured.checked = Boolean(note.is_featured);
  renderFormMediaPreview("#travelNoteForm", "#travelNoteMediaPreview", note.title);
}

function fillCommentForm(comment = null) {
  const form = $("#commentForm");
  form.reset();
  form.dataset.mediaDisplayUrl = "";
  state.editingCommentId = comment?.id || null;
  $("#commentDialogTitle").textContent = comment ? `${t("审核")}：${comment.nickname}` : t("新增留言");
  if (!comment) {
    form.elements.status.value = "pending";
    renderFormMediaPreview("#commentForm", "#commentMediaPreview", t("留言图片"));
    renderContentMediaReview("#commentReviewMedia", []);
    return;
  }
  ["user_id", "spot_id", "content", "image_url", "status"].forEach((field) => {
    form.elements[field].value = comment[field] ?? "";
  });
  form.dataset.mediaDisplayUrl = displayMediaUrl(comment);
  renderContentMediaReview("#commentReviewMedia", comment.media || []);
  renderFormMediaPreview("#commentForm", "#commentMediaPreview", t("留言图片"));
}

function renderContentMediaReview(selector, mediaItems) {
  const container = $(selector);
  if (!container) return;
  container.innerHTML = mediaItems.length
    ? mediaItems.map((item) => `
      <div class="spot-image-item">
        ${renderSpotMediaPreview({ image_url: item.display_url || item.media_url, media_type: item.media_type, caption: item.status })}
        <div class="row-actions">
          <button type="button" class="small-btn" data-content-media-review="${item.id}" data-status="approved">${t("通过")}</button>
          <button type="button" class="small-btn danger" data-content-media-review="${item.id}" data-status="rejected">${t("拒绝")}</button>
          <button type="button" class="small-btn danger" data-delete-content-media="${item.id}">${t("删除")}</button>
        </div>
      </div>`).join("")
    : `<span class="muted">暂无用户上传媒体</span>`;
}

function fillPassSettingForm(setting) {
  const form = $("#passSettingForm");
  form.reset();
  state.editingPassSettingId = setting?.id || null;
  $("#passSettingDialogTitle").textContent = setting ? `${t("编辑通关设置")}：L${setting.level}` : t("新增通关等级");
  const nextLevel = state.passSettings.length ? Math.max(...state.passSettings.map((item) => Number(item.level) || 0)) + 1 : 0;
  const markerColor = normalizeHexColor(setting?.marker_color || "#2f6b4f");
  form.elements.level.value = setting?.level ?? nextLevel;
  form.elements.level.disabled = false;
  setPassMarkerColorInputs(markerColor);
  if (!setting) {
    form.elements.required_explore_points.value = 0;
    form.elements.checkin_points.value = 0;
    form.elements.requires_membership.checked = false;
    form.elements.is_active.checked = true;
    return;
  }
  [
    "name_zh",
    "name_en",
    "required_explore_points",
    "checkin_points",
    "unlock_benefit_zh",
    "unlock_benefit_en",
  ].forEach((field) => {
    form.elements[field].value = setting[field] ?? "";
  });
  form.elements.requires_membership.checked = Boolean(setting.requires_membership);
  form.elements.is_active.checked = Boolean(setting.is_active);
}

function normalizeHexColor(color) {
  const value = String(color || "").trim();
  return /^#[0-9a-fA-F]{6}$/.test(value) ? value.toUpperCase() : "#2F6B4F";
}

function setPassMarkerColorInputs(color) {
  const normalized = normalizeHexColor(color);
  const form = $("#passSettingForm");
  form.elements.marker_color.value = normalized;
  $("#passMarkerColorText").value = normalized;
}

function fillMembershipPlanForm(plan = null) {
  const form = $("#membershipPlanForm");
  form.reset();
  state.editingMembershipPlanId = plan?.id || null;
  $("#membershipPlanDialogTitle").textContent = plan ? `${t("编辑会员套餐")}：${plan.name_zh}` : t("新增会员套餐");
  if (!plan) {
    form.elements.duration_days.value = 30;
    form.elements.price_cents.value = 0;
    form.elements.required_explore_points.value = 0;
    form.elements.is_active.checked = true;
    return;
  }
  ["name_zh", "name_en", "duration_days", "price_cents", "required_explore_points", "benefits_zh", "benefits_en"].forEach((field) => {
    form.elements[field].value = plan[field] ?? "";
  });
  form.elements.is_active.checked = Boolean(plan.is_active);
}

function fillCheckinForm(checkin) {
  const form = $("#checkinForm");
  form.reset();
  state.editingCheckinId = checkin.id;
  $("#checkinDialogTitle").textContent = `${t("审核")}：${checkin.nickname} / ${checkin.spot_name_zh}`;
  form.elements.status.value = checkin.status;
  form.elements.review_note.value = checkin.review_note || "";
}

function fillRecommendationForm(item = null) {
  const form = $("#recommendationForm");
  form.reset();
  form.dataset.mediaDisplayUrl = "";
  state.editingRecommendationId = item?.id || null;
  $("#recommendationDialogTitle").textContent = item ? `${t("编辑推荐")}：${item.name_zh}` : t("新增推荐");
  renderSpotOptions(form.elements.spot_id, item?.spot_id || state.spots[0]?.id);
  if (!item) {
    form.elements.category.value = "food";
    form.elements.price_level.value = "mid";
    form.elements.recommendation_level.value = 1;
    form.elements.is_active.checked = true;
    renderFormMediaPreview("#recommendationForm", "#recommendationMediaPreview", t("推荐"));
    return;
  }
  [
    "spot_id",
    "category",
    "name_zh",
    "name_en",
    "summary_zh",
    "summary_en",
    "city",
    "county",
    "address",
    "contact",
    "image_url",
    "price_level",
    "recommendation_level",
  ].forEach((field) => {
    form.elements[field].value = item[field] ?? "";
  });
  form.dataset.mediaDisplayUrl = displayMediaUrl(item);
  form.elements.is_active.checked = Boolean(item.is_active);
  renderFormMediaPreview("#recommendationForm", "#recommendationMediaPreview", item.name_zh);
}

async function loadSpotImages(spotId) {
  if (!spotId) {
    state.currentSpotImages = [];
    state.pagination.spotImages = { page: 1, page_size: PAGE_SIZE, pages: 0, total: 0 };
    renderSpotImages();
    return;
  }
  state.currentSpotImages = await requestPage("spotImages", `/admin/content/spots/${spotId}/images`);
  renderSpotImages();
}

async function loadSpotCheckins(spotId) {
  if (!spotId) {
    state.currentSpotCheckins = [];
    renderSpotCheckins();
    return;
  }
  state.currentSpotCheckins = await requestPage("spotCheckins", `/admin/spots/${spotId}/checkins`);
  renderSpotCheckins();
}

async function loadSpotComments(spotId) {
  if (!spotId) {
    state.currentSpotComments = [];
    renderSpotComments();
    return;
  }
  state.currentSpotComments = await requestPage("spotComments", `/admin/content/comments?spot_id=${spotId}`);
  renderSpotComments();
}

async function refreshCurrentSpotChildPoints() {
  await loadData();
  const spot = state.spots.find((item) => item.id === state.editingSpotId);
  state.currentSpotChildPoints = spot?.child_points || [];
  renderChildPoints();
}

async function uploadImageTo(folder, fileInputSelector, formSelector, fieldName = "image_url", allowVideo = true, previewSelector = "") {
  const fileInput = $(fileInputSelector);
  const statusSelector = `${fileInputSelector}Status`;
  const clearButtonSelector = `#clear${fileInput.id[0].toUpperCase()}${fileInput.id.slice(1)}Btn`;
  const file = fileInput.files[0];
  if (!file) {
    showToast(allowVideo ? "请选择图片或视频" : "请选择图片");
    return;
  }
  const validation = validateUploadFile(file, allowVideo);
  if (!validation.valid) {
    showToast(validation.message);
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  const data = await uploadWithProgress(`${API}/admin/content/uploads/${folder}`, formData, statusSelector);
  const form = $(formSelector);
  form.elements[fieldName].value = data.image_url;
  if (fieldName === "image_url") {
    form.dataset.mediaDisplayUrl = data.display_url || data.image_url || "";
  }
  if (previewSelector) renderFormMediaPreview(formSelector, previewSelector);
  fileInput.value = "";
  updateUploadFileStatus(fileInputSelector, statusSelector, clearButtonSelector, allowVideo);
  setUploadStatus(statusSelector, t("上传完成"), "ok");
  showToast("媒体已上传");
}

async function deleteFormMedia(formSelector, resourcePath, editingId, statusSelector = "", previewSelector = "") {
  const form = $(formSelector);
  if (!form.elements.image_url.value) return;
  if (!confirmDeletion()) return;
  if (editingId) {
    if (statusSelector) setUploadStatus(statusSelector, t("正在删除OSS文件"), "ok");
    await request(`${resourcePath}/${editingId}`, {
      method: "PATCH",
      body: JSON.stringify({ image_url: null }),
    });
    await loadData();
  }
  form.elements.image_url.value = "";
  form.dataset.mediaDisplayUrl = "";
  if (previewSelector) renderFormMediaPreview(formSelector, previewSelector);
  if (statusSelector) setUploadStatus(statusSelector, t("OSS文件已删除"), "ok");
  showToast("媒体已删除");
}

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#loginError").textContent = "";
  try {
    const data = await request("/admin/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("#loginUsername").value.trim(),
        password: $("#loginPassword").value,
      }),
    });
    state.token = data.access_token;
    state.admin = data.admin;
    localStorage.setItem("gz_admin_token", state.token);
    renderAdminInfo();
    setAuthenticated(true);
    setActiveSection(getInitialSectionId(), { skipHash: Boolean(window.location.hash) });
    await loadData();
  } catch (error) {
    $("#loginError").textContent = error.message;
  }
});

$("#logoutBtn").addEventListener("click", () => {
  localStorage.removeItem("gz_admin_token");
  state.token = "";
  setAuthenticated(false);
  applyLanguage();
});

["#langToggleBtn", "#loginLangToggleBtn"].forEach((selector) => {
  $(selector).addEventListener("click", () => {
    setLanguage(state.lang === "en-US" ? "zh-CN" : "en-US");
  });
});

$("#refreshBtn").addEventListener("click", async () => {
  await loadData();
  showToast("已刷新");
});

$("#checkinSearchForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  state.checkinFilters = Object.fromEntries(
    [...new FormData(form).entries()].filter(([, value]) => String(value).trim()),
  );
  state.pagination.checkins = { ...(state.pagination.checkins || {}), page: 1 };
  await loadData();
});

$("#resetCheckinSearchBtn").addEventListener("click", async () => {
  $("#checkinSearchForm").reset();
  state.checkinFilters = {};
  state.pagination.checkins = { ...(state.pagination.checkins || {}), page: 1 };
  await loadData();
});

$("#accountSettingsBtn").addEventListener("click", () => {
  fillAccountSettingsForm();
  $("#accountSettingsDialog").showModal();
});

$("#newSpotBtn").addEventListener("click", () => {
  fillSpotForm();
  $("#spotDialog").showModal();
});

$("#newTagBtn").addEventListener("click", () => {
  fillTagForm();
  $("#tagDialog").showModal();
});

$("#newUserBtn").addEventListener("click", () => {
  fillUserForm();
  $("#userDialog").showModal();
});

$("#newPassSettingBtn").addEventListener("click", () => {
  fillPassSettingForm();
  $("#passSettingDialog").showModal();
});

$("#newMembershipPlanBtn").addEventListener("click", () => {
  fillMembershipPlanForm();
  $("#membershipPlanDialog").showModal();
});

$("#passSettingForm").elements.marker_color.addEventListener("input", (event) => {
  setPassMarkerColorInputs(event.target.value);
});

$("#passMarkerColorText").addEventListener("input", (event) => {
  const value = event.target.value.trim();
  if (/^#[0-9a-fA-F]{6}$/.test(value)) {
    $("#passSettingForm").elements.marker_color.value = value;
  }
});

$("#passMarkerColorText").addEventListener("blur", (event) => {
  setPassMarkerColorInputs(event.target.value);
});

$("#newTravelNoteBtn").addEventListener("click", () => {
  fillTravelNoteForm();
  $("#travelNoteDialog").showModal();
});

$("#newCommentBtn").addEventListener("click", () => {
  fillCommentForm();
  $("#commentDialog").showModal();
});

$("#newRecommendationBtn").addEventListener("click", () => {
  fillRecommendationForm();
  $("#recommendationDialog").showModal();
});

$$("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => {
    $(`#${button.dataset.closeDialog}`).close();
  });
});

$("#adminAssistantToggle").addEventListener("click", () => {
  renderAssistantPending();
  renderAssistantMessages();
  $("#adminAssistantDialog").showModal();
});

$("#assistantPendingSummary").addEventListener("click", (event) => {
  const button = event.target.closest("[data-assistant-pending-section]");
  if (!button) return;
  setActiveSection(button.dataset.assistantPendingSection);
  if ($("#adminAssistantDialog").open) $("#adminAssistantDialog").close();
  const target = button.dataset.assistantPendingSection === "checkinsSection" ? "#checkinsTable" : "#travelNotesTable";
  window.setTimeout(() => $(target)?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
});

$$("[data-assistant-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    const mode = button.dataset.assistantMode;
    state.assistantMode = mode;
    const prompts = {
      guide: "请说明当前页面的常用操作和字段配置方法。",
      spot_summary: "请根据我接下来提供的景点资料，生成适合小程序展示的中英文简介，并提示需要人工核实的内容。",
      coordinate: "请说明如何合法、准确地采集景点坐标，并如何处理需要保护的精确坐标。",
      review: "请说明游记、留言及其图片/视频的初审流程与风险检查要点。",
    };
    $("#assistantInput").value = prompts[mode] || "";
    $("#assistantInput").focus();
  });
});

$("#assistantSendBtn").addEventListener("click", async () => {
  const input = $("#assistantInput");
  const message = input.value;
  input.value = "";
  await sendAssistantMessage(message);
});

document.addEventListener("click", (event) => {
  const value = event.target.dataset.assistantReview;
  if (!value) return;
  const [contentType, contentId] = value.split(":");
  reviewWithAssistant(contentType, contentId);
});

$$(".nav-btn").forEach((button) => {
  button.addEventListener("click", () => {
    setActiveSection(button.dataset.section);
  });
});

window.addEventListener("hashchange", () => {
  setActiveSection(getInitialSectionId(), { skipHash: true });
});

document.addEventListener("click", async (event) => {
  if (event.target.dataset.testAi) {
    const button = event.target;
    const form = button.closest("[data-integration-form]");
    const groupData = state.integrations.find((item) => item.group === "ai");
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "正在测试大模型连接...";
    try {
      const updated = await request("/admin/integrations/ai", {
        method: "PATCH",
        body: JSON.stringify({ settings: collectIntegrationSettings(form, groupData) }),
      });
      state.integrations = state.integrations.map((item) => (item.group === "ai" ? updated : item));
      const result = await request("/admin/integrations/ai/test", { method: "POST" });
      renderIntegrations();
      applyLanguage($("#integrationsSection"));
      showToast(`大模型连接成功：${result.provider} / ${result.model} · ${result.response}`);
    } catch (error) {
      showToast(`大模型连接失败：${error.message || "未知错误"}`);
      button.disabled = false;
      button.textContent = originalText;
    }
    return;
  }

  if (event.target.dataset.testWeather) {
    const button = event.target;
    const form = button.closest("[data-integration-form]");
    const groupData = state.integrations.find((item) => item.group === "weather");
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "正在测试天气接口...";
    try {
      const updated = await request("/admin/integrations/weather", {
        method: "PATCH",
        body: JSON.stringify({ settings: collectIntegrationSettings(form, groupData) }),
      });
      state.integrations = state.integrations.map((item) => (item.group === "weather" ? updated : item));
      const result = await request("/admin/integrations/weather/test", { method: "POST" });
      renderIntegrations();
      applyLanguage($("#integrationsSection"));
      showToast(`天气获取成功：${result.spot} · ${result.weather.text || "-"} ${result.weather.temp || "-"}°C`);
    } catch (error) {
      const detail = error.message || "未知错误";
      showToast(`天气接口测试失败：${detail}`);
      button.disabled = false;
      button.textContent = originalText;
    }
    return;
  }

  if (event.target.dataset.testObjectStorage) {
    const button = event.target;
    const form = button.closest("[data-integration-form]");
    const groupData = state.integrations.find((item) => item.group === "object_storage");
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = t("正在测试 OSS 连接...");
    showToast("正在测试 OSS 连接...");
    try {
      const updated = await request("/admin/integrations/object_storage", {
        method: "PATCH",
        body: JSON.stringify({ settings: collectIntegrationSettings(form, groupData) }),
      });
      state.integrations = state.integrations.map((item) => (item.group === "object_storage" ? updated : item));
      const result = await request("/admin/integrations/object-storage/test", { method: "POST" });
      renderIntegrations();
      applyLanguage($("#integrationsSection"));
      showToast(`${t("OSS 连接成功")}：${result.bucket} / ${result.region}`);
    } catch (error) {
      showToast(`${t("OSS 连接失败")}：${error.message}`);
      button.disabled = false;
      button.textContent = originalText;
    }
    return;
  }

  const pageKey = event.target.dataset.pageKey;
  const pageTarget = event.target.dataset.pageTarget;
  if (!pageKey || !pageTarget) return;

  state.pagination[pageKey] = {
    ...(state.pagination[pageKey] || { page_size: PAGE_SIZE }),
    page: Number(pageTarget),
  };
  if (pageKey === "spotImages") {
    await loadSpotImages(state.editingSpotId);
  } else {
    await loadData();
  }
});

document.addEventListener("submit", async (event) => {
  const form = event.target.closest("[data-integration-form]");
  if (!form) return;
  event.preventDefault();
  const group = form.dataset.integrationForm;
  const groupData = state.integrations.find((item) => item.group === group);
  const settings = collectIntegrationSettings(form, groupData);
  const updated = await request(`/admin/integrations/${group}`, {
    method: "PATCH",
    body: JSON.stringify({ settings }),
  });
  state.integrations = state.integrations.map((item) => (item.group === group ? updated : item));
  renderIntegrations();
  applyLanguage($("#integrationsSection"));
  showToast("接口配置已保存");
});

$("#spotsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editSpot;
  const reviewId = event.target.dataset.reviewSpot;
  const deleteId = event.target.dataset.deleteSpot;

  if (editId) {
    const spot = state.spots.find((item) => item.id === Number(editId));
    fillSpotForm(spot);
    state.pagination.spotImages = { page: 1, page_size: PAGE_SIZE };
    state.pagination.spotCheckins = { page: 1, page_size: PAGE_SIZE };
    state.pagination.spotComments = { page: 1, page_size: PAGE_SIZE };
    await Promise.all([loadSpotImages(spot.id), loadSpotCheckins(spot.id), loadSpotComments(spot.id)]);
    $("#spotDialog").showModal();
  }

  if (reviewId) {
    await request(`/admin/spots/${reviewId}/review`, {
      method: "PATCH",
      body: JSON.stringify({ review_status: event.target.dataset.reviewStatus }),
    });
    await loadData();
    showToast("审核状态已更新");
  }

  if (deleteId && confirmDeletion()) {
    await request(`/admin/spots/${deleteId}`, { method: "DELETE" });
    await loadData();
    showToast("秘境已删除");
  }
});

$("#tagsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editTag;
  const deleteId = event.target.dataset.deleteTag;

  if (editId) {
    const tag = state.tags.find((item) => item.id === Number(editId));
    fillTagForm(tag);
    $("#tagDialog").showModal();
  }

  if (deleteId && confirmDeletion()) {
    try {
      await request(`/admin/tags/${deleteId}`, { method: "DELETE" });
      await loadData();
      showToast("标签已删除");
    } catch (error) {
      showToast(`${t("删除失败")}：${error.message}`);
    }
  }
});

$("#usersTable").addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit-user]");
  const toggleButton = event.target.closest("[data-toggle-user]");
  const deleteButton = event.target.closest("[data-delete-user]");
  const editId = editButton?.dataset.editUser;
  const toggleId = toggleButton?.dataset.toggleUser;
  const deleteId = deleteButton?.dataset.deleteUser;

  if (editId) {
    try {
      let user = state.users.find((item) => item.id === Number(editId));
      if (!user) user = await request(`/admin/users/${editId}`);
      if (!user) throw new Error("User not found");
      fillUserForm(user);
      $("#userDialog").showModal();
    } catch (error) {
      showToast(`${t("加载失败")}：${error.message}`);
    }
  }

  if (toggleId) {
    const user = state.users.find((item) => item.id === Number(toggleId));
    await request(`/admin/users/${toggleId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !user.is_active }),
    });
    await loadData();
    showToast("用户状态已更新");
  }

  if (deleteId && confirmDeletion()) {
    await request(`/admin/users/${deleteId}`, { method: "DELETE" });
    state.users = state.users.filter((user) => user.id !== Number(deleteId));
    renderUsers();
    renderMetrics();
    await loadData();
    showToast("用户已删除");
  }
});

$("#passSettingsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editPass;
  const deleteId = event.target.dataset.deletePass;

  if (editId) {
    const setting = state.passSettings.find((item) => item.id === Number(editId));
    fillPassSettingForm(setting);
    $("#passSettingDialog").showModal();
  }
  if (deleteId && confirmDeletion()) {
    try {
      await request(`/admin/pass-settings/${deleteId}`, { method: "DELETE" });
      await loadPassSettings();
      showToast("通关设置已删除");
    } catch (error) {
      showToast(`${t("删除失败")}：${error.message}`);
    }
  }
});

$("#membershipPlansTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editPlan;
  const deleteId = event.target.dataset.deletePlan;

  if (editId) {
    const plan = state.membershipPlans.find((item) => item.id === Number(editId));
    fillMembershipPlanForm(plan);
    $("#membershipPlanDialog").showModal();
  }
  if (deleteId && confirmDeletion()) {
    try {
      await request(`/admin/memberships/plans/${deleteId}`, { method: "DELETE" });
      await loadData();
      showToast("会员套餐已删除");
    } catch (error) {
      showToast(`${t("删除失败")}：${error.message}`);
    }
  }
});

$("#checkinsTable").addEventListener("click", async (event) => {
  event.preventDefault();
});

document.addEventListener("click", async (event) => {
  const reviewButton = event.target.closest("[data-content-media-review]");
  const deleteButton = event.target.closest("[data-delete-content-media]");
  if (!reviewButton && !deleteButton) return;
  const mediaId = reviewButton?.dataset.contentMediaReview || deleteButton?.dataset.deleteContentMedia;
  if (deleteButton && !confirmDeletion()) return;
  if (reviewButton) {
    await request(`/admin/content/media/${mediaId}/review`, {
      method: "PATCH",
      body: JSON.stringify({ status: reviewButton.dataset.status }),
    });
  } else {
    await request(`/admin/content/media/${mediaId}`, { method: "DELETE" });
  }
  await loadData();
  const note = state.travelNotes.find((item) => item.id === state.editingTravelNoteId);
  const comment = state.comments.find((item) => item.id === state.editingCommentId);
  if (note && $("#travelNoteDialog").open) fillTravelNoteForm(note);
  if (comment && $("#commentDialog").open) fillCommentForm(comment);
  showToast("媒体审核已完成");
});

$("#travelNotesTable").addEventListener("click", async (event) => {
  const statusId = event.target.dataset.noteStatus;
  const featureId = event.target.dataset.noteFeature;
  const editId = event.target.dataset.editNote;
  const deleteId = event.target.dataset.deleteNote;

  if (statusId) {
    const note = state.travelNotes.find((item) => item.id === Number(statusId));
    await request(`/admin/content/travel-notes/${statusId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: event.target.dataset.status, is_featured: note.is_featured }),
    });
    await loadData();
    showToast("游记状态已更新");
  }

  if (featureId) {
    const note = state.travelNotes.find((item) => item.id === Number(featureId));
    await request(`/admin/content/travel-notes/${featureId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: note.status, is_featured: !note.is_featured }),
    });
    await loadData();
    showToast("游记精选状态已更新");
  }

  if (editId) {
    const note = state.travelNotes.find((item) => item.id === Number(editId));
    fillTravelNoteForm(note);
    $("#travelNoteDialog").showModal();
  }

  if (deleteId && confirmDeletion()) {
    await request(`/admin/content/travel-notes/${deleteId}`, { method: "DELETE" });
    await loadData();
    showToast("游记已删除");
  }
});

$("#commentsTable").addEventListener("click", async (event) => {
  const statusId = event.target.dataset.commentStatus;
  const editId = event.target.dataset.editComment;
  const deleteId = event.target.dataset.deleteComment;

  if (statusId) {
    await request(`/admin/content/comments/${statusId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: event.target.dataset.status }),
    });
    await loadData();
    showToast("留言状态已更新");
  }

  if (editId) {
    const comment = state.comments.find((item) => item.id === Number(editId));
    fillCommentForm(comment);
    $("#commentDialog").showModal();
  }

  if (deleteId && confirmDeletion()) {
    await request(`/admin/content/comments/${deleteId}`, { method: "DELETE" });
    await loadData();
    showToast("留言已删除");
  }
});

$("#recommendationsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editRecommendation;
  const deleteId = event.target.dataset.deleteRecommendation;

  if (editId) {
    const item = state.recommendations.find((recommendation) => recommendation.id === Number(editId));
    fillRecommendationForm(item);
    $("#recommendationDialog").showModal();
  }

  if (deleteId && confirmDeletion()) {
    await request(`/admin/content/recommendations/${deleteId}`, { method: "DELETE" });
    await loadData();
    showToast("推荐已删除");
  }
});

$("#spotImagesList").addEventListener("click", async (event) => {
  event.preventDefault();
  event.stopPropagation();
  const coverId = event.target.dataset.coverImage;
  const deleteId = event.target.dataset.deleteImage;

  if (coverId) {
    await request(`/admin/content/spot-images/${coverId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_cover: true, is_active: true }),
    });
    await loadSpotImages(state.editingSpotId);
    showToast("封面已更新");
  }

  if (deleteId && confirmDeletion()) {
    showToast("正在删除OSS文件");
    await request(`/admin/content/spot-images/${deleteId}`, {
      method: "DELETE",
    });
    await loadSpotImages(state.editingSpotId);
    showToast("OSS文件已删除");
  }
});

$("#spotCheckinsList").addEventListener("click", async (event) => {
  const checkinId = event.target.dataset.spotCheckinReview;
  const deleteId = event.target.dataset.deleteSpotCheckin;
  if (checkinId) {
    await request(`/admin/checkins/${checkinId}/review`, {
      method: "PATCH",
      body: JSON.stringify({
        status: event.target.dataset.status,
        review_note: event.target.dataset.status === "approved" ? "秘境媒体审核通过。" : "秘境媒体审核未通过。",
      }),
    });
    await Promise.all([loadSpotCheckins(state.editingSpotId), loadSpotImages(state.editingSpotId), loadData()]);
    showToast("打卡媒体审核已更新");
  }
  if (deleteId && confirmDeletion()) {
    await request(`/admin/checkins/${deleteId}`, { method: "DELETE" });
    await Promise.all([loadSpotCheckins(state.editingSpotId), loadSpotImages(state.editingSpotId), loadData()]);
    showToast("用户打卡媒体已删除");
  }
});

$("#spotCommentsList").addEventListener("click", async (event) => {
  const commentId = event.target.dataset.spotCommentStatus;
  const deleteId = event.target.dataset.deleteSpotComment;
  if (commentId) {
    await request(`/admin/content/comments/${commentId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: event.target.dataset.status }),
    });
    await Promise.all([loadSpotComments(state.editingSpotId), loadData()]);
    showToast("互动留言状态已更新");
  }
  if (deleteId && confirmDeletion()) {
    await request(`/admin/content/comments/${deleteId}`, { method: "DELETE" });
    await Promise.all([loadSpotComments(state.editingSpotId), loadData()]);
    showToast("互动留言已删除");
  }
});

$("#addSpotCommentBtn").addEventListener("click", () => {
  if (!state.editingSpotId) return;
  fillCommentForm();
  const form = $("#commentForm");
  form.elements.spot_id.value = String(state.editingSpotId);
  form.elements.user_id.value = String(state.users[0]?.id || "");
  $("#commentDialog").showModal();
});

$("#childPointsList").addEventListener("click", async (event) => {
  const deleteId = event.target.dataset.deleteChildPoint;
  if (!deleteId || !state.editingSpotId || !confirmDeletion()) return;
  await request(`/admin/spots/${state.editingSpotId}/child-points/${deleteId}`, {
    method: "DELETE",
  });
  await refreshCurrentSpotChildPoints();
  showToast("子景点已删除");
});

$("#accountSettingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    username: data.username.trim(),
  };
  if (data.new_password) {
    if (!data.current_password) {
      showToast("请输入当前密码");
      return;
    }
    if (data.current_password === data.new_password) {
      showToast("两次密码不能相同");
      return;
    }
    payload.current_password = data.current_password;
    payload.new_password = data.new_password;
  }
  state.admin = await request("/admin/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  renderAdminInfo();
  $("#accountSettingsDialog").close();
  showToast("账号设置已保存");
});

$("#spotForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    ...data,
    latitude: Number(data.latitude),
    longitude: Number(data.longitude),
    river_name: data.river_name || null,
    river_upstream_latitude: data.river_upstream_latitude ? Number(data.river_upstream_latitude) : null,
    river_upstream_longitude: data.river_upstream_longitude ? Number(data.river_upstream_longitude) : null,
    recommendation_level: Number(data.recommendation_level),
    required_explore_points: Number(data.required_explore_points),
    checkin_radius_meters: Number(data.checkin_radius_meters),
    is_active: form.elements.is_active.checked,
    tag_ids: getSelectedSpotTagIds(),
  };

  const path = state.editingSpotId ? `/admin/spots/${state.editingSpotId}` : "/admin/spots";
  const method = state.editingSpotId ? "PATCH" : "POST";
  await request(path, { method, body: JSON.stringify(payload) });
  $("#spotDialog").close();
  await loadData();
  showToast("秘境已保存");
});

$("#uploadSpotImageBtn").addEventListener("click", async () => {
  if (!state.editingSpotId) {
    showToast("请先保存秘境，再上传媒体");
    return;
  }
  const file = $("#spotImageFile").files[0];
  if (!file) {
    showToast("请选择图片或视频");
    return;
  }
  const validation = validateUploadFile(file, true);
  if (!validation.valid) {
    showToast(validation.message);
    return;
  }
  if (validation.isVideo && $("#spotImageCover").checked) {
    showToast("视频不能设为封面");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("caption", $("#spotImageCaption").value);
  formData.append("sort_order", $("#spotImageSort").value || "0");
  formData.append("is_cover", $("#spotImageCover").checked ? "true" : "false");

  await uploadWithProgress(`${API}/admin/content/spots/${state.editingSpotId}/images`, formData, "#spotImageFileStatus");
  $("#spotImageFile").value = "";
  $("#spotImageCaption").value = "";
  $("#spotImageCover").checked = false;
  updateUploadFileStatus("#spotImageFile", "#spotImageFileStatus", "#clearSpotImageFileBtn", true);
  setUploadStatus("#spotImageFileStatus", t("上传完成"), "ok");
  await loadSpotImages(state.editingSpotId);
  showToast("媒体已上传");
});

$("#addChildPointBtn").addEventListener("click", async () => {
  if (!state.editingSpotId) {
    showToast("请先保存秘境，再新增子景点");
    return;
  }
  const name = $("#childPointName").value.trim();
  const latitude = $("#childPointLatitude").value;
  const longitude = $("#childPointLongitude").value;
  if (!name || !latitude || !longitude) {
    showToast("请填写点位名称、纬度和经度");
    return;
  }
  await request(`/admin/spots/${state.editingSpotId}/child-points`, {
    method: "POST",
    body: JSON.stringify({
      name,
      latitude: Number(latitude),
      longitude: Number(longitude),
      note: $("#childPointNote").value.trim() || null,
      fetch_weather: $("#childPointWeather").checked,
      sort_order: Number($("#childPointSort").value || 0),
      is_active: true,
    }),
  });
  clearChildPointForm();
  await refreshCurrentSpotChildPoints();
  showToast("子景点已新增");
});

[
  ["#spotImageFile", "#spotImageFileStatus", "#clearSpotImageFileBtn", true],
  ["#travelNoteImageFile", "#travelNoteImageFileStatus", "#clearTravelNoteImageFileBtn", true],
  ["#commentImageFile", "#commentImageFileStatus", "#clearCommentImageFileBtn", true],
  ["#recommendationImageFile", "#recommendationImageFileStatus", "#clearRecommendationImageFileBtn", true],
].forEach(([fileSelector, statusSelector, clearSelector, allowVideo]) => {
  const input = $(fileSelector);
  const button = $(clearSelector);
  if (input) {
    input.addEventListener("change", () => {
      updateUploadFileStatus(fileSelector, statusSelector, clearSelector, allowVideo);
    });
  }
  if (button) {
    button.addEventListener("click", () => {
      clearUploadFile(fileSelector, statusSelector, clearSelector);
    });
  }
});

$("#uploadTravelNoteImageBtn").addEventListener("click", () => {
  uploadImageTo("travel-notes", "#travelNoteImageFile", "#travelNoteForm", "image_url", true, "#travelNoteMediaPreview");
});

$("#deleteTravelNoteMediaBtn").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  deleteFormMedia("#travelNoteForm", "/admin/content/travel-notes", state.editingTravelNoteId, "#travelNoteImageFileStatus", "#travelNoteMediaPreview");
});

$("#uploadCommentImageBtn").addEventListener("click", () => {
  uploadImageTo("comments", "#commentImageFile", "#commentForm", "image_url", true, "#commentMediaPreview");
});

$("#deleteCommentMediaBtn").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  deleteFormMedia("#commentForm", "/admin/content/comments", state.editingCommentId, "#commentImageFileStatus", "#commentMediaPreview");
});

$("#uploadRecommendationImageBtn").addEventListener("click", () => {
  uploadImageTo("recommendations", "#recommendationImageFile", "#recommendationForm", "image_url", true, "#recommendationMediaPreview");
});

$("#deleteRecommendationMediaBtn").addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  deleteFormMedia("#recommendationForm", "/admin/content/recommendations", state.editingRecommendationId, "#recommendationImageFileStatus", "#recommendationMediaPreview");
});

[
  ["#travelNoteMediaPreview", "#travelNoteForm", "/admin/content/travel-notes", () => state.editingTravelNoteId, "#travelNoteImageFileStatus"],
  ["#commentMediaPreview", "#commentForm", "/admin/content/comments", () => state.editingCommentId, "#commentImageFileStatus"],
  ["#recommendationMediaPreview", "#recommendationForm", "/admin/content/recommendations", () => state.editingRecommendationId, "#recommendationImageFileStatus"],
].forEach(([previewSelector, formSelector, resourcePath, getEditingId, statusSelector]) => {
  const preview = $(previewSelector);
  if (!preview) return;
  preview.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete-form-media]");
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    deleteFormMedia(formSelector, resourcePath, getEditingId(), statusSelector, previewSelector);
  });
});

$("#tagForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    ...data,
    sort_order: Number(data.sort_order),
    is_active: form.elements.is_active.checked,
  };
  const path = state.editingTagId ? `/admin/tags/${state.editingTagId}` : "/admin/tags";
  const method = state.editingTagId ? "PATCH" : "POST";
  await request(path, { method, body: JSON.stringify(payload) });
  $("#tagDialog").close();
  await loadData();
  showToast("标签已保存");
});

$("#userForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    openid: String(data.openid || "").trim(),
    nickname: String(data.nickname || "").trim(),
    phone: data.phone || null,
    language: data.language,
    explore_points: Number(data.explore_points),
    checkin_count: Number(data.checkin_count),
    is_member: form.elements.is_member.checked,
    is_active: form.elements.is_active.checked,
    can_upload_image: form.elements.can_upload_image.checked,
    can_upload_video: form.elements.can_upload_video.checked,
    can_comment: form.elements.can_comment.checked,
    can_checkin: form.elements.can_checkin.checked,
  };
  const path = state.editingUserId ? `/admin/users/${state.editingUserId}` : "/admin/users";
  const method = state.editingUserId ? "PATCH" : "POST";
  try {
    await request(path, {
      method,
      body: JSON.stringify(payload),
    });
    if (!state.editingUserId) {
      state.pagination.users = { ...(state.pagination.users || {}), page: 1 };
    }
    $("#userDialog").close();
    await loadData();
    showToast("用户已保存");
  } catch (error) {
    showToast(`${t("保存失败")}：${error.message}`);
  }
});

$("#travelNoteForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    user_id: Number(data.user_id),
    spot_id: Number(data.spot_id),
    title: data.title,
    content: data.content,
    image_url: data.image_url || null,
    status: data.status,
    is_featured: form.elements.is_featured.checked,
  };
  const path = state.editingTravelNoteId
    ? `/admin/content/travel-notes/${state.editingTravelNoteId}`
    : "/admin/content/travel-notes";
  const method = state.editingTravelNoteId ? "PATCH" : "POST";
  await request(path, { method, body: JSON.stringify(payload) });
  $("#travelNoteDialog").close();
  await loadData();
  showToast("游记已保存");
});

$("#commentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    user_id: Number(data.user_id),
    spot_id: Number(data.spot_id),
    content: data.content,
    image_url: data.image_url || null,
    status: data.status,
  };
  const path = state.editingCommentId ? `/admin/content/comments/${state.editingCommentId}` : "/admin/content/comments";
  const method = state.editingCommentId ? "PATCH" : "POST";
  await request(path, { method, body: JSON.stringify(payload) });
  $("#commentDialog").close();
  await loadData();
  if (state.editingSpotId) await loadSpotComments(state.editingSpotId);
  showToast("留言已保存");
});

$("#passSettingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const markerColor = normalizeHexColor(form.elements.marker_color.value);
  const payload = {
    level: Number(form.elements.level.value),
    name_zh: data.name_zh,
    name_en: data.name_en,
    required_explore_points: Number(data.required_explore_points),
    checkin_points: Number(data.checkin_points),
    requires_membership: form.elements.requires_membership.checked,
    unlock_benefit_zh: data.unlock_benefit_zh,
    unlock_benefit_en: data.unlock_benefit_en,
    marker_color: markerColor,
    is_active: form.elements.is_active.checked,
  };
  const duplicateLevel = state.passSettings.find(
    (setting) => Number(setting.level) === payload.level && setting.id !== state.editingPassSettingId,
  );
  if (duplicateLevel) {
    showToast(t("通关等级不可重复"));
    return;
  }
  const path = state.editingPassSettingId ? `/admin/pass-settings/${state.editingPassSettingId}` : "/admin/pass-settings";
  const method = state.editingPassSettingId ? "PATCH" : "POST";
  try {
    const savedSetting = await request(path, {
      method,
      body: JSON.stringify(payload),
    });

    const updatedSetting = {
      ...savedSetting,
      marker_color: normalizeHexColor(savedSetting.marker_color || markerColor),
    };

    if (state.editingPassSettingId) {
      state.passSettings = state.passSettings.map((setting) =>
        setting.id === updatedSetting.id ? updatedSetting : setting,
      );
    } else {
      state.passSettings = [...state.passSettings, updatedSetting].sort((left, right) => left.level - right.level);
    }
    renderPassSettings();
    renderMetrics();
    $("#passSettingDialog").close();
    if (!state.editingPassSettingId) {
      state.pagination.passSettings = { ...(state.pagination.passSettings || {}), page: 1 };
    }
    try {
      await loadPassSettings();
    } catch (refreshError) {
      console.warn("Pass settings saved but could not be refreshed", refreshError);
    }
    showToast("通关设置已保存");
  } catch (error) {
    showToast(`${t("保存失败")}：${error.message}`);
  }
});

$("#membershipPlanForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    name_zh: data.name_zh,
    name_en: data.name_en,
    duration_days: Number(data.duration_days),
    price_cents: Number(data.price_cents),
    required_explore_points: Number(data.required_explore_points),
    benefits_zh: data.benefits_zh,
    benefits_en: data.benefits_en,
    is_active: form.elements.is_active.checked,
  };
  const path = state.editingMembershipPlanId
    ? `/admin/memberships/plans/${state.editingMembershipPlanId}`
    : "/admin/memberships/plans";
  const method = state.editingMembershipPlanId ? "PATCH" : "POST";
  await request(path, {
    method,
    body: JSON.stringify(payload),
  });
  $("#membershipPlanDialog").close();
  await loadData();
  showToast("会员套餐已保存");
});

$("#checkinForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  await request(`/admin/checkins/${state.editingCheckinId}/review`, {
    method: "PATCH",
    body: JSON.stringify({
      status: data.status,
      review_note: data.review_note || null,
    }),
  });
  $("#checkinDialog").close();
  await loadData();
  showToast("打卡审核已保存");
});

$("#recommendationForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    spot_id: Number(data.spot_id),
    category: data.category,
    name_zh: data.name_zh,
    name_en: data.name_en,
    summary_zh: data.summary_zh,
    summary_en: data.summary_en,
    city: data.city,
    county: data.county,
    address: data.address || null,
    contact: data.contact || null,
    image_url: data.image_url || null,
    price_level: data.price_level,
    recommendation_level: Number(data.recommendation_level),
    is_active: form.elements.is_active.checked,
  };
  const path = state.editingRecommendationId
    ? `/admin/content/recommendations/${state.editingRecommendationId}`
    : "/admin/content/recommendations";
  const method = state.editingRecommendationId ? "PATCH" : "POST";
  await request(path, { method, body: JSON.stringify(payload) });
  $("#recommendationDialog").close();
  await loadData();
  showToast("推荐已保存");
});

bootstrap();
