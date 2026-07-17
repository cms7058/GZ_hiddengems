const DEFAULT_USER = {
  id: 1,
  nickname: "秘境探索者",
  avatar_url: "",
  explore_points: 80,
  is_member: false,
  can_upload_image: true,
  can_upload_video: true,
  can_comment: true,
  can_checkin: true,
  can_recommend_spot: true,
  can_like_comment: true,
  can_share: true,
  safety_level: "general",
}

const { miniLogin, notifyServiceClosedIfNeeded, preloadServiceHours } = require("./utils/request")

const TAB_BAR_TEXT = {
  "zh-CN": ["首页", "小助手", "我的", "EN"],
  "en-US": ["Home", "Assistant", "My", "中"],
}

App({
  onLaunch(options = {}) {
    this.captureDeviceContext()
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
    this.bootstrapUser({ referrer_token: options.query?.ref || "" })
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
          const loginPayload = {
            code,
            nickname: profile.nickname || this.globalData.user.nickname,
            language: this.globalData.lang || "zh-CN",
          }
          if (profile.referrer_token) loginPayload.referrer_token = profile.referrer_token
          if (Object.prototype.hasOwnProperty.call(profile, "avatar_url")) {
            loginPayload.avatar_url = profile.avatar_url
          }
          miniLogin(loginPayload)
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
    const pages = getCurrentPages()
    const currentPage = pages[pages.length - 1]
    if (currentPage && typeof currentPage.onLanguageChanged === "function") {
      currentPage.onLanguageChanged(lang)
    }
  },

  toggleLanguage() {
    this.setLanguage(this.globalData.lang === "zh-CN" ? "en-US" : "zh-CN")
  },

  rememberTab(path) {
    if (path) this.globalData.lastTabPath = path
  },

  captureDeviceContext() {
    const fallback = wx.getSystemInfoSync ? wx.getSystemInfoSync() : {}
    try {
      this.globalData.device = wx.getDeviceInfo ? wx.getDeviceInfo() : fallback
    } catch (error) {
      this.globalData.device = fallback
    }
    try {
      this.globalData.window = wx.getWindowInfo ? wx.getWindowInfo() : fallback
    } catch (error) {
      this.globalData.window = fallback
    }
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
    lockedSpotDetailCache: {},
    lockedSpotListCache: [],
    lockedSpotListFilters: null,
    user: DEFAULT_USER,
    userLoginPromise: null,
    device: {},
    window: {},
    lastTabPath: "pages/index/index",
  },
})
