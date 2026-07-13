const { isServiceClosedError, request, uploadMedia } = require("../../utils/request")
const { chooseNavigationApp } = require("../../utils/navigation")
const { getMarkerIcon, normalizeMarkerColor } = require("../../utils/marker-icon")

const app = getApp()
const MAX_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024
const MAX_VIDEO_UPLOAD_BYTES = 8 * 1024 * 1024

const COPY = {
  "zh-CN": {
    navTitle: "秘境详情",
    points: "探秘积分",
    unlockNeed: "解锁积分",
    users: "互动用户",
    interaction: "公开互动",
    interactionDescription: "通过公开留言交流路线、天气和注意事项，不公开联系方式。",
    emptyInteraction: "暂无互动留言",
    startInteraction: "去留言互动",
    myCheckins: "我的打卡",
    reviewPending: "审核中",
    reviewRejected: "未通过",
    reviewHidden: "已隐藏",
    notes: "游记",
    comments: "留言",
    recommendations: "衣食住行",
    description: "秘境介绍",
    location: "位置",
    tags: "标签",
    emptyRecommendations: "暂无衣食住行推荐",
    emptyNotes: "暂无游记",
    emptyComments: "暂无留言",
    loading: "加载中",
    loadFailed: "详情加载失败",
    fallbackNotice: "后台详情暂不可用，当前显示基础信息",
    locked: "积分不足，暂未解锁",
    featured: "精选",
    address: "地址",
    contact: "联系方式",
    clothing: "衣",
    food: "食",
    hotel: "住",
    transport: "行",
    safety: "实时安全信息",
    weather: "天气",
    alerts: "预警",
    riverRisk: "河流风险",
    upstreamWeather: "上游天气",
    upstreamAlerts: "上游预警",
    safetyNotConfigured: "实时天气暂未接入",
    noAlerts: "暂无生效预警",
    noUpstreamAlerts: "暂无上游生效预警",
    dataSource: "数据来源",
    actions: "互动提交",
    checkin: "提交打卡",
    writeNote: "发布游记",
    leaveComment: "发表留言",
    currentLocation: "我的实时位置",
    chooseMedia: "上传图片/视频",
    mediaReady: "素材已上传",
    mediaEmpty: "可选择图片或视频后再打卡",
    mediaImageTooLarge: "图片不能超过 2MB",
    mediaVideoTooLarge: "视频不能超过 8MB",
    noteTitle: "游记标题",
    noteContent: "游记内容",
    commentContent: "留言内容",
    submitNote: "发布游记",
    submitComment: "提交留言",
    checkinPlaceholder: "记录你到达这里的情况",
    noteTitlePlaceholder: "给这次探索起个标题",
    noteContentPlaceholder: "分享路线、天气、体验和注意事项",
    commentPlaceholder: "写下你的补充或提醒",
    submitted: "已提交，等待后台审核",
    submitFailed: "提交失败，请稍后重试",
    locationFailed: "定位失败，请检查定位权限",
    uploadFailed: "上传失败，请稍后重试",
    permissionDenied: "当前账号暂无此操作权限",
    goThere: "到这去",
    locationRequired: "请先允许位置权限",
    serviceClosed: "后台数据服务开放时间为每天北京时间 08:00-24:00，请在开放时间内使用。",
  },
  "en-US": {
    navTitle: "Gem Detail",
    points: "Explore Points",
    unlockNeed: "Required",
    users: "Users",
    interaction: "Community",
    interactionDescription: "Discuss routes, weather, and safety notes publicly. Contact details stay private.",
    emptyInteraction: "No public comments yet",
    startInteraction: "Write a Comment",
    myCheckins: "My Check-ins",
    reviewPending: "Pending Review",
    reviewRejected: "Not Approved",
    reviewHidden: "Hidden",
    notes: "Notes",
    comments: "Comments",
    recommendations: "Local Picks",
    description: "About",
    location: "Location",
    tags: "Tags",
    emptyRecommendations: "No local picks yet",
    emptyNotes: "No travel notes yet",
    emptyComments: "No comments yet",
    loading: "Loading",
    loadFailed: "Failed to load detail",
    fallbackNotice: "Detail service unavailable. Showing basic info",
    locked: "Not enough points to unlock",
    featured: "Featured",
    address: "Address",
    contact: "Contact",
    clothing: "Clothing",
    food: "Food",
    hotel: "Stay",
    transport: "Transport",
    safety: "Live Safety",
    weather: "Weather",
    alerts: "Alerts",
    riverRisk: "River Risk",
    upstreamWeather: "Upstream Weather",
    upstreamAlerts: "Upstream Alerts",
    safetyNotConfigured: "Live weather not configured",
    noAlerts: "No active alerts",
    noUpstreamAlerts: "No active upstream alerts",
    dataSource: "Source",
    actions: "Submit",
    checkin: "Check In",
    writeNote: "Write Note",
    leaveComment: "Leave Comment",
    currentLocation: "My Live Location",
    chooseMedia: "Upload Photo/Video",
    mediaReady: "Media uploaded",
    mediaEmpty: "Choose photo or video before check-in",
    mediaImageTooLarge: "Image must not exceed 2MB",
    mediaVideoTooLarge: "Video must not exceed 8MB",
    noteTitle: "Note Title",
    noteContent: "Travel Note",
    commentContent: "Comment",
    submitNote: "Publish Note",
    submitComment: "Submit Comment",
    checkinPlaceholder: "Record your arrival or field note",
    noteTitlePlaceholder: "Title your exploration",
    noteContentPlaceholder: "Share route, weather, experience, and cautions",
    commentPlaceholder: "Add a tip or reminder",
    submitted: "Submitted for review",
    submitFailed: "Submit failed. Try again later",
    locationFailed: "Location failed. Check permission",
    uploadFailed: "Upload failed. Try again later",
    permissionDenied: "This account does not have permission",
    goThere: "Go",
    locationRequired: "Allow location first",
    serviceClosed: "Data is available daily from 08:00 to 24:00 Beijing time.",
  },
}

