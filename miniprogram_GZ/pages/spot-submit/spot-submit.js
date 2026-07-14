const { isServiceClosedError, request, uploadMedia } = require("../../utils/request")

const app = getApp()
const MAX_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024
const MAX_VIDEO_UPLOAD_BYTES = 8 * 1024 * 1024

const COPY = {
  "zh-CN": {
    navTitle: "探索提交",
    explorer: "夜郎秘境",
    loading: "加载中",
    checkin: "提交打卡",
    writeNote: "发布游记",
    leaveComment: "发表留言",
    myCheckins: "我的打卡",
    currentLocation: "我的实时位置",
    locationFailed: "定位失败，请检查定位权限",
    chooseMedia: "添加图片/视频",
    removeMedia: "移除",
    mediaReady: "素材已上传",
    mediaAdded: "素材已添加",
    mediaImageTooLarge: "图片不能超过 2MB",
    mediaVideoTooLarge: "视频不能超过 8MB",
    checkinPassed: "打卡成功",
    checkinFailed: "未在打卡范围内",
    noteTitlePlaceholder: "给这次探索起个标题",
    noteContentPlaceholder: "分享路线、天气、体验和注意事项",
    commentPlaceholder: "写下你的补充或提醒",
    submitNote: "发布游记",
    submitComment: "提交留言",
    noteRequired: "请填写游记标题和内容",
    commentRequired: "请填写留言内容",
    submittingNotice: "正在提交，请稍候",
    submitted: "已提交，等待后台审核",
    submitFailed: "提交失败，请稍后重试",
    uploadFailed: "上传失败，请稍后重试",
    permissionDenied: "当前账号暂无此操作权限",
    reviewPending: "审核中",
    reviewRejected: "未通过",
    reviewHidden: "已隐藏",
  },
  "en-US": {
    navTitle: "Submit Exploration",
    explorer: "Yelang Hidden Gems",
    loading: "Loading",
    checkin: "Check In",
    writeNote: "Write Note",
    leaveComment: "Leave Comment",
    myCheckins: "My Check-ins",
    currentLocation: "My Live Location",
    locationFailed: "Location failed. Check permission",
    chooseMedia: "Add Photo/Video",
    removeMedia: "Remove",
    mediaReady: "Media uploaded",
    mediaAdded: "Media added",
    mediaImageTooLarge: "Image must not exceed 2MB",
    mediaVideoTooLarge: "Video must not exceed 8MB",
    checkinPassed: "Check-in Successful",
    checkinFailed: "Outside Check-in Range",
    noteTitlePlaceholder: "Title your exploration",
    noteContentPlaceholder: "Share route, weather, experience, and cautions",
    commentPlaceholder: "Add a tip or reminder",
    submitNote: "Publish Note",
    submitComment: "Submit Comment",
    noteRequired: "Enter both a title and note content",
    commentRequired: "Enter a comment",
    submittingNotice: "Submitting. Please wait",
    submitted: "Submitted for review",
    submitFailed: "Submit failed. Try again later",
    uploadFailed: "Upload failed. Try again later",
    permissionDenied: "This account does not have permission",
    reviewPending: "Pending Review",
    reviewRejected: "Not Approved",
    reviewHidden: "Hidden",
  },
}

