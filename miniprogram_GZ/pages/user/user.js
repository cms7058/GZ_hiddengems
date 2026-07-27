const app = getApp()
const { isServiceClosedError, resolveMediaUrl, uploadMedia } = require("../../utils/request")

const COPY = {
  "zh-CN": {
    title: "我的",
    defaultAvatar: "旅",
    points: "积分权益",
    benefitPoints: "可用权益积分",
    member: "会员状态",
    activeMember: "已开通",
    regular: "普通用户",
    checkins: "打卡次数",
    warningShort: "警告",
    suspiciousShort: "可疑",
    watchShort: "关注",
    contributions: "贡献内容",
    ecoCredit: "环保信用",
    shares: "分享次数",
    referrals: "分享注册人数",
    approvedRecommendations: "推荐通过次数",
    likesReceived: "获赞次数",
    likesGiven: "点赞次数",
    accountInfo: "账号资料",
    openid: "OpenID",
    phone: "手机号",
    phoneVerified: "手机号认证",
    language: "语言",
    safetyLevel: "会员安全等级",
    accountStatus: "账号状态",
    active: "已启用",
    inactive: "已停用",
    verified: "已认证",
    notVerified: "未认证",
    general: "一般",
    risk: "风险",
    quality: "优质",
    permissions: "账号权限",
    uploadImage: "上传图片",
    uploadVideo: "上传视频",
    comment: "留言游记",
    checkin: "打卡通关",
    recommend: "推荐秘境",
    like: "留言点赞",
    share: "小程序分享",
    allowed: "允许",
    denied: "不允许",
    next: "下一阶段",
    tip: "完成打卡、发布优质游记后可继续累积探秘积分。",
    editProfile: "编辑",
    cancelEdit: "取消",
    editProfileTitle: "编辑用户信息",
    nicknamePlaceholder: "请输入微信昵称",
    chooseAvatar: "选择头像",
    saveProfile: "保存",
    saved: "已保存",
    saving: "保存中",
    avatarUploadFailed: "头像上传失败，请稍后重试",
  },
  "en-US": {
    title: "My Profile",
    defaultAvatar: "G",
    points: "Benefits",
    benefitPoints: "Available Points",
    member: "Membership",
    activeMember: "Active",
    regular: "Regular",
    checkins: "Check-ins",
    warningShort: "Warning",
    suspiciousShort: "Suspicious",
    watchShort: "Watch",
    contributions: "Contributions",
    ecoCredit: "Eco Credit",
    shares: "Shares",
    referrals: "Referral Sign-ups",
    approvedRecommendations: "Approved Recommendations",
    likesReceived: "Likes Received",
    likesGiven: "Likes Given",
    accountInfo: "Account Details",
    openid: "OpenID",
    phone: "Phone",
    phoneVerified: "Phone Verified",
    language: "Language",
    safetyLevel: "Safety Level",
    accountStatus: "Account Status",
    active: "Active",
    inactive: "Inactive",
    verified: "Verified",
    notVerified: "Not verified",
    general: "General",
    risk: "Risk",
    quality: "Quality",
    permissions: "Permissions",
    uploadImage: "Upload Image",
    uploadVideo: "Upload Video",
    comment: "Notes/Comments",
    checkin: "Check-in/Pass",
    recommend: "Recommend Gems",
    like: "Comment Likes",
    share: "Mini Program Sharing",
    allowed: "Allowed",
    denied: "Denied",
    next: "Next Stage",
    tip: "Earn more points by completing check-ins and sharing useful notes.",
    editProfile: "Edit",
    cancelEdit: "Cancel",
    editProfileTitle: "Edit profile",
    nicknamePlaceholder: "Enter WeChat nickname",
    chooseAvatar: "Choose Avatar",
    saveProfile: "Save",
    saved: "Saved",
    saving: "Saving",
    avatarUploadFailed: "Avatar upload failed. Try again later",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    user: app.globalData.user,
    avatarInitial: "秘",
    profileForm: {
      nickname: app.globalData.user.nickname,
      avatar_url: app.globalData.user.avatar_url || "",
    },
    avatarNeedsUpload: false,
    editing: false,
    syncError: "",
    saving: false,
    refreshing: false,
  },

  onShow() {
    app.rememberTab("pages/user/user")
    this.refreshUserView()
    // Account data such as permissions, balances, and redeemed benefits is
    // server-authoritative. Refresh it whenever the user returns to this tab.
    this.reloadUser()
  },

  refreshUserView() {
    app.applyTabBarLanguage()
    const lang = app.globalData.lang || "zh-CN"
    const copy = COPY[lang]
    const user = this.buildUserView(app.globalData.user, copy)
    this.setData({
      lang,
      copy,
      user,
      avatarInitial: (user.nickname || "秘").slice(0, 1),
      profileForm: {
        nickname: user.nickname,
        avatar_url: user.avatar_url || "",
      },
      avatarNeedsUpload: false,
    })
  },

  buildUserView(user = {}, copy = COPY["zh-CN"]) {
    const safetyLevel = user.safety_level || "general"
    const avatarUrl = resolveMediaUrl(user.avatar_display_url || user.avatar_url || "")
    return {
      ...user,
      safetyLevelLabel: copy[safetyLevel] || safetyLevel,
      // Refresh the image URL after a successful profile save so WeChat does
      // not keep displaying a previously cached avatar.
      avatarDisplayUrl: avatarUrl ? `${avatarUrl}${avatarUrl.includes("?") ? "&" : "?"}v=${Date.now()}` : "",
    }
  },

  onLanguageChanged() {
    this.refreshUserView()
  },

  onPullDownRefresh() {
    this.reloadUser()
  },

  onUserRefresh() {
    this.reloadUser()
  },

  reloadUser() {
    this.setData({ refreshing: true })
    app.bootstrapUser({ force: true })
      .then(() => this.setData({ syncError: "" }))
      .catch((error) => {
        console.warn("profile refresh failed", error)
        this.setData({ syncError: error.message || "后台用户数据同步失败" })
      })
      .finally(() => {
        this.refreshUserView()
        this.setData({ refreshing: false })
        wx.stopPullDownRefresh()
      })
  },

  onChooseAvatar(event) {
    this.setData({
      "profileForm.avatar_url": event.detail.avatarUrl,
      avatarNeedsUpload: true,
    })
  },

  onNicknameInput(event) {
    this.setData({
      "profileForm.nickname": event.detail.value,
    })
  },

  onToggleProfileEdit() {
    this.setData({
      editing: true,
      profileForm: {
        nickname: this.data.user.nickname || "",
        avatar_url: this.data.user.avatar_url || "",
      },
      avatarNeedsUpload: false,
    })
  },

  onCloseProfileEdit() {
    if (!this.data.saving) this.setData({ editing: false, avatarNeedsUpload: false })
  },

  onProfileModalTap() {},

  onOpenBenefits() {
    wx.navigateTo({ url: "/pages/benefits/benefits" })
  },

  onOpenCheckinHistory() {
    wx.navigateTo({ url: "/pages/checkin-history/checkin-history" })
  },

  async onSaveProfile() {
    if (this.data.saving) return
    const nickname = (this.data.profileForm.nickname || "").trim() || this.data.user.nickname
    this.setData({ saving: true })
    try {
      const profile = { force: true, nickname }
      if (this.data.avatarNeedsUpload && this.data.profileForm.avatar_url) {
        const uploaded = await uploadMedia(this.data.profileForm.avatar_url, "image", "avatar")
        const avatarUrl = uploaded.image_url || uploaded.media_url || ""
        if (!avatarUrl) throw new Error(this.data.copy.avatarUploadFailed)
        profile.avatar_url = avatarUrl
      }
      const nextUser = await app.bootstrapUser(profile)
      app.globalData.user = nextUser
      const displayUser = this.buildUserView(nextUser, this.data.copy)
      wx.setStorageSync("gzHiddenGemsUser", nextUser)
      this.setData({
        user: displayUser,
        avatarInitial: (nextUser.nickname || "秘").slice(0, 1),
        profileForm: { nickname: nextUser.nickname, avatar_url: nextUser.avatar_url || "" },
        avatarNeedsUpload: false,
        editing: false,
      }, () => this.refreshUserView())
      wx.showToast({ title: this.data.copy.saved, icon: "success" })
    } catch (error) {
      if (!isServiceClosedError(error)) {
        wx.showModal({
          title: this.data.copy.avatarUploadFailed,
          content: error.message || this.data.copy.avatarUploadFailed,
          showCancel: false,
        })
      }
    } finally {
      this.setData({ saving: false })
    }
  },

  onFloatingBackTap() {
    const goHome = () => wx.switchTab({ url: "/pages/index/index" })
    if (getCurrentPages().length > 1) {
      wx.navigateBack({ delta: 1, fail: goHome })
      return
    }
    goHome()
  },
})
