const { request } = require("../../utils/request")

const app = getApp()

const CENTER = {
  latitude: 26.5982,
  longitude: 106.7074,
}

const COPY = {
  "zh-CN": {
    navTitle: "夜郎秘境",
    langButton: "EN",
    allTags: "全部",
    points: "探秘积分",
    unlocked: "已解锁",
    locked: "待解锁",
    needPoints: "还需",
    pointsUnit: "积分",
    visible: "查看详情",
    lockedAction: "积分不足",
    empty: "暂无匹配秘境",
    loading: "加载中",
    offline: "当前显示示例点位",
    tagPrefix: "标签",
    weather: "实时天气",
    weatherUnavailable: "天气暂不可用",
    alertUnit: "条预警",
    locationPermission: "显示我的位置",
    goThere: "到这去",
    locationReady: "已显示当前位置",
    locationFailed: "定位失败，请检查权限",
    locationRequired: "请先允许位置权限",
  },
  "en-US": {
    navTitle: "Yelang Gems",
    langButton: "中",
    allTags: "All",
    points: "Explore Points",
    unlocked: "Unlocked",
    locked: "Locked",
    needPoints: "Need",
    pointsUnit: "pts",
    visible: "View",
    lockedAction: "Locked",
    empty: "No matching spots",
    loading: "Loading",
    offline: "Showing demo spots",
    tagPrefix: "Tags",
    weather: "Weather",
    weatherUnavailable: "Weather unavailable",
    alertUnit: "alerts",
    locationPermission: "Show My Location",
    goThere: "Go",
    locationReady: "Location shown",
    locationFailed: "Location failed",
    locationRequired: "Allow location first",
  },
}

const DEMO_TAGS = [
  { id: 1, name: "摄影", icon: "camera" },
  { id: 2, name: "徒步", icon: "footprints" },
  { id: 3, name: "露营", icon: "tent" },
  { id: 6, name: "低难度", icon: "leaf" },
]

