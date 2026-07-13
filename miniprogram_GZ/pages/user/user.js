const app = getApp()

const COPY = {
  "zh-CN": {
    title: "用户",
    subtitle: "查看探秘积分、等级和解锁进度",
    points: "探秘积分",
    level: "探索等级",
    member: "会员状态",
    activeMember: "已开通",
    regular: "普通用户",
    checkins: "打卡次数",
    contributions: "贡献内容",
    permissions: "账号权限",
    uploadImage: "上传图片",
    uploadVideo: "上传视频",
    comment: "留言游记",
    checkin: "打卡通关",
    allowed: "允许",
    denied: "不允许",
    next: "下一阶段",
    tip: "完成打卡、发布优质游记后可继续累积探秘积分。",
    editProfile: "获取微信用户信息",
    nicknamePlaceholder: "请输入微信昵称",
    chooseAvatar: "选择头像",
    saveProfile: "保存资料",
    saved: "已保存",
  },
  "en-US": {
    title: "Profile",
    subtitle: "Track explore points, level, and unlock progress",
    points: "Explore Points",
    level: "Explorer Level",
    member: "Membership",
    activeMember: "Active",
    regular: "Regular",
    checkins: "Check-ins",
    contributions: "Contributions",
    permissions: "Permissions",
    uploadImage: "Upload Image",
    uploadVideo: "Upload Video",
    comment: "Notes/Comments",
    checkin: "Check-in/Pass",
    allowed: "Allowed",
    denied: "Denied",
    next: "Next Stage",
    tip: "Earn more points by completing check-ins and sharing useful notes.",
    editProfile: "Get WeChat Profile",
    nicknamePlaceholder: "Enter WeChat nickname",
    chooseAvatar: "Choose Avatar",
    saveProfile: "Save Profile",
    saved: "Saved",
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
  },

  onShow() {
    app.applyTabBarLanguage()
    const lang = app.globalData.lang || "zh-CN"
    this.setData({
      lang,
      copy: COPY[lang],
      user: app.globalData.user,
      avatarInitial: (app.globalData.user.nickname || "秘").slice(0, 1),
      profileForm: {
        nickname: app.globalData.user.nickname,
        avatar_url: app.globalData.user.avatar_url || "",
      },
    })
  },

  onChooseAvatar(event) {
    this.setData({
      "profileForm.avatar_url": event.detail.avatarUrl,
    })
  },

  onNicknameInput(event) {
    this.setData({
      "profileForm.nickname": event.detail.value,
    })
  },

  async onSaveProfile() {
    const nickname = (this.data.profileForm.nickname || "").trim() || this.data.user.nickname
    let nextUser = {
      ...app.globalData.user,
      nickname,
      avatar_url: this.data.profileForm.avatar_url,
    }
    nextUser = await app.bootstrapUser({
      force: true,
      nickname: nextUser.nickname,
      avatar_url: nextUser.avatar_url,
    })
    app.globalData.user = nextUser
    wx.setStorageSync("gzHiddenGemsUser", nextUser)
    this.setData({
      user: nextUser,
      avatarInitial: (nextUser.nickname || "秘").slice(0, 1),
    })
    wx.showToast({
      title: this.data.copy.saved,
      icon: "success",
    })
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
