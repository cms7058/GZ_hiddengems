const { isServiceClosedError, request } = require("../../utils/request")

const app = getApp()

const COPY = {
  "zh-CN": {
    navTitle: "待解锁秘境详情",
    loading: "正在加载秘境资料",
    offline: "暂时无法获取秘境资料",
    serviceClosed: "后台数据服务开放时间为每天北京时间 08:00-24:00，请在开放时间内使用。",
    locked: "秘境待解锁",
    level: "秘境等级",
    need: "所需",
    available: "可用权益积分",
    points: "积分",
    unlock: "解锁",
    unlockTitle: "确认解锁",
    unlockSuccess: "秘境已解锁",
    unlockInsufficient: "可用权益积分不足",
    description: "秘境介绍（未解锁）",
    noPhotos: "暂无公开照片",
    protected: "为保护秘境，本页面不展示地图、坐标、距离或导航信息。",
  },
  "en-US": {
    navTitle: "Locked Gem Details",
    loading: "Loading gem information",
    offline: "Gem information is unavailable",
    serviceClosed: "Data is available daily from 08:00 to 24:00 Beijing time.",
    locked: "Locked Gem",
    level: "Gem Level",
    need: "Need",
    available: "Available benefit points",
    points: "pts",
    unlock: "Unlock",
    unlockTitle: "Confirm Unlock",
    unlockSuccess: "Gem unlocked",
    unlockInsufficient: "Not enough benefit points",
    description: "Locked Gem Introduction",
    noPhotos: "No public photos",
    protected: "To protect this gem, maps, coordinates, distance, and navigation are not shown here.",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    spot: null,
    loading: true,
    offline: false,
    serviceClosed: false,
    benefitPoints: 0,
    unlocking: false,
  },

  onLoad(options) {
    this.hideShareMenu()
    this.spotId = Number(options.id)
    this.refreshCopy()
    this.showCachedSpot()
    this.loadSpot()
  },

  onShow() {
    app.applyTabBarLanguage()
    if (this.data.lang !== (app.globalData.lang || "zh-CN")) {
      this.refreshCopy()
      this.loadSpot()
    }
  },

  onPullDownRefresh() {
    this.loadSpot().finally(() => wx.stopPullDownRefresh())
  },

  refreshCopy() {
    const lang = app.globalData.lang || "zh-CN"
    this.setData({ lang, copy: COPY[lang] })
  },

  showCachedSpot() {
    const cached = (app.globalData.lockedSpotDetailCache || {})[this.spotId]
    if (!cached) return false
    this.setData({
      spot: {
        ...cached,
        images: [],
        image_urls: [],
        description: cached.description || cached.summary || "",
        need_points: Number(cached.required_explore_points || 0),
      },
      benefitPoints: Number((app.globalData.user || {}).benefit_points || 0),
      loading: false,
      offline: false,
    })
    return true
  },

  async loadSpot() {
    const user = app.globalData.user || {}
    if (!this.spotId || !user.id) {
      this.setData({ loading: false, offline: true })
      return
    }
    const hasCachedSpot = this.showCachedSpot()
    this.setData({ loading: !hasCachedSpot, offline: false, serviceClosed: false })
    try {
      const [spot, benefits] = await Promise.all([
        request(`/spots/locked-preview/${this.spotId}?lang=${this.data.lang}&user_id=${user.id}`),
        request(`/benefits/me/${user.id}`),
      ])
      this.setData({
        spot: {
          ...spot,
          images: [],
          image_urls: [],
          need_points: Number(spot.required_explore_points || 0),
        },
        benefitPoints: Number(benefits.benefit_points || 0),
        loading: false,
      })
    } catch (error) {
      if (isServiceClosedError(error)) {
        this.setData({ spot: null, loading: false, serviceClosed: true })
        return
      }
      console.warn("locked spot detail request failed", error)
      if (hasCachedSpot) {
        this.setData({ loading: false, offline: false })
        return
      }
      this.setData({ spot: null, loading: false, offline: true })
    }
  },

  onPreviewImage(event) {
    const urls = event.currentTarget.dataset.urls || []
    const current = event.currentTarget.dataset.current
    if (urls.length) wx.previewImage({ current, urls })
  },

  onUnlockSpot() {
    const user = app.globalData.user || {}
    const spot = this.data.spot
    if (!user.id || !spot || this.data.unlocking) return
    const required = Number(spot.need_points || 0)
    const available = Number(this.data.benefitPoints || 0)
    if (available < required) {
      wx.showModal({
        title: this.data.copy.unlockInsufficient,
        content: `${this.data.copy.need} ${required} ${this.data.copy.points}，${this.data.copy.available} ${available} ${this.data.copy.points}`,
        showCancel: false,
      })
      return
    }
    wx.showModal({
      title: this.data.copy.unlockTitle,
      content: `${this.data.copy.need} ${required} ${this.data.copy.points}，${this.data.copy.available} ${available} ${this.data.copy.points}`,
      success: async (result) => {
        if (!result.confirm) return
        try {
          this.setData({ unlocking: true })
          const redemption = await request("/benefits/unlock-spot", {
            method: "POST",
            data: { user_id: user.id, spot_id: this.spotId },
          })
          const benefitPoints = Math.max(0, available - Number(redemption.points_cost || required))
          app.globalData.user = { ...user, benefit_points: benefitPoints }
          wx.setStorageSync("gzHiddenGemsUser", app.globalData.user)
          wx.showToast({ title: this.data.copy.unlockSuccess, icon: "success" })
          wx.redirectTo({ url: `/pages/spot-detail/spot-detail?id=${this.spotId}` })
        } catch (error) {
          wx.showModal({ title: this.data.copy.unlockInsufficient, content: error.message || "", showCancel: false })
        } finally {
          this.setData({ unlocking: false })
        }
      },
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

  hideShareMenu() {
    if (wx.hideShareMenu) wx.hideShareMenu({ menus: ["shareAppMessage", "shareTimeline"] })
    if (wx.hideOptionMenu) wx.hideOptionMenu()
  },
})
