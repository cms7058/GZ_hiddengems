const { isServiceClosedError, request } = require("../../utils/request")
const { chooseNavigationApp } = require("../../utils/navigation")

const app = getApp()

const CENTER = {
  latitude: 26.5982,
  longitude: 106.7074,
}

const DEFAULT_SCALE = 7
const MIN_SCALE = 5
const MAX_SCALE = 18

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
    resetMap: "默认",
    mysteryTitle: "神秘秘境等待探索",
    mysteryPrefix: "还有",
    mysterySuffix: "个神秘景点等待你去探索",
    nextUnlockPrefix: "还差",
    nextUnlockSuffix: "积分可以解锁下一个秘境",
    allUnlocked: "当前可探索秘境已全部解锁",
    profileTitle: "获取微信用户信息",
    profileBody: "用于同步你的昵称、头像和 OPENID，后台会根据用户权限自动开放上传、留言和打卡功能。",
    profileNicknamePlaceholder: "请输入微信昵称",
    profileAvatar: "选择微信头像",
    profileButton: "允许并继续",
    profileSkip: "暂不授权",
    profileFailed: "获取用户信息失败",
    serviceClosed: "后台数据服务开放时间为每天北京时间 08:00-24:00，请在开放时间内使用。",
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
    resetMap: "Reset",
    mysteryTitle: "Mystery gems ahead",
    mysteryPrefix: "There are ",
    mysterySuffix: " mystery spots waiting",
    nextUnlockPrefix: "Need ",
    nextUnlockSuffix: " more pts to unlock the next gem",
    allUnlocked: "All visible gems are unlocked",
    profileTitle: "Get WeChat Profile",
    profileBody: "Used to sync nickname, avatar, and OpenID. The admin permissions control uploads, comments, and check-ins.",
    profileNicknamePlaceholder: "Enter WeChat nickname",
    profileAvatar: "Choose WeChat Avatar",
    profileButton: "Allow and Continue",
    profileSkip: "Skip",
    profileFailed: "Failed to get profile",
    serviceClosed: "Data is available daily from 08:00 to 24:00 Beijing time.",
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
    scale: DEFAULT_SCALE,
    tags: [],
    selectedTagId: 0,
    spots: [],
    filteredSpots: [],
    markers: [],
    selectedSpot: null,
    selectedSpotId: 0,
    unlockHint: {
      hiddenCount: 0,
      nextNeed: 0,
    },
    userLocation: null,
    hasUserLocation: false,
    user: app.globalData.user,
    loading: true,
    offline: false,
    serviceClosed: false,
    profileAuthForm: {
      nickname: "",
      avatar_url: "",
    },
    showProfileAuth: false,
    showSafetyAgreement: false,
  },

  onLoad() {
    this.mapAutoFit = true
    this.hideShareMenu()
    this.handleLocationChange = (location) => this.updateUserLocation(location, false)
    this.refreshCopy()
    this.bootstrapLogin()
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

  onShow() {
    app.applyTabBarLanguage()
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

  async bootstrapLogin() {
    const user = await app.bootstrapUser()
    this.setData({ user })
    this.showNextAgreementStep()
    this.loadHomeData()
  },

  showNextAgreementStep() {
    const hasProfileAuth = app.globalData.hasAcceptedProfileAuth || wx.getStorageSync("gzProfileAuthAccepted")
    if (!hasProfileAuth) {
      this.setData({ showProfileAuth: true, showSafetyAgreement: false })
      return
    }
    this.setData({ showProfileAuth: false })
    this.checkSafetyAgreement()
  },

  async loadHomeData() {
    this.mapAutoFit = true
    this.setData({ loading: true })
    try {
      const tags = await request(`/tags?lang=${this.data.lang}`)
      const spots = await request(this.buildMapPath())
      this.setData({
        tags,
        spots: this.normalizeSpots(spots),
        offline: false,
        serviceClosed: false,
        loading: false,
      })
      this.applyFilters()
      this.loadWeatherSummaries()
    } catch (error) {
      if (isServiceClosedError(error)) {
        this.setData({
          tags: [],
          spots: [],
          filteredSpots: [],
          markers: [],
          selectedSpot: null,
          selectedSpotId: 0,
          unlockHint: { hiddenCount: 0, nextNeed: 0 },
          offline: false,
          serviceClosed: true,
          loading: false,
        })
        return
      }
      this.setData({
        tags: DEMO_TAGS,
        spots: DEMO_SPOTS,
        offline: true,
        serviceClosed: false,
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
    const weather = (safety && safety.weather) || {}
    if (!weather.text) return this.data.copy.weatherUnavailable
    const temp = weather.temp ? `${weather.temp}°C` : ""
    const humidity = weather.humidity ? `${weather.humidity}%` : ""
    return [weather.text, temp, humidity].filter(Boolean).join(" · ")
  },

  applyFilters(options = {}) {
    const selectedTagId = Number(this.data.selectedTagId)
    const taggedSpots = selectedTagId
      ? this.data.spots.filter((spot) => spot.tags.some((tag) => tag.id === selectedTagId))
      : this.data.spots
    const filteredSpots = taggedSpots.filter((spot) => this.canViewSpot(spot))
    const markers = this.buildMarkers(filteredSpots)
    const selectedSpotId = options.preserveSelection ? this.data.selectedSpotId : (filteredSpots[0] && filteredSpots[0].id) || 0
    const selectedSpot = filteredSpots.find((spot) => spot.id === selectedSpotId) || filteredSpots[0] || null
    this.setData({
      filteredSpots,
      markers,
      selectedSpot,
      selectedSpotId: (selectedSpot && selectedSpot.id) || 0,
      unlockHint: this.buildUnlockHint(taggedSpots),
    })
    this.fitMapToVisiblePoints(filteredSpots)
  },

  canViewSpot(spot) {
    const requiredPoints = Number(spot.required_explore_points || 0)
    const userPoints = Number(this.data.user.explore_points || 0)
    return spot.is_unlocked !== false && userPoints >= requiredPoints
  },

  buildUnlockHint(spots) {
    const userPoints = Number(this.data.user.explore_points || 0)
    const hiddenSpots = (spots || []).filter((spot) => !this.canViewSpot(spot))
    const nextNeed = hiddenSpots.reduce((minNeed, spot) => {
      const need = Math.max(Number(spot.required_explore_points || 0) - userPoints, 0)
      if (need <= 0) return minNeed
      return minNeed === 0 ? need : Math.min(minNeed, need)
    }, 0)
    return {
      hiddenCount: hiddenSpots.length,
      nextNeed,
    }
  },

  fitMapToVisiblePoints(spots) {
    if (!this.mapAutoFit) return

    const points = (spots || [])
      .filter((spot) => Number.isFinite(Number(spot.latitude)) && Number.isFinite(Number(spot.longitude)))
      .map((spot) => ({
        latitude: Number(spot.latitude),
        longitude: Number(spot.longitude),
      }))

    if (this.data.userLocation) {
      points.push({
        latitude: Number(this.data.userLocation.latitude),
        longitude: Number(this.data.userLocation.longitude),
      })
    }

    if (points.length === 0) return
    if (points.length === 1) {
      this.setData({
        center: points[0],
        scale: this.data.userLocation ? 11 : 8,
      })
      return
    }

    clearTimeout(this.fitMapTimer)
    this.fitMapTimer = setTimeout(() => {
      wx.createMapContext("gemsMap", this).includePoints({
        points,
        padding: [72, 48, 72, 48],
      })
    }, 80)
  },

  disableMapAutoFit() {
    this.mapAutoFit = false
    clearTimeout(this.fitMapTimer)
  },

  onMapRegionChange(event) {
    if (event.type !== "end") return
    if (event.causedBy === "scale" || event.causedBy === "drag") {
      this.disableMapAutoFit()
    }
  },

  onZoomIn() {
    this.adjustMapScale(1)
  },

  onZoomOut() {
    this.adjustMapScale(-1)
  },

  adjustMapScale(delta) {
    this.disableMapAutoFit()
    this.getCurrentMapScale((currentScale) => {
      const nextScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, currentScale + delta))
      this.setData({ scale: nextScale })
    })
  },

  getCurrentMapScale(callback) {
    const fallbackScale = Number(this.data.scale) || DEFAULT_SCALE
    const mapContext = wx.createMapContext("gemsMap", this)
    if (!mapContext.getScale) {
      callback(fallbackScale)
      return
    }

    mapContext.getScale({
      success: (res) => callback(Number(res.scale) || fallbackScale),
      fail: () => callback(fallbackScale),
    })
  },

  onResetMap() {
    this.mapAutoFit = true
    this.setData({ scale: DEFAULT_SCALE })
    this.fitMapToVisiblePoints(this.data.filteredSpots)
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
    this.mapAutoFit = true
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
    if (!this.canViewSpot(spot)) {
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

  hideShareMenu() {
    if (wx.hideShareMenu) {
      wx.hideShareMenu({
        menus: ["shareAppMessage", "shareTimeline"],
      })
    }
    if (wx.hideOptionMenu) {
      wx.hideOptionMenu()
    }
  },

  onLanguageTap() {
    app.setLanguage(this.data.lang === "zh-CN" ? "en-US" : "zh-CN")
    this.refreshCopy()
    this.mapAutoFit = true
    this.loadHomeData()
  },

  onAcceptSafetyAgreement() {
    wx.setStorageSync("gzSafetyAgreementAccepted", true)
    app.globalData.hasAcceptedSafetyAgreement = true
    this.setData({ showSafetyAgreement: false })
  },

  onSkipProfileAuth() {
    wx.setStorageSync("gzProfileAuthAccepted", true)
    app.globalData.hasAcceptedProfileAuth = true
    this.setData({ showProfileAuth: false })
    this.checkSafetyAgreement()
  },

  onProfileAvatar(event) {
    this.setData({ "profileAuthForm.avatar_url": event.detail.avatarUrl || "" })
  },

  onProfileNicknameInput(event) {
    this.setData({ "profileAuthForm.nickname": event.detail.value || "" })
  },

  async onAuthorizeProfile() {
    try {
      let userInfo = {
        nickName: this.data.profileAuthForm.nickname,
        avatarUrl: this.data.profileAuthForm.avatar_url,
      }
      if ((!userInfo.nickName || !userInfo.avatarUrl) && wx.getUserProfile) {
        try {
          const profile = await new Promise((resolve, reject) => {
            wx.getUserProfile({
              desc: this.data.copy.profileBody,
              success: resolve,
              fail: reject,
            })
          })
          userInfo = {
            nickName: userInfo.nickName || (profile.userInfo && profile.userInfo.nickName),
            avatarUrl: userInfo.avatarUrl || (profile.userInfo && profile.userInfo.avatarUrl),
          }
        } catch (error) {
          // Newer WeChat clients require chooseAvatar and nickname input; continue with entered values.
        }
      }
      const user = await app.bootstrapUser({
        force: true,
        nickname: userInfo.nickName,
        avatar_url: userInfo.avatarUrl,
      })
      wx.setStorageSync("gzProfileAuthAccepted", true)
      app.globalData.hasAcceptedProfileAuth = true
      this.setData({ user, showProfileAuth: false })
      this.checkSafetyAgreement()
      this.loadHomeData()
    } catch (error) {
      wx.showToast({ title: this.data.copy.profileFailed, icon: "none" })
    }
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
      hasUserLocation: true,
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
      chooseNavigationApp({
        spot,
        location,
        mapId: "gemsMap",
        page: this,
        lang: this.data.lang,
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