Page({
  data: {
    id: 0,
    mode: "checkin",
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    user: app.globalData.user,
    spot: null,
    myCheckins: [],
    loading: true,
    refreshing: false,
    error: "",
    submitting: false,
    userLocation: null,
    noteMedia: [],
    noteForm: { title: "", content: "" },
    commentForm: { content: "" },
  },

  onLoad(options) {
    const mode = ["checkin", "note", "comment"].includes(options.mode) ? options.mode : "checkin"
    this.setData({ id: Number(options.id || 0), mode })
    this.refreshCopy()
    this.loadSpot()
    if (mode === "checkin") this.tryShowUserLocation()
  },

  onShow() {
    app.applyTabBarLanguage()
  },

  onLanguageChanged() {
    this.refreshCopy()
    this.loadSpot()
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true })
    this.loadSpot().finally(() => {
      this.setData({ refreshing: false })
      wx.stopPullDownRefresh()
    })
  },

  refreshCopy() {
    const lang = app.globalData.lang || "zh-CN"
    this.setData({ lang, copy: COPY[lang], user: app.globalData.user })
  },

  buildDetailPath() {
    const { user, id, lang } = this.data
    return `/spots/${id}?lang=${lang}&user_id=${user.id}&explore_points=${user.explore_points || 0}&is_member=${user.is_member ? "true" : "false"}`
  },

  async loadSpot() {
    if (!this.data.id) return
    this.setData({ loading: true, error: "" })
    try {
      const spot = await request(this.buildDetailPath())
      this.setData({
        spot,
        myCheckins: (spot.my_checkins || []).map((item) => this.decorateSubmission(item)),
        loading: false,
      })
    } catch (error) {
      this.setData({ loading: false, error: error.message || this.data.copy.submitFailed })
    }
  },

  decorateSubmission(item) {
    const statusText = { pending: this.data.copy.reviewPending, rejected: this.data.copy.reviewRejected, hidden: this.data.copy.reviewHidden }[item.status] || ""
    return { ...item, statusText }
  },

  onNoteTitleInput(event) { this.setData({ "noteForm.title": event.detail.value }) },
  onNoteContentInput(event) { this.setData({ "noteForm.content": event.detail.value }) },
  onCommentInput(event) { this.setData({ "commentForm.content": event.detail.value }) },
  onRemoveNoteMedia(event) {
    const index = Number(event.currentTarget.dataset.index)
    this.setData({ noteMedia: this.data.noteMedia.filter((_, itemIndex) => itemIndex !== index) })
  },

  async tryShowUserLocation() {
    try {
      const location = await this.getLocation()
      this.setData({ userLocation: { latitude: location.latitude, longitude: location.longitude } })
    } catch (error) {
      console.warn("submit location skipped", error)
    }
  },

  async onChooseNoteMedia() {
    if (this.data.submitting) return
    const allowedMediaTypes = []
    if (this.data.user.can_upload_image !== false) allowedMediaTypes.push("image")
    if (this.data.user.can_upload_video !== false) allowedMediaTypes.push("video")
    if (!allowedMediaTypes.length) return wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
    try {
      const remaining = 9 - this.data.noteMedia.length
      if (remaining <= 0) return wx.showToast({ title: "最多添加 9 个文件", icon: "none" })
      const result = await new Promise((resolve, reject) => wx.chooseMedia({ count: remaining, mediaType: allowedMediaTypes, sourceType: ["album", "camera"], maxDuration: 30, camera: "back", success: resolve, fail: reject }))
      const files = (result.tempFiles || []).filter((file) => file && file.tempFilePath)
      if (!files.length) return
      this.setData({ submitting: true })
      const uploadedMedia = []
      for (const file of files) {
        const type = file.fileType || result.type || (/\.(mp4|mov|m4v)$/i.test(file.tempFilePath) ? "video" : "image")
        if (type === "video" && Number(file.size || 0) > MAX_VIDEO_UPLOAD_BYTES) throw new Error(this.data.copy.mediaVideoTooLarge)
        if (type !== "video" && Number(file.size || 0) > MAX_IMAGE_UPLOAD_BYTES) throw new Error(this.data.copy.mediaImageTooLarge)
        const uploaded = await uploadMedia(file.tempFilePath, type)
        uploadedMedia.push({ ...uploaded, tempFilePath: file.tempFilePath, media_type: uploaded.media_type || type })
      }
      this.setData({ noteMedia: [...this.data.noteMedia, ...uploadedMedia] })
      wx.showToast({ title: this.data.copy.mediaAdded, icon: "none" })
    } catch (error) {
      if (!isServiceClosedError(error)) wx.showModal({ title: this.data.copy.uploadFailed, content: error.message || this.data.copy.uploadFailed, showCancel: false })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async onSubmitCheckin() {
    if (this.data.submitting || this.data.user.can_checkin === false) return
    this.setData({ submitting: true })
    try {
      const location = this.data.userLocation || await this.getLocation()
      this.setData({ userLocation: { latitude: location.latitude, longitude: location.longitude } })
      const record = await request("/mini/checkins", { method: "POST", data: { user_id: this.data.user.id, spot_id: this.data.spot.id, latitude: String(location.latitude), longitude: String(location.longitude) } })
      await this.loadSpot()
      wx.showModal({
        title: record.status === "approved" ? this.data.copy.checkinPassed : this.data.copy.checkinFailed,
        content: record.review_note || this.data.copy.submitFailed,
        showCancel: false,
      })
    } catch (error) {
      if (!isServiceClosedError(error)) wx.showToast({ title: this.data.copy.submitFailed, icon: "none" })
    } finally { this.setData({ submitting: false }) }
  },

  async onSubmitNote() {
    const { title, content } = this.data.noteForm
    if (this.data.submitting) {
      wx.showToast({ title: this.data.copy.submittingNotice, icon: "none" })
      return
    }
    if (this.data.user.can_comment === false) {
      wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
      return
    }
    if (!title.trim() || !content.trim()) {
      wx.showToast({ title: this.data.copy.noteRequired, icon: "none" })
      return
    }
    await this.submitContent("/mini/travel-notes", {
      user_id: this.data.user.id,
      spot_id: this.data.spot.id,
      title: title.trim(),
      content: content.trim(),
      media: this.data.noteMedia.map((item) => ({ media_url: item.media_url, media_type: item.media_type })),
    }, { noteForm: { title: "", content: "" }, noteMedia: [] })
  },

  async onSubmitComment() {
    const content = this.data.commentForm.content.trim()
    if (this.data.submitting) {
      wx.showToast({ title: this.data.copy.submittingNotice, icon: "none" })
      return
    }
    if (this.data.user.can_comment === false) {
      wx.showToast({ title: this.data.copy.permissionDenied, icon: "none" })
      return
    }
    if (!content) {
      wx.showToast({ title: this.data.copy.commentRequired, icon: "none" })
      return
    }
    await this.submitContent("/mini/comments", { user_id: this.data.user.id, spot_id: this.data.spot.id, content }, { commentForm: { content: "" } })
  },

  async submitContent(path, data, resetData) {
    this.setData({ submitting: true })
    try {
      await request(path, { method: "POST", data })
      this.setData(resetData)
      wx.showToast({ title: this.data.copy.submitted, icon: "none" })
    } catch (error) {
      if (!isServiceClosedError(error)) {
        wx.showModal({
          title: this.data.copy.submitFailed,
          content: error.message || this.data.copy.submitFailed,
          showCancel: false,
        })
      }
    } finally { this.setData({ submitting: false }) }
  },

  getLocation() {
    return new Promise((resolve, reject) => wx.getLocation({ type: "gcj02", success: resolve, fail: reject }))
  },

  onBackTap() {
    wx.navigateBack({ delta: 1, fail: () => wx.switchTab({ url: "/pages/index/index" }) })
  },
})
