const { isServiceClosedError, request } = require("../../utils/request")

const app = getApp()

const COPY = {
  "zh-CN": {
    navTitle: "秘境列表",
    loading: "加载中",
    empty: "当前筛选条件下暂无已解锁秘境",
    offline: "当前显示首页缓存数据",
    serviceClosed: "后台数据服务开放时间为每天北京时间 08:00-24:00，请在开放时间内使用。",
    selected: "当前筛选",
    allTags: "全部标签",
    allLevels: "全部等级",
    countSuffix: "个秘境",
    points: "积分",
  },
  "en-US": {
    navTitle: "Gem List",
    loading: "Loading",
    empty: "No unlocked gems match these filters",
    offline: "Showing cached home results",
    serviceClosed: "Data is available daily from 08:00 to 24:00 Beijing time.",
    selected: "Filters",
    allTags: "All Tags",
    allLevels: "All Levels",
    countSuffix: " gems",
    points: "pts",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    user: app.globalData.user,
    spots: [],
    loading: true,
    offline: false,
    serviceClosed: false,
    summary: {
      tags: "",
      levels: "",
      count: 0,
    },
  },

  onLoad() {
    this.hideShareMenu()
    this.refreshCopy()
    this.loadSpots()
  },

  onShow() {
    app.applyTabBarLanguage()
  },

  onPullDownRefresh() {
    this.loadSpots().finally(() => wx.stopPullDownRefresh())
  },

  refreshCopy() {
    const lang = app.globalData.lang || "zh-CN"
    this.setData({
      lang,
      copy: COPY[lang],
      user: app.globalData.user,
    })
  },

  getFilters() {
    const filters = app.globalData.spotFilters || {}
    return {
      tagIds: (filters.tagIds || []).map(Number),
      levelIds: (filters.levelIds || []).map(Number),
    }
  },

  buildMapPath() {
    const user = this.data.user
    const params = [
      `lang=${this.data.lang}`,
      `user_id=${user.id}`,
      `explore_points=${user.explore_points}`,
      `user_level=${user.explorer_level}`,
      `is_member=${user.is_member ? "true" : "false"}`,
    ]
    return `/spots/map?${params.join("&")}`
  },

  async loadSpots() {
    this.setData({ loading: true, serviceClosed: false })
    try {
      const spots = this.normalizeSpots(await request(this.buildMapPath()))
      this.setFilteredSpots(spots, false)
    } catch (error) {
      if (isServiceClosedError(error)) {
        this.setData({
          spots: [],
          loading: false,
          offline: false,
          serviceClosed: true,
        })
        return
      }
      this.setFilteredSpots(app.globalData.spotListCache || [], true)
    }
  },

  normalizeSpots(spots) {
    return (spots || []).map((spot) => ({
      ...spot,
      tags: spot.tags || [],
      required_explore_points: Number(spot.required_explore_points || 0),
      is_unlocked: spot.is_unlocked !== false,
      markerColor: /^#[0-9a-fA-F]{6}$/.test(spot.marker_color || "") ? spot.marker_color : "#2f6b4f",
    }))
  },

  canViewSpot(spot) {
    return spot.is_unlocked !== false && Number(this.data.user.explore_points || 0) >= Number(spot.required_explore_points || 0)
  },

  setFilteredSpots(allSpots, offline) {
    const { tagIds, levelIds } = this.getFilters()
    const tagNames = []
    const eligible = this.normalizeSpots(allSpots).filter((spot) => this.canViewSpot(spot))
    const tagFiltered = tagIds.length
      ? eligible.filter((spot) => spot.tags.some((tag) => tagIds.includes(Number(tag.id))))
      : eligible
    tagFiltered.forEach((spot) => {
      spot.tags.forEach((tag) => {
        if (tagIds.includes(Number(tag.id)) && !tagNames.includes(tag.name)) tagNames.push(tag.name)
      })
    })
    const spots = levelIds.length
      ? tagFiltered.filter((spot) => levelIds.includes(Number(spot.recommendation_level)))
      : tagFiltered
    this.setData({
      spots,
      loading: false,
      offline,
      serviceClosed: false,
      summary: {
        tags: tagNames.length ? tagNames.join(this.data.lang === "en-US" ? ", " : "、") : this.data.copy.allTags,
        levels: levelIds.length ? levelIds.slice().sort((a, b) => a - b).map((level) => `L${level}`).join("-") : this.data.copy.allLevels,
        count: spots.length,
      },
    })
  },

  onSpotTap(event) {
    const spot = this.data.spots.find((item) => Number(item.id) === Number(event.currentTarget.dataset.id))
    if (!spot) return
    app.globalData.currentSpot = spot
    wx.navigateTo({ url: `/pages/spot-detail/spot-detail?id=${spot.id}` })
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
