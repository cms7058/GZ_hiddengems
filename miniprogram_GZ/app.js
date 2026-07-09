const DEFAULT_USER = {
  id: 1,
  nickname: "秘境探索者",
  avatar_url: "",
  explore_points: 80,
  explorer_level: 1,
  is_member: false,
}

App({
  onLaunch() {
    const savedUser = wx.getStorageSync("gzHiddenGemsUser")
    if (savedUser) {
      this.globalData.user = {
        ...this.globalData.user,
        ...savedUser,
      }
    }
    this.globalData.hasAcceptedSafetyAgreement = Boolean(wx.getStorageSync("gzSafetyAgreementAccepted"))
  },

  globalData: {
    lang: "zh-CN",
    hasAcceptedSafetyAgreement: false,
    currentSpot: null,
    user: DEFAULT_USER,
  },
})
