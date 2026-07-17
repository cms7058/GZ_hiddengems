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
    need: "还需",
    points: "积分",
    description: "秘境介绍",
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
    points: "pts",
    description: "About This Gem",
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
    const imageUrls = (cached.images || []).map((image) => image.display_url || image.image_url).filter(Boolean)
    this.setData({
      spot: {
        ...cached,
        image_urls: imageUrls,
        description: cached.description || cached.summary || "",
        need_points: Math.max(Number(cached.required_explore_points || 0) - Number(cached.user_explore_points || 0), 0),
      },
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
      const spot = await request(`/spots/locked-preview/${this.spotId}?lang=${this.data.lang}&user_id=${user.id}`)
      const imageUrls = (spot.images || []).map((image) => image.display_url || image.image_url).filter(Boolean)
      this.setData({
        spot: {
          ...spot,
          image_urls: imageUrls,
          need_points: Math.max(Number(spot.required_explore_points || 0) - Number(spot.user_explore_points || 0), 0),
        },
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
