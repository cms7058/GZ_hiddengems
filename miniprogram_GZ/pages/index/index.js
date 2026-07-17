const { isServiceClosedError, request } = require("../../utils/request")
const { chooseNavigationApp } = require("../../utils/navigation")
const { getMarkerIcon, normalizeMarkerColor } = require("../../utils/marker-icon")

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
    allLevels: "全部等级",
    levelOverview: "秘境等级",
    filterSummaryPrefix: "已选择",
    filterSummaryCountPrefix: "共",
    filterSummaryCountSuffix: "个秘境",
    radius: "搜索半径",
    radiusUnit: "公里",
    recommendSpot: "推荐秘境",
    searching: "正在搜索",
    noEligibleSpots: "当前条件下暂无已解锁秘境",
    points: "探秘积分",
    unlocked: "已解锁",
    locked: "待解锁",
    needPoints: "还需",
    pointsUnit: "积分",
    visible: "查看详情",
    lockedAction: "积分不足",
    empty: "暂无匹配秘境",
    loading: "加载中",
    offline: "后台数据暂不可用，请检查网络与小程序服务器域名配置。",
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
    profileButton: "微信授权获取",
    profileSkip: "暂不授权",
    profileFailed: "获取用户信息失败",
    profileDomainFailed: "小程序请求域名尚未配置。请在微信公众平台当前 AppID 的“服务器域名”中添加 https://hiddengems.pebs.tech 后重新编译。",
    serviceClosed: "后台数据服务开放时间为每天北京时间 08:00-24:00，请在开放时间内使用。",
  },
  "en-US": {
    navTitle: "Yelang Gems",
    langButton: "中",
    allTags: "All",
    allLevels: "All Levels",
    levelOverview: "Gem Levels",
    filterSummaryPrefix: "Selected",
    filterSummaryCountPrefix: "",
    filterSummaryCountSuffix: " gems",
    radius: "Search radius",
    radiusUnit: "km",
    recommendSpot: "Recommend a Gem",
    searching: "Searching",
    noEligibleSpots: "No unlocked gems match these filters",
    points: "Explore Points",
    unlocked: "Unlocked",
    locked: "Locked",
    needPoints: "Need",
    pointsUnit: "pts",
    visible: "View",
    lockedAction: "Locked",
    empty: "No matching spots",
    loading: "Loading",
    offline: "Backend data is unavailable. Check the network and mini program server-domain settings.",
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
    profileButton: "Use WeChat Profile",
    profileSkip: "Skip",
    profileFailed: "Failed to get profile",
    profileDomainFailed: "The mini program request domain is not configured. Add https://hiddengems.pebs.tech to Server Domains for the current AppID, then recompile.",
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
    selectedTagIds: [],
    selectedLevelIds: [],
    allTagsSelected: true,
    allLevelsSelected: true,
    levelOptions: [],
    filterSummary: {
      tags: "",
      levels: "",
      count: 0,
    },
    spots: [],
    homeCatalog: [],
    filteredSpots: [],
    markers: [],
    selectedSpot: null,
    selectedSpotId: 0,
    unlockHint: {
      hiddenCount: 0,
      nextNeed: 0,
    },
    showUnlockBubble: false,
    nearbyRadiusKm: "20",
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
    profileLoading: false,
    showProfileAuth: false,
    showSafetyAgreement: false,
  },

  onLoad() {
    this.mapAutoFit = true
    this.markerCanvasReady = false
    this.hideShareMenu()
    this.handleLocationChange = (location) => this.updateUserLocation(location, false)
    this.refreshCopy()
    this.bootstrapLogin()
    this.tryShowUserLocation()
  },

  onReady() {
    this.markerCanvasReady = true
    this.refreshMarkerIcons(this.data.filteredSpots)
  },

  onUnload() {
    clearTimeout(this.unlockBubbleTimer)
    if (this.handleLocationChange && wx.offLocationChange) {
      wx.offLocationChange(this.handleLocationChange)
    }
  },

  onPullDownRefresh() {
    this.loadHomeData().finally(() => wx.stopPullDownRefresh())
  },

  onShow() {
    app.applyTabBarLanguage()
    app.rememberTab("pages/index/index")
    if (this.data.lang !== (app.globalData.lang || "zh-CN")) this.onLanguageChanged()
  },

  onLanguageChanged() {
    this.refreshCopy()
    this.mapAutoFit = true
    this.loadHomeData()
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
    const user = app.globalData.user || {}
    const hasRealProfile = Boolean(user.avatar_url) && Boolean(user.nickname) && user.nickname !== "秘境探索者"
    if (!hasProfileAuth || !hasRealProfile) {
      this.setData({
        showProfileAuth: true,
        showSafetyAgreement: false,
        profileAuthForm: {
          nickname: user.nickname && user.nickname !== "秘境探索者" ? user.nickname : "",
          avatar_url: user.avatar_url || "",
        },
      })
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
      const [spots, homeCatalog] = await Promise.all([
        request(this.buildMapPath()),
        request(this.buildHomeCatalogPath()),
      ])
      this.setData({
        tags,
        spots: this.normalizeSpots(spots),
        homeCatalog: this.normalizeSpots(homeCatalog),
        offline: false,
        serviceClosed: false,
        loading: false,
      })
      this.applyFilters()
    } catch (error) {
      if (isServiceClosedError(error)) {
        this.setData({
          tags: [],
          spots: [],
          homeCatalog: [],
          filteredSpots: [],
          levelOptions: [],
          markers: [],
          selectedSpot: null,
          selectedSpotId: 0,
          unlockHint: { hiddenCount: 0, nextNeed: 0 },
          showUnlockBubble: false,
          offline: false,
          serviceClosed: true,
          loading: false,
        })
        return
      }
      this.setData({
        tags: [],
        spots: [],
        homeCatalog: [],
        filteredSpots: [],
        levelOptions: [],
        markers: [],
        selectedSpot: null,
        selectedSpotId: 0,
        unlockHint: { hiddenCount: 0, nextNeed: 0 },
        offline: true,
        serviceClosed: false,
        loading: false,
      })
    }
  },

  buildMapPath() {
    const { user } = this.data
    const params = [
      `lang=${this.data.lang}`,
      `user_id=${user.id}`,
      `explore_points=${user.explore_points}`,
      `is_member=${user.is_member ? "true" : "false"}`,
    ]
    return `/spots/map?${params.join("&")}`
  },

  buildHomeCatalogPath() {
    const user = this.data.user || {}
    const params = [
      `lang=${this.data.lang}`,
      `user_id=${user.id || 0}`,
      `explore_points=${user.explore_points || 0}`,
    ]
    return `/spots/home-catalog?${params.join("&")}`
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

  applyFilters(options = {}) {
    const selectedTagIds = this.data.selectedTagIds.map(Number)
    const selectedLevelIds = this.data.selectedLevelIds.map(Number)
    const catalog = this.data.homeCatalog || []
    const taggedSpots = selectedTagIds.length
      ? catalog.filter((spot) => spot.tags.some((tag) => selectedTagIds.includes(Number(tag.id))))
      : catalog
    const filteredCatalog = selectedLevelIds.length
      ? taggedSpots.filter((spot) => selectedLevelIds.includes(Number(spot.recommendation_level)))
      : taggedSpots
    const eligibleSpots = filteredCatalog.filter((spot) => this.canViewSpot(spot))
    const filteredSpots = (this.data.spots || []).filter((spot) => {
      if (!this.canViewSpot(spot)) return false
      return filteredCatalog.some((catalogSpot) => Number(catalogSpot.id) === Number(spot.id))
    })
    const selectedSpotId = options.preserveSelection ? this.data.selectedSpotId : (filteredSpots[0] && filteredSpots[0].id) || 0
    const selectedSpot = filteredSpots.find((spot) => spot.id === selectedSpotId) || filteredSpots[0] || null
    this.setData({
      filteredSpots,
      selectedSpot,
      selectedSpotId: (selectedSpot && selectedSpot.id) || 0,
      tags: this.decorateTags(this.data.tags, selectedTagIds),
      levelOptions: this.buildLevelOptions(taggedSpots, selectedLevelIds, eligibleSpots, filteredCatalog),
      allTagsSelected: selectedTagIds.length === 0,
      allLevelsSelected: selectedLevelIds.length === 0,
      filterSummary: this.buildFilterSummary(filteredCatalog, selectedTagIds, selectedLevelIds),
      unlockHint: this.buildUnlockHint(taggedSpots),
    })
    this.refreshMarkerIcons(filteredSpots)
    this.fitMapToVisiblePoints(filteredSpots)
  },

  decorateTags(tags, selectedTagIds) {
    return (tags || []).map((tag) => ({
      ...tag,
      active: selectedTagIds.includes(Number(tag.id)),
    }))
  },

  buildLevelOptions(spots, selectedLevelIds, eligibleSpots = [], filteredCatalog = []) {
    const eligibleSpotIds = new Set((eligibleSpots || []).map((spot) => Number(spot.id)))
    const byLevel = (spots || []).reduce((result, spot) => {
      const level = Number(spot.recommendation_level)
      if (!Number.isFinite(level) || level < 0) return result
      if (!result[level]) {
        result[level] = {
          level,
          markerColor: this.normalizeMarkerColor(spot.marker_color),
          count: 0,
          availableCount: 0,
          spots: [],
        }
      }
      result[level].count += 1
      if (eligibleSpotIds.has(Number(spot.id))) result[level].availableCount += 1
      if ((filteredCatalog || []).some((item) => Number(item.id) === Number(spot.id))) result[level].spots.push(spot)
      return result
    }, {})
    return Object.keys(byLevel)
      .map(Number)
      .sort((left, right) => left - right)
      .map((level) => ({
        ...byLevel[level],
        label: `L${level}`,
        active: selectedLevelIds.includes(level),
      }))
  },

  buildFilterSummary(spots, selectedTagIds, selectedLevelIds) {
    const tagNames = (this.data.tags || [])
      .filter((tag) => selectedTagIds.includes(Number(tag.id)))
      .map((tag) => tag.name)
    const levelNames = selectedLevelIds
      .slice()
      .sort((left, right) => left - right)
      .map((level) => `L${level}`)
    return {
      tags: tagNames.length ? tagNames.join(this.data.lang === "en-US" ? ", " : "、") : this.data.copy.allTags,
      levels: levelNames.length ? levelNames.join("-") : this.data.copy.allLevels,
      count: (spots || []).length,
    }
  },

  canViewSpot(spot) {
    // The API applies every unlock rule with the current user record. Rechecking
    // cached points here could hide a spot before mini-program login finishes.
    return spot.is_unlocked !== false
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
    return spots.map((spot) => this.spotToMarker(spot))
  },

  async refreshMarkerIcons(spots) {
    if (!this.markerCanvasReady) return
    const requestId = (this.markerIconRequestId || 0) + 1
    this.markerIconRequestId = requestId
    // The native map view on some clients can retain markers when two marker
    // lists are assigned in quick succession. Remove the previous list first.
    this.setData({ markers: [] })
    try {
      const markers = await Promise.all((spots || []).map(async (spot) => {
        try {
          const iconPath = await getMarkerIcon(this, "homeMarkerCanvas", spot.marker_color)
          return this.spotToMarker(spot, iconPath)
        } catch (error) {
          console.warn("custom marker icon failed for spot", spot.id, error)
          return this.spotToMarker(spot)
        }
      }))
      if (requestId === this.markerIconRequestId) this.setData({ markers })
    } catch (error) {
      console.warn("custom marker icon failed", error)
    }
  },

  spotToMarker(spot, iconPath = "") {
    const locked = !spot.is_unlocked
    const markerColor = this.normalizeMarkerColor(spot.marker_color)
    return {
      id: spot.id,
      latitude: spot.latitude,
      longitude: spot.longitude,
      width: 21,
      height: 26,
      ...(iconPath ? { iconPath } : {}),
      callout: {
        content: `${locked ? "🔒 " : ""}${spot.name}`,
        color: locked ? "#7b6651" : "#ffffff",
        fontSize: 13,
        borderRadius: 8,
        bgColor: locked ? "#fff2d8" : markerColor,
        padding: 8,
        display: "BYCLICK",
      },
    }
  },

  normalizeMarkerColor(color) {
    return normalizeMarkerColor(color)
  },

  onTagTap(event) {
    const tagId = Number(event.currentTarget.dataset.id)
    if (!tagId) return
    this.mapAutoFit = true
    const selectedTagIds = this.data.selectedTagIds.slice()
    const index = selectedTagIds.indexOf(tagId)
    if (index >= 0) selectedTagIds.splice(index, 1)
    else selectedTagIds.push(tagId)
    this.setData({ selectedTagIds }, () => this.applyFilters())
  },

  onClearTags() {
    this.mapAutoFit = true
    this.setData({ selectedTagIds: [] }, () => this.applyFilters())
  },

  onLevelTap(event) {
    const level = Number(event.currentTarget.dataset.level)
    if (!Number.isFinite(level) || level < 0) return
    this.mapAutoFit = true
    const selectedLevelIds = this.data.selectedLevelIds.slice()
    const index = selectedLevelIds.indexOf(level)
    if (index >= 0) selectedLevelIds.splice(index, 1)
    else selectedLevelIds.push(level)
    this.setData({ selectedLevelIds }, () => this.applyFilters())
  },

  onClearLevels() {
    this.mapAutoFit = true
    this.setData({ selectedLevelIds: [] }, () => this.applyFilters())
  },

  onNearbyRadiusInput(event) {
    this.setData({ nearbyRadiusKm: event.detail.value })
    clearTimeout(this.nearbyCountTimer)
    this.nearbyCountTimer = setTimeout(() => this.refreshNearbyCount(), 350)
  },

  buildLockedNearbyPath(path, location, radiusKm) {
    const user = this.data.user || {}
    const params = [
      `user_id=${user.id}`,
      `latitude=${location.latitude}`,
      `longitude=${location.longitude}`,
      `radius_km=${radiusKm}`,
    ]
    return `${path}?${params.join("&")}`
  },

  async refreshNearbyCount() {
    const radiusKm = Number(this.data.nearbyRadiusKm)
    if (!Number.isFinite(radiusKm) || radiusKm <= 0 || radiusKm > 4000) {
      this.setData({ nearbyCount: null })
      return
    }
    const requestId = (this.nearbyCountRequestId || 0) + 1
    this.nearbyCountRequestId = requestId
    try {
      const location = this.data.userLocation || (await this.getLocation())
      this.updateUserLocation(location, false)
      const result = await request(this.buildLockedNearbyPath("/spots/locked-nearby/count", location, radiusKm))
      if (requestId === this.nearbyCountRequestId) this.setData({ nearbyCount: Number(result.count || 0) })
    } catch (error) {
      if (requestId === this.nearbyCountRequestId) this.setData({ nearbyCount: null })
    }
  },

  async onSearchLockedSpots() {
    const radiusKm = Number(this.data.nearbyRadiusKm)
    if (!Number.isFinite(radiusKm) || radiusKm <= 0 || radiusKm > 4000) {
      wx.showToast({ title: this.data.copy.invalidRadius, icon: "none" })
      return
    }
    this.setData({ nearbySearching: true })
    try {
      const location = this.data.userLocation || (await this.getLocation())
      this.updateUserLocation(location, false)
      this.startLocationWatch()
      app.globalData.lockedSpotSearch = {
        latitude: Number(location.latitude),
        longitude: Number(location.longitude),
        radiusKm,
      }
      wx.navigateTo({ url: "/pages/locked-spot-list/locked-spot-list" })
    } catch (error) {
      wx.showModal({
        title: this.data.copy.locationRequired,
        content: this.data.copy.locationFailed,
        confirmText: this.data.lang === "en-US" ? "Settings" : "去设置",
        success: (res) => {
          if (res.confirm) wx.openSetting()
        },
      })
    } finally {
      this.setData({ nearbySearching: false })
    }
  },

  showUnlockHintBubble() {
    clearTimeout(this.unlockBubbleTimer)
    if (!this.data.unlockHint || this.data.unlockHint.hiddenCount <= 0) {
      this.setData({ showUnlockBubble: false })
      return
    }
    this.setData({ showUnlockBubble: true })
    this.unlockBubbleTimer = setTimeout(() => {
      this.setData({ showUnlockBubble: false })
    }, 3000)
  },

  hideUnlockHintBubble() {
    clearTimeout(this.unlockBubbleTimer)
    this.setData({ showUnlockBubble: false })
  },

  onMarkerTap(event) {
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

  onCatalogSpotTap(event) {
    const spotId = Number(event.currentTarget.dataset.id)
    const spot = (this.data.homeCatalog || []).find((item) => Number(item.id) === spotId)
    if (!spot) return
    if (spot.is_unlocked) {
      this.openSpotDetail(spot)
      return
    }
    app.globalData.lockedSpotDetailCache = {
      ...(app.globalData.lockedSpotDetailCache || {}),
      [spot.id]: spot,
    }
    wx.navigateTo({ url: `/pages/locked-spot-detail/locked-spot-detail?id=${spot.id}` })
  },

  onRecommendSpot() {
    wx.navigateTo({ url: "/pages/spot-recommend/spot-recommend" })
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

  async onAuthorizeProfile() {
    if (this.data.profileLoading) return
    this.setData({ profileLoading: true })
    wx.showLoading({
      title: this.data.lang === "en-US" ? "Syncing..." : "正在同步",
      mask: true,
    })
    let userInfo = this.getFallbackProfileInfo()
    try {
      userInfo = await this.getWechatProfileInfo()
    } catch (error) {
      console.warn("wx.getUserProfile failed, continue with login profile", error)
    }
    try {
      await this.saveProfileInfo(userInfo)
    } catch (error) {
      console.warn("save profile failed", error)
      this.setData({ profileLoading: false })
      wx.hideLoading()
      const message = error && error.message ? error.message : this.data.copy.profileFailed
      const isDomainConfigError = /not in domain list|合法域名|request:fail/i.test(message)
      wx.showModal({
        title: this.data.copy.profileFailed,
        content: isDomainConfigError ? this.data.copy.profileDomainFailed : message,
        showCancel: false,
      })
    }
  },

  getFallbackProfileInfo() {
    const user = app.globalData.user || {}
    return {
      nickName: this.data.profileAuthForm.nickname || user.nickname || "秘境探索者",
      avatarUrl: this.data.profileAuthForm.avatar_url || user.avatar_url || "",
    }
  },

  getWechatProfileInfo() {
    return new Promise((resolve, reject) => {
      if (!wx.getUserProfile) {
        resolve(this.getFallbackProfileInfo())
        return
      }
      wx.getUserProfile({
        desc: this.data.copy.profileBody,
        success: (profile) => {
          const info = profile.userInfo || {}
          resolve({
            nickName: info.nickName || this.data.profileAuthForm.nickname,
            avatarUrl: info.avatarUrl || this.data.profileAuthForm.avatar_url,
          })
        },
        fail: reject,
      })
    })
  },

  async saveProfileInfo(userInfo) {
    const fallback = this.getFallbackProfileInfo()
    const user = await app.bootstrapUser({
      force: true,
      nickname: userInfo.nickName || fallback.nickName,
      avatar_url: userInfo.avatarUrl || fallback.avatarUrl,
    })
    if (!user || !user.openid) {
      throw new Error("后台未返回用户 OpenID，请检查 /mini/login 接口和微信 AppID/Secret 配置")
    }
    wx.setStorageSync("gzProfileAuthAccepted", true)
    app.globalData.hasAcceptedProfileAuth = true
    this.setData({
      user,
      profileLoading: false,
      showProfileAuth: false,
      profileAuthForm: {
        nickname: user.nickname || "",
        avatar_url: user.avatar_url || "",
      },
    })
    wx.hideLoading()
    wx.showToast({
      title: this.data.lang === "en-US" ? "User synced" : "用户已同步",
      icon: "success",
    })
    this.checkSafetyAgreement()
    this.loadHomeData()
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
