const { isServiceClosedError, request } = require("../../utils/request")

const app = getApp()

const COPY = {
  "zh-CN": {
    navTitle: "附近待解锁秘境",
    loading: "正在搜索附近秘境",
    empty: "该范围内暂无待解锁秘境",
    offline: "暂时无法获取附近待解锁秘境",
    serviceClosed: "后台数据服务开放时间为每天北京时间 08:00-24:00，请在开放时间内使用。",
    radius: "搜索范围",
    distance: "距离",
    need: "还需",
    points: "积分",
    protected: "为保护秘境，地图不展示未解锁点位。",
    noPhotos: "暂无公开照片",
  },
  "en-US": {
    navTitle: "Nearby Locked Gems",
    loading: "Searching nearby gems",
    empty: "No locked gems are available in this range",
    offline: "Nearby locked gems are unavailable",
    serviceClosed: "Data is available daily from 08:00 to 24:00 Beijing time.",
    radius: "Search range",
    distance: "Distance",
    need: "Need",
    points: "pts",
    protected: "Locked spot locations are not shown on the map.",
    noPhotos: "No public photos",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    spots: [],
    radiusKm: 0,
    loading: true,
    offline: false,
    serviceClosed: false,
    refreshing: false,
    catalogMode: false,
  },

  onLoad(options = {}) {
    this.hideShareMenu()
    this.catalogMode = options.mode === "catalog"
    this.refreshCopy()
    this.loadSpots()
  },

  onShow() {
    app.applyTabBarLanguage()
    if (this.data.lang !== (app.globalData.lang || "zh-CN")) {
      this.refreshCopy()
      this.loadSpots()
    }
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true })
    this.loadSpots().finally(() => {
      this.setData({ refreshing: false })
      wx.stopPullDownRefresh()
    })
  },

  refreshCopy() {
    const lang = app.globalData.lang || "zh-CN"
    this.setData({ lang, copy: COPY[lang] })
  },

  getSearch() {
    return app.globalData.lockedSpotSearch || null
  },

  async loadSpots() {
    if (this.catalogMode) {
      const spots = (app.globalData.lockedSpotListCache || []).map((spot) => ({
        ...spot,
        images: spot.images || [],
        image_urls: [],
        need_points: Math.max(Number(spot.required_explore_points || 0) - Number(spot.user_explore_points || 0), 0),
      }))
      this.setData({ spots, loading: false, offline: false, serviceClosed: false, radiusKm: 0, catalogMode: true })
      return
    }
    const search = this.getSearch()
    if (!search) {
      this.setData({ spots: [], loading: false, offline: true })
      return
    }
    const user = app.globalData.user || {}
    this.setData({ loading: true, offline: false, serviceClosed: false, radiusKm: Number(search.radiusKm) || 0 })
    try {
      const params = [
        `lang=${this.data.lang}`,
        `user_id=${user.id}`,
        `latitude=${search.latitude}`,
        `longitude=${search.longitude}`,
        `radius_km=${search.radiusKm}`,
      ]
      ;(search.tagIds || []).forEach((id) => params.push(`tag_ids=${Number(id)}`))
      ;(search.levelIds || []).forEach((level) => params.push(`level_ids=${Number(level)}`))
      const spots = (await request(`/spots/locked-nearby?${params.join("&")}`)).map((spot) => {
        const imageUrls = (spot.images || []).map((image) => image.display_url || image.image_url).filter(Boolean)
        return {
          ...spot,
          image_urls: imageUrls,
          need_points: Math.max(Number(spot.required_explore_points || 0) - Number(spot.user_explore_points || 0), 0),
        }
      })
      this.setData({ spots, loading: false })
    } catch (error) {
      if (isServiceClosedError(error)) {
        this.setData({ spots: [], loading: false, serviceClosed: true })
        return
      }
      this.setData({ spots: [], loading: false, offline: true })
    }
  },

  onPreviewImage(event) {
    const urls = event.currentTarget.dataset.urls || []
    const current = event.currentTarget.dataset.current
    if (urls.length) wx.previewImage({ current, urls })
  },

  onSpotTap(event) {
    const spotId = Number(event.currentTarget.dataset.id)
    if (!spotId) return
    const spot = this.data.spots.find((item) => Number(item.id) === spotId)
    if (spot) {
      app.globalData.lockedSpotDetailCache = {
        ...(app.globalData.lockedSpotDetailCache || {}),
        [spotId]: spot,
      }
    }
    wx.navigateTo({ url: `/pages/locked-spot-detail/locked-spot-detail?id=${spotId}` })
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
