const API = "/api/v1";

const state = {
  token: localStorage.getItem("gz_admin_token") || "",
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
  currentSpotImages: [],
  editingSpotId: null,
  editingTagId: null,
  editingUserId: null,
  editingPassSettingId: null,
  editingMembershipPlanId: null,
  editingCheckinId: null,
  editingRecommendationId: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 2400);
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
    throw new Error(data.detail || `请求失败 ${response.status}`);
  }
  return data;
}

function setAuthenticated(isAuthenticated) {
  $("#loginView").classList.toggle("hidden", isAuthenticated);
  $("#appView").classList.toggle("hidden", !isAuthenticated);
}

function statusPill(status) {
  const labels = {
    draft: "草稿",
    pending: "待审核",
    approved: "已通过",
    rejected: "已拒绝",
    hidden: "已隐藏",
  };
  const tone = status === "approved" ? "" : status === "rejected" ? "danger" : "warning";
  return `<span class="pill ${tone}">${labels[status] || status}</span>`;
}

function visibilityText(level) {
  return {
    public: "公开",
    member: "会员",
    protected: "保护",
    secret: "守护者",
  }[level] || level;
}

function activePill(active) {
  return active ? '<span class="pill">启用</span>' : '<span class="pill danger">停用</span>';
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
  $("#spotCount").textContent = state.spots.length;
  $("#approvedCount").textContent = state.spots.filter((spot) => spot.review_status === "approved").length;
  $("#tagCount").textContent = state.tags.length;
  $("#protectedCount").textContent = state.spots.filter((spot) => spot.visibility_level !== "public").length;
  $("#userCount").textContent = state.users.length;
  $("#passLevelCount").textContent = state.passSettings.length;
  $("#membershipPlanCount").textContent = state.membershipPlans.length;
  $("#pendingCheckinCount").textContent = state.checkins.filter((checkin) => checkin.status === "pending").length;
  $("#pendingCommunityCount").textContent =
    state.travelNotes.filter((note) => note.status === "pending").length +
    state.comments.filter((comment) => comment.status === "pending").length;
  $("#recommendationCount").textContent = state.recommendations.length;
}

