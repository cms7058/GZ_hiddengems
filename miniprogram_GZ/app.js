const DEFAULT_USER = {
  id: 1,
  nickname: "秘境探索者",
  avatar_url: "",
  explore_points: 80,
  explorer_level: 1,
  is_member: false,
}

const TAB_BAR_TEXT = {
  "zh-CN": ["首页", "小助手", "用户"],
  "en-US": ["Home", "Assistant", "Profile"],
}

App({
  onLaunch() {
    if (wx.hideShareMenu) {
      wx.hideShareMenu({
        menus: ["shareAppMessage", "shareTimeline"],
      })
    }
    if (wx.hideOptionMenu) {
      wx.hideOptionMenu()
    }
    const savedUser = wx.getStorageSync("gzHiddenGemsUser")
    if (savedUser) {
      this.globalData.user = {
        ...this.globalData.user,
        ...savedUser,
      }
    }
    this.globalData.hasAcceptedSafetyAgreement = Boolean(wx.getStorageSync("gzSafetyAgreementAccepted"))
  },

  setLanguage(lang) {
    this.globalData.lang = lang
    this.applyTabBarLanguage()
  },

  applyTabBarLanguage() {
    if (!wx.setTabBarItem) return
    const labels = TAB_BAR_TEXT[this.globalData.lang || "zh-CN"] || TAB_BAR_TEXT["zh-CN"]
    labels.forEach((text, index) => {
      wx.setTabBarItem({
        index,
        text,
      })
    })
  },

  globalData: {
    lang: "zh-CN",
    hasAcceptedSafetyAgreement: false,
    currentSpot: null,
    user: DEFAULT_USER,
  },
})
