const { isServiceClosedError, request, resolveMediaUrl } = require("../../utils/request")

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
    imageLoading: "图片加载中",
    imageFailed: "图片暂时无法加载",
    searchPlaceholder: "搜索名称、简介或地点",
    tagFilter: "标签",
    regionFilter: "行政区",
    allRegions: "全部行政区",
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
    imageLoading: "Loading image",
    imageFailed: "Image unavailable",
    searchPlaceholder: "Search name, summary or place",
    tagFilter: "Tag",
    regionFilter: "Region",
    allRegions: "All regions",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    user: app.globalData.user,
    spots: [],
    allSpots: [],
    keyword: "",
    tagOptions: [{ id: 0, label: "全部标签" }],
    regionOptions: [{ key: "", label: "全部行政区" }],
    selectedTagIndex: 0,
    selectedRegionIndex: 0,
    loading: true,
    offline: false,
    serviceClosed: false,
    refreshing: false,
    summary: {
      tags: "",
      levels: "",
      count: 0,
    },
  },

  onLoad() {
    this.coverPathCache = {}
    this.hideShareMenu()
    this.refreshCopy()
    this.loadSpots()
  },

  onShow() {
    app.applyTabBarLanguage()
  },

  onLanguageChanged() {
    this.refreshCopy()
    this.loadSpots()
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
    const user = this.data.user || {}
    const params = [
      `lang=${this.data.lang}`,
      `explore_points=${user.explore_points}`,
      `is_member=${user.is_member ? "true" : "false"}`,
    ]
    if (user.id && user.openid) params.push(`user_id=${user.id}`)
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
      cover_image_url: resolveMediaUrl(spot.cover_image_url || ""),
      cover_display_url: spot.cover_display_url || "",
      cover_loading: typeof spot.cover_loading === "boolean" ? spot.cover_loading : Boolean(spot.cover_image_url),
      cover_failed: Boolean(spot.cover_failed),
      markerColor: /^#[0-9a-fA-F]{6}$/.test(spot.marker_color || "") ? spot.marker_color : "#2f6b4f",
    }))
  },

  canViewSpot(spot) {
    return spot.is_unlocked !== false
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
    const baseSpots = levelIds.length
      ? tagFiltered.filter((spot) => levelIds.includes(Number(spot.recommendation_level)))
      : tagFiltered
    const tagOptions = this.buildTagOptions(baseSpots)
    const regionOptions = this.buildRegionOptions(baseSpots)
    const currentTagId = Number((this.data.tagOptions[this.data.selectedTagIndex] || {}).id || 0)
    const currentRegionKey = (this.data.regionOptions[this.data.selectedRegionIndex] || {}).key || ""
    const selectedTagIndex = Math.max(0, tagOptions.findIndex((item) => Number(item.id) === currentTagId))
    const selectedRegionIndex = Math.max(0, regionOptions.findIndex((item) => item.key === currentRegionKey))
    const selectedTag = tagOptions[selectedTagIndex] || tagOptions[0]
    const selectedRegion = regionOptions[selectedRegionIndex] || regionOptions[0]
    const keyword = (this.data.keyword || "").trim().toLowerCase()
    const spots = baseSpots.filter((spot) => {
      if (Number(selectedTag?.id || 0) && !spot.tags.some((tag) => Number(tag.id) === Number(selectedTag.id))) return false
      if (selectedRegion?.key && `${spot.city || ""}|${spot.county || ""}` !== selectedRegion.key) return false
      if (!keyword) return true
      const searchable = [spot.name, spot.summary, spot.city, spot.county, ...spot.tags.map((tag) => tag.name)]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
      return searchable.includes(keyword)
    })
    this.setData({
      spots,
      allSpots: eligible,
      tagOptions,
      regionOptions,
      selectedTagIndex,
      selectedRegionIndex,
      loading: false,
      offline,
      serviceClosed: false,
      summary: {
        tags: tagNames.length ? tagNames.join(this.data.lang === "en-US" ? ", " : "、") : this.data.copy.allTags,
        levels: levelIds.length ? levelIds.slice().sort((a, b) => a - b).map((level) => `L${level}`).join("-") : this.data.copy.allLevels,
        count: spots.length,
      },
    }, () => this.prefetchCoverImages(spots))
  },

  prefetchCoverImages(spots) {
    const pending = (spots || []).filter((spot) => spot.cover_image_url && !spot.cover_display_url && !spot.cover_failed)
    const workerCount = Math.min(3, pending.length)
    for (let worker = 0; worker < workerCount; worker += 1) {
      const next = () => {
        const spot = pending.shift()
        if (!spot) return
        this.downloadCoverImage(spot).finally(next)
      }
      next()
    }
  },

  downloadCoverImage(spot) {
    const url = spot.cover_image_url
    const cachedPath = this.coverPathCache[url]
    if (cachedPath) {
      this.updateCoverById(spot.id, url, { cover_display_url: cachedPath, cover_loading: false, cover_failed: false })
      return Promise.resolve()
    }
    return new Promise((resolve) => {
      wx.downloadFile({
        url,
        success: (result) => {
          if (result.statusCode >= 200 && result.statusCode < 300 && result.tempFilePath) {
            this.coverPathCache[url] = result.tempFilePath
            this.updateCoverById(spot.id, url, { cover_display_url: result.tempFilePath, cover_loading: false, cover_failed: false })
          } else {
            this.updateCoverById(spot.id, url, { cover_loading: false, cover_failed: true })
          }
          resolve()
        },
        fail: () => {
          this.updateCoverById(spot.id, url, { cover_loading: false, cover_failed: true })
          resolve()
        },
      })
    })
  },

  buildTagOptions(spots) {
    const uniqueTags = new Map()
    spots.forEach((spot) => spot.tags.forEach((tag) => {
      if (tag && tag.id != null && !uniqueTags.has(Number(tag.id))) {
        uniqueTags.set(Number(tag.id), { id: Number(tag.id), label: tag.name || this.data.copy.allTags })
      }
    }))
    return [{ id: 0, label: this.data.copy.allTags }].concat(Array.from(uniqueTags.values()).sort((a, b) => a.label.localeCompare(b.label, "zh-CN")))
  },

  buildRegionOptions(spots) {
    const regions = new Map()
    spots.forEach((spot) => {
      const city = String(spot.city || "").trim()
      const county = String(spot.county || "").trim()
      if (!city && !county) return
      const key = `${city}|${county}`
      if (!regions.has(key)) regions.set(key, { key, label: county ? `${city} / ${county}` : city })
    })
    return [{ key: "", label: this.data.copy.allRegions }].concat(Array.from(regions.values()).sort((a, b) => a.label.localeCompare(b.label, "zh-CN")))
  },

  applyListFilters() {
    this.setFilteredSpots(this.data.allSpots || [], this.data.offline)
  },

  onKeywordInput(event) {
    this.setData({ keyword: event.detail.value || "" }, () => this.applyListFilters())
  },

  onTagPickerChange(event) {
    this.setData({ selectedTagIndex: Number(event.detail.value) || 0 }, () => this.applyListFilters())
  },

  onRegionPickerChange(event) {
    this.setData({ selectedRegionIndex: Number(event.detail.value) || 0 }, () => this.applyListFilters())
  },

  onSpotTap(event) {
    const spot = this.data.spots.find((item) => Number(item.id) === Number(event.currentTarget.dataset.id))
    if (!spot) return
    app.globalData.currentSpot = spot
    wx.navigateTo({ url: `/pages/spot-detail/spot-detail?id=${spot.id}` })
  },

  onCoverLoad(event) {
    this.updateCoverState(event.currentTarget.dataset.index, { cover_loading: false, cover_failed: false })
  },

  onCoverError(event) {
    this.updateCoverState(event.currentTarget.dataset.index, { cover_loading: false, cover_failed: true })
  },

  updateCoverState(index, patch) {
    const spotIndex = Number(index)
    if (!Number.isInteger(spotIndex) || !this.data.spots[spotIndex]) return
    Object.keys(patch).forEach((key) => this.setData({ [`spots[${spotIndex}].${key}`]: patch[key] }))
  },

  updateCoverById(id, url, patch) {
    const spotIndex = this.data.spots.findIndex((item) => Number(item.id) === Number(id) && item.cover_image_url === url)
    if (spotIndex >= 0) this.updateCoverState(spotIndex, patch)
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
