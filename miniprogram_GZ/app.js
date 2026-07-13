const DEFAULT_USER = {
  id: 1,
  nickname: "秘境探索者",
  avatar_url: "",
  explore_points: 80,
  explorer_level: 1,
  is_member: false,
  can_upload_image: true,
  can_upload_video: true,
  can_comment: true,
  can_checkin: true,
}

const { miniLogin, notifyServiceClosedIfNeeded, preloadServiceHours } = require("./utils/request")

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
    this.globalData.hasAcceptedProfileAuth = Boolean(wx.getStorageSync("gzProfileAuthAccepted"))
    this.bootstrapUser()
    preloadServiceHours().then(() => notifyServiceClosedIfNeeded())
  },

  bootstrapUser(profile = {}) {
    if (this.globalData.userLoginPromise && !profile.force) return this.globalData.userLoginPromise
    const loginPromise = new Promise((resolve, reject) => {
      wx.login({
        success: ({ code }) => {
          if (!code) {
            if (profile.force) {
              reject(new Error("wx.login did not return code"))
              return
            }
            resolve(this.globalData.user)
            return
          }
          miniLogin({
            code,
            nickname: profile.nickname || this.globalData.user.nickname,
            avatar_url: profile.avatar_url || this.globalData.user.avatar_url,
            language: this.globalData.lang || "zh-CN",
          })
            .then((user) => {
              if (profile.force && (!user || !user.openid)) {
                reject(new Error("mini login returned no openid"))
                return
              }
              this.globalData.user = {
                ...this.globalData.user,
                ...user,
              }
              wx.setStorageSync("gzHiddenGemsUser", this.globalData.user)
              resolve(this.globalData.user)
            })
            .catch((error) => {
              console.warn("mini login failed", error)
              if (profile.force) {
                reject(error)
                return
              }
              resolve(this.globalData.user)
            })
        },
        fail: (error) => {
          if (profile.force) {
            reject(error)
            return
          }
          resolve(this.globalData.user)
        },
      })
    })
    if (!profile.force) {
      this.globalData.userLoginPromise = loginPromise
    }
    return loginPromise
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
    hasAcceptedProfileAuth: false,
    currentSpot: null,
    spotFilters: null,
    spotListCache: [],
    user: DEFAULT_USER,
    userLoginPromise: null,
  },
})
