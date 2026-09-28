const { communityRequest, communityUpload } = require("../../utils/community-client")
const { resolveMediaUrl } = require("../../utils/request")
const labels = { pending: "待审核", approved: "通过", rejected: "不通过" }
const categories = [
  "A. 本人将超市购物袋大小的垃圾袋丢入垃圾桶",
  "B. 本人将装有明显可辨垃圾的垃圾袋放入个人车厢内带走",
  "C. 本人手提装有明显可辨垃圾的垃圾袋",
]

Page({
  data: { mode: "history", spotId: 0, summary: null, records: [], foodRecords: [], categories, categoryIndex: 0,
    video: null, photos: [], title: "", content: "", busy: false, loading: false, error: "", blocked: false },
  onLoad(options) {
    this.setData({ mode: ["eco", "food"].includes(options.mode) ? options.mode : "history", spotId: Number(options.id || 0) })
  },
  onShow() { this.load() },
  async load() {
    this.setData({ loading: true, error: "" })
    try {
      const summary = await communityRequest("/summary")
      const records = await communityRequest(`/eco${this.data.mode === "eco" ? `?spot_id=${this.data.spotId}` : ""}`)
      const food = await communityRequest("/food")
      const decorate = (row) => ({ ...row, statusText: labels[row.status], media: row.media.map((m) => ({ ...m, url: resolveMediaUrl(m.url) })) })
      this.setData({ summary, records: records.map(decorate), foodRecords: food.map(decorate),
        blocked: this.data.mode === "eco" && records.some((row) => row.status !== "rejected") })
    } catch (error) { this.setData({ error: error.message || "加载失败" }) }
    finally { this.setData({ loading: false }) }
  },
  onCategory(event) { this.setData({ categoryIndex: Number(event.detail.value) }) },
  onTitle(event) { this.setData({ title: event.detail.value }) },
  onContent(event) { this.setData({ content: event.detail.value }) },
  onRemovePhoto(event) { if (!this.data.busy) this.setData({ photos: this.data.photos.filter((_, i) => i !== Number(event.currentTarget.dataset.index)) }) },
  onRemoveVideo() { if (!this.data.busy) this.setData({ video: null }) },
  async onRecord() {
    if (this.data.busy || this.data.blocked) return
    this.setData({ busy: true })
    try {
      const eco = this.data.mode === "eco"
      const maxDuration = eco ? 3 : this.data.summary.food_policy.max_video_seconds
      const video = await new Promise((resolve, reject) => wx.chooseVideo({ sourceType: ["camera"], maxDuration, compressed: true, camera: "back", success: resolve, fail: reject }))
      if (video.size > 8 * 1024 * 1024) throw new Error("视频不能超过8MB")
      if (!Number.isFinite(video.duration) || (eco && (video.duration < 2.5 || video.duration > 3.5)) || video.duration > maxDuration + 0.5) throw new Error(eco ? "请录制完整3秒视频" : "视频时长超过限制")
      this.setData({ video })
    } catch (error) { this.showError(error) }
    finally { this.setData({ busy: false }) }
  },
  async onPhotos() {
    if (this.data.busy) return
    const policy = this.data.summary && this.data.summary.food_policy
    if (!policy) return
    const remaining = policy.max_photos - this.data.photos.length
    if (remaining <= 0) return
    this.setData({ busy: true })
    try {
      const result = await new Promise((resolve, reject) => wx.chooseMedia({ count: remaining, mediaType: ["image"], sourceType: ["album", "camera"], success: resolve, fail: reject }))
      const photos = result.tempFiles || []
      for (const file of photos) {
        const size = await new Promise((resolve, reject) => wx.getImageInfo({ src: file.tempFilePath, success: resolve, fail: reject }))
        if (file.size > policy.max_image_bytes || size.width > policy.max_width || size.height > policy.max_height) throw new Error("图片大小或尺寸超出后台设置")
      }
      this.setData({ photos: this.data.photos.concat(photos) })
    } catch (error) { this.showError(error) }
    finally { this.setData({ busy: false }) }
  },
  async onSubmit() {
    if (this.data.busy || this.data.loading || this.data.blocked) return
    const eco = this.data.mode === "eco"
    this.setData({ busy: true })
    try {
      if (eco && !this.data.video) throw new Error("请先录制3秒环保视频")
      const policy = this.data.summary && this.data.summary.food_policy
      if (!eco && (!policy || this.data.photos.length < policy.min_photos || (policy.video_required && !this.data.video) || !this.data.title.trim() || !this.data.content.trim())) throw new Error("请填写推荐内容并按要求添加照片和视频")
      const files = eco ? [this.data.video] : [...this.data.photos, ...(this.data.video ? [this.data.video] : [])]
      const ids = []
      for (const file of files) {
        const isVideo = file === this.data.video
        if (!file.uploadId) {
          const uploaded = await communityUpload(file.tempFilePath, eco ? "eco" : "food", isVideo ? "video" : "image")
          file.uploadId = uploaded.id
        }
        ids.push(file.uploadId)
      }
      const payload = eco ? { spot_id: this.data.spotId, category: ["A", "B", "C"][this.data.categoryIndex], upload_id: ids[0] }
        : { title: this.data.title, content: this.data.content, upload_ids: ids }
      await communityRequest(eco ? "/eco" : "/food", { method: "POST", data: payload })
      this.setData({ video: null, photos: [], title: "", content: "" })
      wx.showModal({ title: "提交成功", content: "审核状态：待审核。审核结果将在小程序内通知。", showCancel: false })
      await this.load()
    } catch (error) { this.showError(error) }
    finally { this.setData({ busy: false }) }
  },
  showError(error) {
    if (!/cancel/i.test(error.errMsg || "")) wx.showModal({ title: "提示", content: error.message || error.errMsg || "操作失败", showCancel: false })
  },
  onBack() { wx.navigateBack({ fail: () => wx.switchTab({ url: "/pages/user/user" }) }) },
})
