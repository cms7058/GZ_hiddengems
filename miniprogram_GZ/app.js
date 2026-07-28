const DEFAULT_USER = {
  id: null,
  openid: "",
  nickname: "微信用户",
  avatar_url: "",
  explore_points: 0,
  benefit_points: 0,
  checkin_count: 0,
  contribution_count: 0,
  eco_credit: 100,
  is_member: false,
  can_upload_image: false,
  can_upload_video: false,
  can_comment: false,
  can_checkin: false,
  can_recommend_spot: false,
  can_like_comment: false,
  can_share: false,
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
    // Old builds stored a hard-coded demo user without an OpenID. Never use it
    // as an authenticated account, otherwise its data can mask the real user.
    if (savedUser && savedUser.openid) {
      this.globalData.user = {
        ...this.globalData.user,
        ...savedUser,
      }
    }
    this.globalData.pendingReferrerToken = String(wx.getStorageSync("gzPendingReferrerToken") || "").trim()
    this.globalData.hasAcceptedSafetyAgreement = Boolean(wx.getStorageSync("gzSafetyAgreementAccepted"))
    this.globalData.hasAcceptedProfileAuth = Boolean(wx.getStorageSync("gzProfileAuthAccepted"))
    this.captureReferrerToken(options)
    this.bootstrapUser()
    preloadServiceHours().then(() => notifyServiceClosedIfNeeded())
  },

  onShow(options = {}) {
    const hasReferral = this.captureReferrerToken(options)
    const user = this.globalData.user || {}
    // A share can reopen a mini program already resident in memory. When the
    // recipient has not logged in yet, retry login with the retained token so
    // the registration is attributed to the inviter.
    if (hasReferral && !user.id && !this.globalData.userLoginPromise) {
      this.bootstrapUser({ force: true })
    }
  },

  captureReferrerToken(options = {}) {
    const token = String(options.query?.ref || "").trim()
    if (!token) return false
    this.globalData.pendingReferrerToken = token
    wx.setStorageSync("gzPendingReferrerToken", token)
    return true
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
            language: this.globalData.lang || "zh-CN",
          }
          // A normal launch/refresh only identifies the user. Do not send the
          // local placeholder nickname here, otherwise it overwrites a profile
          // the user previously saved on another launch or device.
          if (Object.prototype.hasOwnProperty.call(profile, "nickname")) {
            const nickname = (profile.nickname || "").trim()
            if (nickname) loginPayload.nickname = nickname
          }
          const referrerToken = String(profile.referrer_token || this.globalData.pendingReferrerToken || "").trim()
          if (referrerToken) loginPayload.referrer_token = referrerToken
          if (Object.prototype.hasOwnProperty.call(profile, "avatar_url")) {
            loginPayload.avatar_url = profile.avatar_url
          }
          miniLogin(loginPayload)
            .then((user) => {
              if (!user || !user.openid) {
                reject(new Error("mini login returned no openid"))
                return
              }
              this.globalData.user = {
                ...this.globalData.user,
                ...user,
              }
              this.globalData.pendingReferrerToken = ""
              wx.removeStorageSync("gzPendingReferrerToken")
              wx.setStorageSync("gzHiddenGemsUser", this.globalData.user)
              resolve(this.globalData.user)
            })
            .catch((error) => {
              console.warn("mini login failed", error)
              this.globalData.userLoginPromise = null
              if (profile.force) {
                reject(error)
                return
              }
              resolve(this.globalData.user)
            })
        },
        fail: (error) => {
          this.globalData.userLoginPromise = null
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
    pendingReferrerToken: "",
    device: {},
    window: {},
    lastTabPath: "pages/index/index",
  },
})