const DEMO_SPOTS = [
  {
    id: 1,
    name: "加榜梯田晨雾点",
    summary: "适合清晨摄影的梯田观景点，云雾和村寨层次明显。",
    city: "黔东南州",
    county: "从江县",
    latitude: 25.7436,
    longitude: 108.5062,
    visibility_level: "public",
    required_explore_points: 0,
    user_explore_points: 80,
    is_unlocked: true,
    recommendation_level: 5,
    tags: [DEMO_TAGS[0], DEMO_TAGS[3]],
  },
  {
    id: 2,
    name: "乌蒙山隐秘露营地",
    summary: "适合有经验玩家的高海拔露营地，天气变化快。",
    city: "六盘水市",
    county: "盘州市",
    latitude: 26.1068,
    longitude: 104.6341,
    visibility_level: "protected",
    required_explore_points: 120,
    user_explore_points: 80,
    is_unlocked: false,
    recommendation_level: 4,
    tags: [DEMO_TAGS[1], DEMO_TAGS[2]],
  },
]

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    center: CENTER,
    scale: 7,
    tags: [],
    selectedTagId: 0,
    spots: [],
    filteredSpots: [],
    markers: [],
    selectedSpot: null,
    selectedSpotId: 0,
    userLocation: null,
    user: app.globalData.user,
    loading: true,
    offline: false,
    showSafetyAgreement: false,
  },

  onLoad() {
    this.handleLocationChange = (location) => this.updateUserLocation(location, false)
    this.refreshCopy()
    this.checkSafetyAgreement()
    this.loadHomeData()
    this.tryShowUserLocation()
  },

  onUnload() {
    if (this.handleLocationChange && wx.offLocationChange) {
      wx.offLocationChange(this.handleLocationChange)
    }
  },

  onPullDownRefresh() {
    this.loadHomeData().finally(() => wx.stopPullDownRefresh())
  },

  refreshCopy() {
    const lang = app.globalData.lang || "zh-CN"
    this.setData({
      lang,
      copy: COPY[lang],
      user: app.globalData.user,
    })
  },

  checkSafetyAgreement() {
    const accepted = app.globalData.hasAcceptedSafetyAgreement || wx.getStorageSync("gzSafetyAgreementAccepted")
    this.setData({ showSafetyAgreement: !accepted })
  },

  async loadHomeData() {
    this.setData({ loading: true })
    try {
      const tags = await request(`/tags?lang=${this.data.lang}`)
      const spots = await request(this.buildMapPath())
      this.setData({
        tags,
        spots: this.normalizeSpots(spots),
        offline: false,
        loading: false,
      })
      this.applyFilters()
      this.loadWeatherSummaries()
    } catch (error) {
      this.setData({
        tags: DEMO_TAGS,
        spots: DEMO_SPOTS,
        offline: true,
        loading: false,
      })
      this.applyFilters()
    }
  },

  buildMapPath() {
    const { user } = this.data
    const params = [
      `lang=${this.data.lang}`,
      `user_id=${user.id}`,
      `explore_points=${user.explore_points}`,
      `user_level=${user.explorer_level}`,
      `is_member=${user.is_member ? "true" : "false"}`,
    ]
    return `/spots/map?${params.join("&")}`
  },

  normalizeSpots(spots) {
    return (spots || []).map((spot) => ({
      ...spot,
      required_explore_points: spot.required_explore_points || 0,
      user_explore_points: spot.user_explore_points || this.data.user.explore_points || 0,
      is_unlocked: spot.is_unlocked !== false,
      tags: spot.tags || [],
      weatherSummary: spot.weatherSummary || "",
      weatherAlertCount: spot.weatherAlertCount || 0,
    }))
  },

  async loadWeatherSummaries() {
    const spots = this.data.spots || []
    if (this.data.offline || spots.length === 0) return

    const results = await Promise.all(
      spots.map(async (spot) => {
        try {
          const safety = await request(`/spots/${spot.id}/safety?lang=${this.data.lang}`)
          return {
            id: spot.id,
            weatherSummary: this.formatWeatherSummary(safety),
            weatherAlertCount: (safety.alerts || []).length,
          }
        } catch (error) {
          console.warn("load home weather failed", spot.id, error)
          return {
            id: spot.id,
            weatherSummary: this.data.copy.weatherUnavailable,
            weatherAlertCount: 0,
          }
        }
      })
    )

    const weatherById = results.reduce((map, item) => {
      map[item.id] = item
      return map
    }, {})
    const spotsWithWeather = this.data.spots.map((spot) => ({
      ...spot,
      ...(weatherById[spot.id] || {}),
    }))
    this.setData({ spots: spotsWithWeather })
    this.applyFilters({ preserveSelection: true })
  },

  formatWeatherSummary(safety) {
    const weather = safety?.weather || {}
    if (!weather.text) return this.data.copy.weatherUnavailable
    const temp = weather.temp ? `${weather.temp}°C` : ""
    const humidity = weather.humidity ? `${weather.humidity}%` : ""
    return [weather.text, temp, humidity].filter(Boolean).join(" · ")
  },

  applyFilters(options = {}) {
    const selectedTagId = Number(this.data.selectedTagId)
    const filteredSpots = selectedTagId
      ? this.data.spots.filter((spot) => spot.tags.some((tag) => tag.id === selectedTagId))
      : this.data.spots
    const markers = this.buildMarkers(filteredSpots)
    const selectedSpotId = options.preserveSelection ? this.data.selectedSpotId : filteredSpots[0]?.id || 0
    const selectedSpot = filteredSpots.find((spot) => spot.id === selectedSpotId) || filteredSpots[0] || null
    this.setData({
      filteredSpots,
      markers,
      selectedSpot,
      selectedSpotId: selectedSpot?.id || 0,
    })
  },

  buildMarkers(spots) {
    const markers = spots.map((spot) => this.spotToMarker(spot))
    if (this.data.userLocation) {
      markers.push({
        id: 999999,
        latitude: this.data.userLocation.latitude,
        longitude: this.data.userLocation.longitude,
        width: 26,
        height: 26,
        callout: {
          content: this.data.lang === "en-US" ? "You are here" : "我的位置",
          color: "#ffffff",
          fontSize: 12,
          borderRadius: 8,
          bgColor: "#1f5f45",
          padding: 8,
          display: "ALWAYS",
        },
      })
    }
    return markers
  },

  spotToMarker(spot) {
    const locked = !spot.is_unlocked
    return {
      id: spot.id,
      latitude: spot.latitude,
      longitude: spot.longitude,
      width: 34,
      height: 34,
      callout: {
        content: `${locked ? "🔒 " : ""}${spot.name}`,
        color: locked ? "#7b6651" : "#1d3f31",
        fontSize: 13,
        borderRadius: 8,
        bgColor: locked ? "#fff2d8" : "#e7f3e8",
        padding: 8,
        display: "BYCLICK",
      },
      label: {
        content: locked ? "锁" : `${spot.recommendation_level}`,
        color: "#ffffff",
        fontSize: 12,
        bgColor: locked ? "#9a6a43" : "#2f6b4f",
        borderRadius: 12,
        padding: 6,
      },
    }
  },

  onTagTap(event) {
    this.setData({ selectedTagId: Number(event.currentTarget.dataset.id) })
    this.applyFilters()
  },

  onMarkerTap(event) {
    if (event.markerId === 999999) return
    const spot = this.data.filteredSpots.find((item) => item.id === event.markerId)
    if (spot) {
      this.setData({ selectedSpot: spot, selectedSpotId: spot.id })
      this.openSpotDetail(spot)
    }
  },

  onSpotTap(event) {
    const spot = this.data.filteredSpots.find((item) => item.id === Number(event.currentTarget.dataset.id))
    if (!spot) return
    this.openSpotDetail(spot)
  },

  openSpotDetail(spot) {
    if (!spot.is_unlocked) {
      const need = Math.max((spot.required_explore_points || 0) - (this.data.user.explore_points || 0), 0)
      wx.showToast({
        title: `${this.data.copy.needPoints} ${need} ${this.data.copy.pointsUnit}`,
        icon: "none",
      })
      return
    }
    app.globalData.currentSpot = spot
    wx.navigateTo({
      url: `/pages/spot-detail/spot-detail?id=${spot.id}`,
    })
  },

  onLanguageTap() {
    app.globalData.lang = this.data.lang === "zh-CN" ? "en-US" : "zh-CN"
    this.refreshCopy()
    this.loadHomeData()
  },

  onAcceptSafetyAgreement() {
    wx.setStorageSync("gzSafetyAgreementAccepted", true)
    app.globalData.hasAcceptedSafetyAgreement = true
    this.setData({ showSafetyAgreement: false })
  },

  async tryShowUserLocation() {
    try {
      const location = await this.getLocation()
      this.updateUserLocation(location)
      this.startLocationWatch()
    } catch (error) {
      console.warn("initial location skipped", error)
    }
  },

  updateUserLocation(location, recenter = true) {
    this.setData({
      userLocation: {
        latitude: location.latitude,
        longitude: location.longitude,
      },
      ...(recenter
        ? {
            center: {
              latitude: location.latitude,
              longitude: location.longitude,
            },
            scale: 11,
          }
        : {}),
    })
    this.applyFilters({ preserveSelection: true })
  },

  startLocationWatch() {
    if (!wx.startLocationUpdate || !wx.onLocationChange || this.locationWatcherStarted) return
    wx.startLocationUpdate({
      type: "gcj02",
      success: () => {
        this.locationWatcherStarted = true
        wx.onLocationChange(this.handleLocationChange)
      },
    })
  },

  async onAuthorizeLocation() {
    try {
      const location = await this.getLocation()
      this.updateUserLocation(location)
      this.startLocationWatch()
      wx.showToast({ title: this.data.copy.locationReady, icon: "none" })
    } catch (error) {
      wx.showToast({ title: this.data.copy.locationFailed, icon: "none" })
    }
  },

  getLocation() {
    return new Promise((resolve, reject) => {
      wx.getLocation({
        type: "gcj02",
        success: resolve,
        fail: reject,
      })
    })
  },

  async onNavigateTap(event) {
    const spot = this.data.filteredSpots.find((item) => item.id === Number(event.currentTarget.dataset.id))
    if (!spot) return
    try {
      const location = this.data.userLocation || (await this.getLocation())
      this.updateUserLocation(location)
      this.startLocationWatch()
      wx.openLocation({
        latitude: Number(spot.latitude),
        longitude: Number(spot.longitude),
        name: spot.name,
        address: [spot.city, spot.county, spot.summary].filter(Boolean).join(" "),
        scale: 16,
      })
    } catch (error) {
      wx.showModal({
        title: this.data.copy.locationRequired,
        content: this.data.copy.locationFailed,
        confirmText: this.data.lang === "en-US" ? "Settings" : "去设置",
        success: (res) => {
          if (res.confirm) wx.openSetting()
        },
      })
    }
  },
})