const CATEGORY_ORDER = ["clothing", "food", "hotel", "transport"]

Page({
  data: {
    id: 0,
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    user: app.globalData.user,
    spot: null,
    spotPhotos: [],
    photoSlides: [],
    markers: [],
    userLocation: null,
    hasUserLocation: false,
    groupedRecommendations: [],
    safety: null,
    userCount: 0,
    loading: true,
    error: "",
    fallbackMode: false,
    interactionMessages: [],
    scrollTarget: "",
    checkinNote: "",
    checkinMedia: null,
    noteForm: {
      title: "",
      content: "",
    },
    commentForm: {
      content: "",
    },
    submitting: false,
  },

  onLoad(options) {
    this.markerCanvasReady = false
    this.hideShareMenu()
    this.handleLocationChange = (location) => this.updateUserLocation(location)
    const id = Number(options.id || 0)
    this.setData({ id })
    this.refreshCopy()
    this.loadDetail()
    this.tryShowUserLocation()
  },

  onReady() {
    this.markerCanvasReady = true
    this.refreshMarkerIcon(this.data.spot)
  },

  onUnload() {
    if (this.handleLocationChange && wx.offLocationChange) {
      wx.offLocationChange(this.handleLocationChange)
    }
  },

  onPullDownRefresh() {
    this.loadDetail().finally(() => wx.stopPullDownRefresh())
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

  buildDetailPath() {
    const { user } = this.data
    const params = [
      `lang=${this.data.lang}`,
      `user_id=${user.id}`,
      `explore_points=${user.explore_points}`,
      `is_member=${user.is_member ? "true" : "false"}`,
    ]
    return `/spots/${this.data.id}?${params.join("&")}`
  },

  async loadDetail() {
    if (!this.data.id) return
    this.setData({ loading: true, error: "" })
    try {
      const spot = this.normalizeSpot(await request(this.buildDetailPath()))
      this.setData({
        spot,
        spotPhotos: this.getSpotPhotos(spot),
        photoSlides: this.buildPhotoSlides(spot),
        markers: this.buildMarkers(spot),
        groupedRecommendations: this.groupRecommendations(spot.lifestyle_recommendations || []),
        userCount: this.countUsers(spot),
        interactionMessages: this.buildInteractionMessages(spot),
        loading: false,
        fallbackMode: false,
      })
      this.refreshMarkerIcon(spot)
      this.loadSafety()
    } catch (error) {
      if (isServiceClosedError(error)) {
        this.setData({
          spot: null,
          markers: [],
          groupedRecommendations: [],
          safety: null,
          loading: false,
          fallbackMode: false,
          error: this.data.copy.serviceClosed,
        })
        return
      }
      const fallbackSpot = app.globalData.currentSpot
      if (fallbackSpot && Number(fallbackSpot.id) === this.data.id) {
        const spot = this.normalizeSpot(fallbackSpot)
        this.setData({
          spot,
          spotPhotos: this.getSpotPhotos(spot),
          photoSlides: this.buildPhotoSlides(spot),
          markers: this.buildMarkers(spot),
          groupedRecommendations: [],
          userCount: 0,
          loading: false,
          fallbackMode: true,
          error: "",
        })
        this.refreshMarkerIcon(spot)
        return
      }
      this.setData({
        loading: false,
        error: error.message || this.data.copy.loadFailed,
      })
      wx.showToast({
        title: this.data.copy.loadFailed,
        icon: "none",
      })
    }
  },

  async loadSafety() {
    try {
      const safety = await request(`/spots/${this.data.id}/safety?lang=${this.data.lang}`)
      this.setData({ safety: this.normalizeSafety(safety) })
    } catch (error) {
      console.warn("load safety failed", error)
      this.setData({ safety: null })
    }
  },

  normalizeSafety(safety) {
    const weather = safety.weather || {}
    const riverWarning = safety.river_warning || {}
    const upstreamWeather = riverWarning.upstream_weather || {}
    const upstream = upstreamWeather.weather || {}
    const upstreamLocation = riverWarning.upstream_location
    const upstreamLocationText = upstreamLocation
      ? `${Number(upstreamLocation.latitude).toFixed(4)}, ${Number(upstreamLocation.longitude).toFixed(4)}`
      : ""
    return {
      ...safety,
      weatherText: weather.text ? `${weather.text} ${weather.temp || "-"}°C` : this.data.copy.safetyNotConfigured,
      weatherMeta: weather.obsTime ? `${weather.windDir || ""} ${weather.windScale || ""}级 · ${weather.humidity || "-"}% · ${weather.obsTime}` : "",
      upstreamWeatherText: upstream.text ? `${upstream.text} ${upstream.temp || "-"}°C` : "",
      upstreamWeatherMeta: upstream.obsTime ? `${upstream.windDir || ""} ${upstream.windScale || ""}级 · ${upstream.humidity || "-"}% · ${upstream.obsTime}${upstreamLocationText ? ` · ${upstreamLocationText}` : ""}` : upstreamLocationText,
      alerts: safety.alerts || [],
      upstreamAlerts: riverWarning.upstream_alerts || [],
      riverLevelText: this.riverLevelText(riverWarning.level),
    }
  },

  riverLevelText(level) {
    const labels = {
      high: this.data.lang === "en-US" ? "High" : "高",
      medium: this.data.lang === "en-US" ? "Medium" : "中",
      low: this.data.lang === "en-US" ? "Low" : "低",
      unknown: this.data.lang === "en-US" ? "Unknown" : "未知",
    }
    return labels[level] || labels.unknown
  },

  normalizeSpot(spot) {
    return {
      ...spot,
      required_explore_points: spot.required_explore_points || 0,
      user_explore_points: spot.user_explore_points || this.data.user.explore_points || 0,
      is_unlocked: spot.is_unlocked !== false,
      tags: spot.tags || [],
      travel_notes: (spot.travel_notes || []).map((item) => this.decorateSubmission(item)),
      comments: (spot.comments || []).map((item) => this.decorateSubmission(item)),
      my_checkins: (spot.my_checkins || []).map((item) => this.decorateSubmission(item)),
      lifestyle_recommendations: spot.lifestyle_recommendations || [],
      images: spot.images || [],
    }
  },

  decorateSubmission(item) {
    const status = item.status || "pending"
    const statusText = {
      pending: this.data.copy.reviewPending,
      rejected: this.data.copy.reviewRejected,
      hidden: this.data.copy.reviewHidden,
    }[status] || ""
    return {
      ...item,
      isMine: Number(item.user_id) === Number(this.data.user.id),
      statusText,
    }
  },

  getSpotPhotos(spot) {
    return (spot.images || [])
      .filter((item) => item.is_active !== false && ["image", "video"].includes(item.media_type || "image") && (item.display_url || item.image_url))
      .sort((left, right) => Number(Boolean(right.is_cover)) - Number(Boolean(left.is_cover)) || left.sort_order - right.sort_order)
  },

  buildPhotoSlides(spot) {
    const photos = this.getSpotPhotos(spot)
    const slides = []
    for (let index = 0; index < photos.length; index += 3) {
      slides.push(photos.slice(index, index + 3))
    }
    return slides
  },

  onPreviewSpotPhoto(event) {
    const current = event.currentTarget.dataset.url
    if (event.currentTarget.dataset.mediaType === "video") return
    const urls = this.data.spotPhotos
      .filter((item) => (item.media_type || "image") === "image")
      .map((item) => item.display_url || item.image_url)
      .filter(Boolean)
    if (current && urls.length) wx.previewImage({ current, urls })
  },

  async refreshMarkerIcon(spot) {
    if (!this.markerCanvasReady || !spot) return
    const requestId = (this.markerIconRequestId || 0) + 1
    this.markerIconRequestId = requestId
    try {
      const iconPath = await getMarkerIcon(this, "detailMarkerCanvas", spot.marker_color)
      if (requestId === this.markerIconRequestId) {
        this.setData({ markers: this.buildMarkers(spot, iconPath) })
      }
    } catch (error) {
      console.warn("custom detail marker icon failed", error)
    }
  },

  buildMarkers(spot, iconPath = "") {
    const markerColor = this.normalizeMarkerColor(spot.marker_color)
    const markers = [
      {
        id: spot.id,
        latitude: spot.latitude,
        longitude: spot.longitude,
        width: 42,
        height: 52,
        ...(iconPath ? { iconPath } : {}),
        callout: {
          content: spot.name,
          display: "BYCLICK",
          fontSize: 13,
          borderRadius: 8,
          padding: 8,
          bgColor: markerColor,
          color: "#ffffff",
        },
      },
    ]
    return markers
  },

  normalizeMarkerColor(color) {
    return normalizeMarkerColor(color)
  },

  countUsers(spot) {
    const ids = {}
    ;(spot.travel_notes || []).filter((item) => item.status === "approved").forEach((item) => {
      ids[item.user_id] = true
    })
    ;(spot.comments || []).filter((item) => item.status === "approved").forEach((item) => {
      ids[item.user_id] = true
    })
    return Object.keys(ids).length
  },

  buildInteractionMessages(spot) {
    return (spot.comments || [])
      .filter((item) => item.status === "approved" && item.content)
      .map((item) => ({
        id: item.id,
        nickname: item.nickname || (this.data.lang === "en-US" ? "Explorer" : "探索者"),
        content: item.content,
      }))
  },

  scrollTo(target) {
    this.setData({ scrollTarget: "" }, () => this.setData({ scrollTarget: target }))
  },

  onStatTap(event) {
    const target = event.currentTarget.dataset.target
    if (target === "checkin") {
      this.openAction("checkin")
      return
    }
    if (target) this.scrollTo(target)
  },

  onStartInteraction() {
    this.openAction("comment")
  },

  onActionTap(event) {
    this.openAction(event.currentTarget.dataset.action)
  },

  openAction(action) {
    if (!this.data.spot || !action) return
    wx.navigateTo({
      url: `/pages/spot-submit/spot-submit?id=${this.data.spot.id}&mode=${action}`,
    })
  },

  groupRecommendations(recommendations) {
    const copy = this.data.copy
    return CATEGORY_ORDER.map((category) => ({
      category,
      label: copy[category],
      items: recommendations.filter((item) => item.category === category).map((item) => ({
        ...item,
        displayName: this.data.lang === "en-US" ? item.name_en : item.name_zh,
        displaySummary: this.data.lang === "en-US" ? item.summary_en : item.summary_zh,
      })),
    })).filter((group) => group.items.length)
  },

  onLanguageTap() {
    app.setLanguage(this.data.lang === "zh-CN" ? "en-US" : "zh-CN")
    this.refreshCopy()
    this.loadDetail()
  },

  onCheckinNoteInput(event) {
    this.setData({ checkinNote: event.detail.value })
  },

  async tryShowUserLocation() {
    try {
      const location = await this.getLocation()
      this.updateUserLocation(location)
      this.startLocationWatch()
    } catch (error) {
      console.warn("detail location skipped", error)
    }
  },

  updateUserLocation(location) {
    this.setData({
      userLocation: {
        latitude: location.latitude,
        longitude: location.longitude,
      },
      hasUserLocation: true,
    })
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

  async onChooseCheckinMedia() {
    if (this.data.submitting) return
    const allowedMediaTypes = []
    if (this.data.user.can_upload_image !== false) allowedMediaTypes.push("image")
    if (this.data.user.can_upload_video !== false) allowedMediaTypes.push("video")
    if (allowedMediaTypes.length === 0) {
      wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
      return
    }
    try {
      const result = await new Promise((resolve, reject) => {
        wx.chooseMedia({
          count: 1,
          mediaType: allowedMediaTypes,
          sourceType: ["album", "camera"],
          maxDuration: 30,
          camera: "back",
          success: resolve,
          fail: reject,
        })
      })
      const file = result.tempFiles && result.tempFiles[0]
      if (!file || !file.tempFilePath) return
      const fileType = file.fileType || result.type || (/\.(mp4|mov|m4v)$/i.test(file.tempFilePath) ? "video" : "image")
      const fileSize = Number(file.size || 0)
      if (fileType === "video" && this.data.user.can_upload_video === false) {
        wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
        return
      }
      if (fileType !== "video" && this.data.user.can_upload_image === false) {
        wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
        return
      }
      if (fileType === "video" && fileSize > MAX_VIDEO_UPLOAD_BYTES) {
        wx.showToast({ title: this.data.copy.mediaVideoTooLarge, icon: "none" })
        return
      }
      if (fileType !== "video" && fileSize > MAX_IMAGE_UPLOAD_BYTES) {
        wx.showToast({ title: this.data.copy.mediaImageTooLarge, icon: "none" })
        return
      }
      this.setData({ submitting: true })
      const uploaded = await uploadMedia(file.tempFilePath, fileType)
      this.setData({
        submitting: false,
        checkinMedia: {
          ...uploaded,
          tempFilePath: file.tempFilePath,
          media_type: uploaded.media_type || fileType,
        },
      })
      wx.showToast({ title: this.data.copy.mediaReady, icon: "none" })
    } catch (error) {
      this.setData({ submitting: false })
      if (isServiceClosedError(error)) return
      console.error("check-in media upload failed", error)
      wx.showModal({
        title: this.data.copy.uploadFailed,
        content: error.message || this.data.copy.uploadFailed,
        showCancel: false,
      })
    }
  },

  async onNavigateTap() {
    const spot = this.data.spot
    if (!spot) return
    try {
      const location = this.data.userLocation || (await this.getLocation())
      this.updateUserLocation(location)
      this.startLocationWatch()
      chooseNavigationApp({
        spot,
        location,
        mapId: "spotDetailMap",
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

  onFloatingBackTap() {
    const goHome = () => wx.switchTab({ url: "/pages/index/index" })
    if (getCurrentPages().length > 1) {
      wx.navigateBack({ delta: 1, fail: goHome })
      return
    }
    goHome()
  },

  onNoteTitleInput(event) {
    this.setData({ "noteForm.title": event.detail.value })
  },

  onNoteContentInput(event) {
    this.setData({ "noteForm.content": event.detail.value })
  },

  onCommentInput(event) {
    this.setData({ "commentForm.content": event.detail.value })
  },

  async onSubmitCheckin() {
    if (this.data.submitting || !this.data.spot) return
    if (this.data.user.can_checkin === false) {
      wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      let location
      try {
        location = this.data.userLocation || (await this.getLocation())
        this.updateUserLocation(location)
        this.startLocationWatch()
      } catch (error) {
        wx.showToast({ title: this.data.copy.locationFailed, icon: "none" })
        return
      }
      await request("/mini/checkins", {
        method: "POST",
        data: {
          user_id: this.data.user.id,
          spot_id: this.data.spot.id,
          latitude: String(location.latitude),
          longitude: String(location.longitude),
          image_url: (this.data.checkinMedia && this.data.checkinMedia.image_url) || null,
          media_url: (this.data.checkinMedia && this.data.checkinMedia.media_url) || null,
          media_type: (this.data.checkinMedia && this.data.checkinMedia.media_type) || null,
          note: this.data.checkinNote,
        },
      })
      this.setData({ checkinNote: "", checkinMedia: null })
      await this.loadDetail()
      wx.showToast({ title: this.data.copy.submitted, icon: "none" })
    } catch (error) {
      if (isServiceClosedError(error)) return
      wx.showToast({ title: this.data.copy.submitFailed, icon: "none" })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async onSubmitNote() {
    const title = this.data.noteForm.title.trim()
    const content = this.data.noteForm.content.trim()
    if (this.data.submitting || !title || !content || !this.data.spot) return
    if (this.data.user.can_comment === false) {
      wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      await request("/mini/travel-notes", {
        method: "POST",
        data: {
          user_id: this.data.user.id,
          spot_id: this.data.spot.id,
          title,
          content,
        },
      })
      this.setData({ noteForm: { title: "", content: "" } })
      await this.loadDetail()
      wx.showToast({ title: this.data.copy.submitted, icon: "none" })
    } catch (error) {
      if (isServiceClosedError(error)) return
      wx.showToast({ title: this.data.copy.submitFailed, icon: "none" })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async onSubmitComment() {
    const content = this.data.commentForm.content.trim()
    if (this.data.submitting || !content || !this.data.spot) return
    if (this.data.user.can_comment === false) {
      wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      await request("/mini/comments", {
        method: "POST",
        data: {
          user_id: this.data.user.id,
          spot_id: this.data.spot.id,
          content,
        },
      })
      this.setData({ commentForm: { content: "" } })
      await this.loadDetail()
      wx.showToast({ title: this.data.copy.submitted, icon: "none" })
    } catch (error) {
      if (isServiceClosedError(error)) return
      wx.showToast({ title: this.data.copy.submitFailed, icon: "none" })
    } finally {
      this.setData({ submitting: false })
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
})