function memberPill(isMember) {
  return isMember ? '<span class="pill">会员</span>' : '<span class="pill warning">普通</span>';
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
              <button class="small-btn danger" data-disable-tag="${tag.id}">停用</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderSpots() {
  $("#spotsTable").innerHTML = state.spots
    .map((spot) => {
      const tags = spot.tags.length
        ? spot.tags.map((tag) => `<span class="pill">${escapeHtml(tag.name)}</span>`).join("")
        : '<span class="muted">未设置</span>';
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
          <td>${statusPill(spot.review_status)}</td>
          <td>${activePill(spot.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-spot="${spot.id}">编辑</button>
              <button class="small-btn" data-review-spot="${spot.id}" data-review-status="approved">通过</button>
              <button class="small-btn" data-review-spot="${spot.id}" data-review-status="rejected">拒绝</button>
              <button class="small-btn danger" data-disable-spot="${spot.id}">停用</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderUsers() {
  $("#usersTable").innerHTML = state.users
    .map(
      (user) => `
        <tr>
          <td>
            <div class="cell-title">
              <strong>${escapeHtml(user.nickname)}</strong>
              <span class="muted">${escapeHtml(user.phone || "未绑定手机")}</span>
            </div>
          </td>
          <td>${escapeHtml(user.openid)}</td>
          <td>${escapeHtml(user.language)}</td>
          <td>L${user.explorer_level}</td>
          <td>
            <div class="cell-title">
              <span>打卡 ${user.checkin_count} / 贡献 ${user.contribution_count}</span>
              <span class="muted">环保信用 ${user.eco_credit}</span>
            </div>
          </td>
          <td>${memberPill(user.is_member)}</td>
          <td>${activePill(user.is_active)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-user="${user.id}">编辑</button>
              <button class="small-btn danger" data-toggle-user="${user.id}">${user.is_active ? "停用" : "启用"}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
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
              <span>打卡 ${setting.required_checkins} / 贡献 ${setting.required_contributions}</span>
              <span class="muted">环保信用 ${setting.required_eco_credit}</span>
            </div>
          </td>
          <td>${setting.requires_membership ? '<span class="pill warning">需要</span>' : '<span class="pill">不需要</span>'}</td>
          <td>
            <div class="cell-title">
              <span>${escapeHtml(setting.unlock_benefit_zh)}</span>
              <span class="muted">${escapeHtml(setting.unlock_benefit_en)}</span>
            </div>
          </td>
          <td>${activePill(setting.is_active)}</td>
          <td><button class="small-btn" data-edit-pass="${setting.id}">编辑</button></td>
        </tr>
      `,
    )
    .join("");
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
          <td>${plan.duration_days} 天</td>
          <td>¥${(plan.price_cents / 100).toFixed(2)}</td>
          <td>
            <div class="cell-title">
              <span>${escapeHtml(plan.benefits_zh)}</span>
              <span class="muted">${escapeHtml(plan.benefits_en)}</span>
            </div>
          </td>
          <td>${activePill(plan.is_active)}</td>
          <td><button class="small-btn" data-edit-plan="${plan.id}">编辑</button></td>
        </tr>
      `,
    )
    .join("");

  $("#membershipRecordsTable").innerHTML = state.membershipRecords
    .map(
      (record) => `
        <tr>
          <td>${escapeHtml(record.nickname)}</td>
          <td>${escapeHtml(record.plan_name_zh)}</td>
          <td>${record.status === "active" ? '<span class="pill">有效</span>' : '<span class="pill warning">非有效</span>'}</td>
          <td>${escapeHtml(record.started_at || "-")}</td>
          <td>${escapeHtml(record.expires_at || "-")}</td>
        </tr>
      `,
    )
    .join("");
}

function renderCheckins() {
  $("#checkinsTable").innerHTML = state.checkins
    .map(
      (checkin) => `
        <tr>
          <td>${escapeHtml(checkin.nickname)}</td>
          <td>${escapeHtml(checkin.spot_name_zh)}</td>
          <td>${escapeHtml(checkin.latitude || "-")}, ${escapeHtml(checkin.longitude || "-")}</td>
          <td>
            <div class="cell-title">
              <span>${escapeHtml(checkin.note || "-")}</span>
              <span class="muted">${escapeHtml(checkin.review_note || "")}</span>
            </div>
          </td>
          <td>${statusPill(checkin.status)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-edit-checkin="${checkin.id}">审核</button>
              <button class="small-btn" data-quick-checkin="${checkin.id}" data-checkin-status="approved">通过</button>
              <button class="small-btn danger" data-quick-checkin="${checkin.id}" data-checkin-status="rejected">拒绝</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function categoryText(category) {
  return {
    clothing: "衣",
    food: "食",
    hotel: "住",
    transport: "行",
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
          <td>${escapeHtml(note.nickname)}</td>
          <td>${escapeHtml(note.spot_name_zh || "-")}</td>
          <td>${statusPill(note.status)}</td>
          <td>${note.is_featured ? '<span class="pill">精选</span>' : '<span class="pill warning">普通</span>'}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-note-status="${note.id}" data-status="approved">通过</button>
              <button class="small-btn" data-note-status="${note.id}" data-status="hidden">隐藏</button>
              <button class="small-btn" data-note-feature="${note.id}">${note.is_featured ? "取消精选" : "设为精选"}</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");

  $("#commentsTable").innerHTML = state.comments
    .map(
      (comment) => `
        <tr>
          <td>${escapeHtml(comment.content)}</td>
          <td>${escapeHtml(comment.nickname)}</td>
          <td>${escapeHtml(comment.spot_name_zh || "-")}</td>
          <td>${statusPill(comment.status)}</td>
          <td>
            <div class="row-actions">
              <button class="small-btn" data-comment-status="${comment.id}" data-status="approved">通过</button>
              <button class="small-btn danger" data-comment-status="${comment.id}" data-status="hidden">隐藏</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
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
          <td>${escapeHtml(item.city)} / ${escapeHtml(item.county)}</td>
          <td>${escapeHtml(item.price_level)}</td>
          <td>${item.recommendation_level}</td>
          <td>${activePill(item.is_active)}</td>
          <td><button class="small-btn" data-edit-recommendation="${item.id}">编辑</button></td>
        </tr>
      `,
    )
    .join("");
}

function renderSpotImages() {
  $("#spotImagesList").innerHTML = state.currentSpotImages.length
    ? state.currentSpotImages
        .map(
          (image) => `
            <article class="image-item">
              <img class="image-thumb" src="${escapeHtml(image.image_url)}" alt="${escapeHtml(image.caption || "秘境图片")}" />
              <div class="cell-title">
                <strong>${escapeHtml(image.caption || "未填写说明")}</strong>
                <span class="muted">排序 ${image.sort_order} ${image.is_cover ? " / 封面" : ""}</span>
              </div>
              <div class="row-actions">
                <button class="small-btn" data-cover-image="${image.id}">设封面</button>
                <button class="small-btn danger" data-disable-image="${image.id}">停用</button>
              </div>
            </article>
          `,
        )
        .join("")
    : '<p class="muted">暂无图片</p>';
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
  ] = await Promise.all([
    request("/admin/tags"),
    request("/admin/spots"),
    request("/admin/users"),
    request("/admin/pass-settings"),
    request("/admin/memberships/plans"),
    request("/admin/memberships/records"),
    request("/admin/checkins"),
    request("/admin/content/travel-notes"),
    request("/admin/content/comments"),
    request("/admin/content/recommendations"),
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
  renderMetrics();
  renderTags();
  renderSpots();
  renderUsers();
  renderPassSettings();
  renderMemberships();
  renderCheckins();
  renderCommunity();
  renderRecommendations();
}

async function bootstrap() {
  if (!state.token) {
    setAuthenticated(false);
    return;
  }
  try {
    state.admin = await request("/admin/me");
    $("#adminInfo").textContent = `${state.admin.username} / ${state.admin.role}`;
    setAuthenticated(true);
    await loadData();
  } catch (error) {
    localStorage.removeItem("gz_admin_token");
    state.token = "";
    setAuthenticated(false);
  }
}

function formToObject(form) {
  const formData = new FormData(form);
  return Object.fromEntries(formData.entries());
}

function getSelectedSpotTagIds() {
  return $$("#spotTagChecks input:checked").map((input) => Number(input.value));
}

function fillSpotForm(spot = null) {
  const form = $("#spotForm");
  form.reset();
  state.editingSpotId = spot?.id || null;
  $("#spotDialogTitle").textContent = spot ? "编辑秘境" : "新增秘境";
  renderTagChecks(spot?.tag_ids || []);

  if (!spot) {
    state.currentSpotImages = [];
    renderSpotImages();
    form.elements.review_status.value = "draft";
    form.elements.visibility_level.value = "public";
    form.elements.recommendation_level.value = 1;
    form.elements.checkin_radius_meters.value = 300;
    form.elements.is_active.checked = true;
    return;
  }

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
    "visibility_level",
    "review_status",
    "recommendation_level",
    "checkin_radius_meters",
  ].forEach((field) => {
    form.elements[field].value = spot[field] ?? "";
  });
  form.elements.is_active.checked = Boolean(spot.is_active);
}

function fillTagForm(tag = null) {
  const form = $("#tagForm");
  form.reset();
  state.editingTagId = tag?.id || null;
  $("#tagDialogTitle").textContent = tag ? "编辑标签" : "新增标签";
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
  state.editingUserId = user.id;
  $("#userDialogTitle").textContent = `编辑用户：${user.nickname}`;
  [
    "nickname",
    "phone",
    "language",
    "explorer_level",
    "checkin_count",
    "contribution_count",
    "eco_credit",
  ].forEach((field) => {
    form.elements[field].value = user[field] ?? "";
  });
  form.elements.is_member.checked = Boolean(user.is_member);
  form.elements.is_active.checked = Boolean(user.is_active);
}

function fillPassSettingForm(setting) {
  const form = $("#passSettingForm");
  form.reset();
  state.editingPassSettingId = setting.id;
  $("#passSettingDialogTitle").textContent = `编辑通关设置：L${setting.level}`;
  [
    "name_zh",
    "name_en",
    "required_checkins",
    "required_contributions",
    "required_eco_credit",
    "unlock_benefit_zh",
    "unlock_benefit_en",
  ].forEach((field) => {
    form.elements[field].value = setting[field] ?? "";
  });
  form.elements.requires_membership.checked = Boolean(setting.requires_membership);
  form.elements.is_active.checked = Boolean(setting.is_active);
}

function fillMembershipPlanForm(plan) {
  const form = $("#membershipPlanForm");
  form.reset();
  state.editingMembershipPlanId = plan.id;
  $("#membershipPlanDialogTitle").textContent = `编辑会员套餐：${plan.name_zh}`;
  ["name_zh", "name_en", "duration_days", "price_cents", "benefits_zh", "benefits_en"].forEach((field) => {
    form.elements[field].value = plan[field] ?? "";
  });
  form.elements.is_active.checked = Boolean(plan.is_active);
}

function fillCheckinForm(checkin) {
  const form = $("#checkinForm");
  form.reset();
  state.editingCheckinId = checkin.id;
  $("#checkinDialogTitle").textContent = `审核：${checkin.nickname} / ${checkin.spot_name_zh}`;
  form.elements.status.value = checkin.status;
  form.elements.review_note.value = checkin.review_note || "";
}

function fillRecommendationForm(item = null) {
  const form = $("#recommendationForm");
  form.reset();
  state.editingRecommendationId = item?.id || null;
  $("#recommendationDialogTitle").textContent = item ? `编辑推荐：${item.name_zh}` : "新增推荐";
  if (!item) {
    form.elements.category.value = "food";
    form.elements.price_level.value = "mid";
    form.elements.recommendation_level.value = 1;
    form.elements.is_active.checked = true;
    return;
  }
  [
    "category",
    "name_zh",
    "name_en",
    "summary_zh",
    "summary_en",
    "city",
    "county",
    "address",
    "contact",
    "price_level",
    "recommendation_level",
  ].forEach((field) => {
    form.elements[field].value = item[field] ?? "";
  });
  form.elements.is_active.checked = Boolean(item.is_active);
}

async function loadSpotImages(spotId) {
  if (!spotId) {
    state.currentSpotImages = [];
    renderSpotImages();
    return;
  }
  state.currentSpotImages = await request(`/admin/content/spots/${spotId}/images`);
  renderSpotImages();
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
    $("#adminInfo").textContent = `${state.admin.username} / ${state.admin.role}`;
    setAuthenticated(true);
    await loadData();
  } catch (error) {
    $("#loginError").textContent = error.message;
  }
});

$("#logoutBtn").addEventListener("click", () => {
  localStorage.removeItem("gz_admin_token");
  state.token = "";
  setAuthenticated(false);
});

$("#refreshBtn").addEventListener("click", async () => {
  await loadData();
  showToast("已刷新");
});

$("#newSpotBtn").addEventListener("click", () => {
  fillSpotForm();
  $("#spotDialog").showModal();
});

$("#newTagBtn").addEventListener("click", () => {
  fillTagForm();
  $("#tagDialog").showModal();
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

$$(".nav-btn").forEach((button) => {
  button.addEventListener("click", () => {
    $$(".nav-btn").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $$(".panel-section").forEach((section) => section.classList.add("hidden"));
    $(`#${button.dataset.section}`).classList.remove("hidden");
  });
});

$("#spotsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editSpot;
  const reviewId = event.target.dataset.reviewSpot;
  const disableId = event.target.dataset.disableSpot;

  if (editId) {
    const spot = state.spots.find((item) => item.id === Number(editId));
    fillSpotForm(spot);
    await loadSpotImages(spot.id);
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

  if (disableId) {
    await request(`/admin/spots/${disableId}`, { method: "DELETE" });
    await loadData();
    showToast("秘境已停用");
  }
});

$("#tagsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editTag;
  const disableId = event.target.dataset.disableTag;

  if (editId) {
    const tag = state.tags.find((item) => item.id === Number(editId));
    fillTagForm(tag);
    $("#tagDialog").showModal();
  }

  if (disableId) {
    await request(`/admin/tags/${disableId}`, { method: "DELETE" });
    await loadData();
    showToast("标签已停用");
  }
});

$("#usersTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editUser;
  const toggleId = event.target.dataset.toggleUser;

  if (editId) {
    const user = state.users.find((item) => item.id === Number(editId));
    fillUserForm(user);
    $("#userDialog").showModal();
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
});

$("#passSettingsTable").addEventListener("click", (event) => {
  const editId = event.target.dataset.editPass;
  if (!editId) return;

  const setting = state.passSettings.find((item) => item.id === Number(editId));
  fillPassSettingForm(setting);
  $("#passSettingDialog").showModal();
});

$("#membershipPlansTable").addEventListener("click", (event) => {
  const editId = event.target.dataset.editPlan;
  if (!editId) return;

  const plan = state.membershipPlans.find((item) => item.id === Number(editId));
  fillMembershipPlanForm(plan);
  $("#membershipPlanDialog").showModal();
});

$("#checkinsTable").addEventListener("click", async (event) => {
  const editId = event.target.dataset.editCheckin;
  const quickId = event.target.dataset.quickCheckin;

  if (editId) {
    const checkin = state.checkins.find((item) => item.id === Number(editId));
    fillCheckinForm(checkin);
    $("#checkinDialog").showModal();
  }

  if (quickId) {
    await request(`/admin/checkins/${quickId}/review`, {
      method: "PATCH",
      body: JSON.stringify({
        status: event.target.dataset.checkinStatus,
        review_note: event.target.dataset.checkinStatus === "approved" ? "后台快速通过。" : "后台快速拒绝。",
      }),
    });
    await loadData();
    showToast("打卡审核已更新");
  }
});

$("#travelNotesTable").addEventListener("click", async (event) => {
  const statusId = event.target.dataset.noteStatus;
  const featureId = event.target.dataset.noteFeature;

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
});

$("#commentsTable").addEventListener("click", async (event) => {
  const statusId = event.target.dataset.commentStatus;
  if (!statusId) return;

  await request(`/admin/content/comments/${statusId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: event.target.dataset.status }),
  });
  await loadData();
  showToast("留言状态已更新");
});

$("#recommendationsTable").addEventListener("click", (event) => {
  const editId = event.target.dataset.editRecommendation;
  if (!editId) return;

  const item = state.recommendations.find((recommendation) => recommendation.id === Number(editId));
  fillRecommendationForm(item);
  $("#recommendationDialog").showModal();
});

$("#spotImagesList").addEventListener("click", async (event) => {
  const coverId = event.target.dataset.coverImage;
  const disableId = event.target.dataset.disableImage;

  if (coverId) {
    await request(`/admin/content/spot-images/${coverId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_cover: true, is_active: true }),
    });
    await loadSpotImages(state.editingSpotId);
    showToast("封面已更新");
  }

  if (disableId) {
    await request(`/admin/content/spot-images/${disableId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: false }),
    });
    await loadSpotImages(state.editingSpotId);
    showToast("图片已停用");
  }
});

$("#spotForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    ...data,
    latitude: Number(data.latitude),
    longitude: Number(data.longitude),
    recommendation_level: Number(data.recommendation_level),
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
    showToast("请先保存秘境，再上传图片");
    return;
  }
  const file = $("#spotImageFile").files[0];
  if (!file) {
    showToast("请选择图片");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("caption", $("#spotImageCaption").value);
  formData.append("sort_order", $("#spotImageSort").value || "0");
  formData.append("is_cover", $("#spotImageCover").checked ? "true" : "false");

  const response = await fetch(`${API}/admin/content/spots/${state.editingSpotId}/images`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${state.token}`,
    },
    body: formData,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "上传失败");
  }
  $("#spotImageFile").value = "";
  $("#spotImageCaption").value = "";
  $("#spotImageCover").checked = false;
  await loadSpotImages(state.editingSpotId);
  showToast("图片已上传");
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
    nickname: data.nickname,
    phone: data.phone || null,
    language: data.language,
    explorer_level: Number(data.explorer_level),
    checkin_count: Number(data.checkin_count),
    contribution_count: Number(data.contribution_count),
    eco_credit: Number(data.eco_credit),
    is_member: form.elements.is_member.checked,
    is_active: form.elements.is_active.checked,
  };
  await request(`/admin/users/${state.editingUserId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  $("#userDialog").close();
  await loadData();
  showToast("用户已保存");
});

$("#passSettingForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formToObject(form);
  const payload = {
    name_zh: data.name_zh,
    name_en: data.name_en,
    required_checkins: Number(data.required_checkins),
    required_contributions: Number(data.required_contributions),
    required_eco_credit: Number(data.required_eco_credit),
    requires_membership: form.elements.requires_membership.checked,
    unlock_benefit_zh: data.unlock_benefit_zh,
    unlock_benefit_en: data.unlock_benefit_en,
    is_active: form.elements.is_active.checked,
  };
  await request(`/admin/pass-settings/${state.editingPassSettingId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  $("#passSettingDialog").close();
  await loadData();
  showToast("通关设置已保存");
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
    benefits_zh: data.benefits_zh,
    benefits_en: data.benefits_en,
    is_active: form.elements.is_active.checked,
  };
  await request(`/admin/memberships/plans/${state.editingMembershipPlanId}`, {
    method: "PATCH",
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
    category: data.category,
    name_zh: data.name_zh,
    name_en: data.name_en,
    summary_zh: data.summary_zh,
    summary_en: data.summary_en,
    city: data.city,
    county: data.county,
    address: data.address || null,
    contact: data.contact || null,
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
