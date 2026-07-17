const { request, uploadMedia } = require("../../utils/request")

const app = getApp()

const MAX_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024
const MAX_VIDEO_UPLOAD_BYTES = 8 * 1024 * 1024

Page({
  data: {
    lang: "zh-CN",
    tags: [],
    selectedTagIds: [],
    media: [],
    submitting: false,
    form: {
      name_zh: "",
      name_en: "",
      summary_zh: "",
      summary_en: "",
      description_zh: "",
      description_en: "",
      city: "",
      county: "",
      latitude: "",
      longitude: "",
      river_name: "",
      river_upstream_latitude: "",
      river_upstream_longitude: "",
      recommendation_level: "0",
    },
  },

  onLoad() {
    this.refreshLanguage()
    this.loadTags()
  },

  onShow() {
    app.applyTabBarLanguage()
  },

  onPullDownRefresh() {
    this.loadTags().finally(() => wx.stopPullDownRefresh())
  },

  refreshLanguage() {
    this.setData({ lang: app.globalData.lang || "zh-CN" })
  },

  async loadTags() {
    try {
      const tags = await request(`/tags?lang=${app.globalData.lang || "zh-CN"}`)
      this.setData({ tags })
    } catch (error) {
      wx.showToast({ title: "标签加载失败", icon: "none" })
    }
  },

  onFieldInput(event) {
    const field = event.currentTarget.dataset.field
    if (!field) return
    this.setData({ [`form.${field}`]: event.detail.value })
  },

  onTagTap(event) {
    const tagId = Number(event.currentTarget.dataset.id)
    if (!tagId) return
    const selectedTagIds = this.data.selectedTagIds.slice()
    const index = selectedTagIds.indexOf(tagId)
    if (index >= 0) selectedTagIds.splice(index, 1)
    else selectedTagIds.push(tagId)
    this.setData({ selectedTagIds })
  },

  async onChooseMedia() {
    if (this.data.media.length >= 9) return
    try {
      const result = await new Promise((resolve, reject) => wx.chooseMedia({
        count: Math.min(9 - this.data.media.length, 9),
        mediaType: ["image", "video"],
        sourceType: ["album", "camera"],
        success: resolve,
        fail: reject,
      }))
      for (const file of result.tempFiles || []) {
        const isVideo = file.fileType === "video"
        const limit = isVideo ? MAX_VIDEO_UPLOAD_BYTES : MAX_IMAGE_UPLOAD_BYTES
        if (Number(file.size || 0) > limit) {
          wx.showToast({ title: isVideo ? "视频不能超过 8MB" : "图片不能超过 2MB", icon: "none" })
          continue
        }
        const uploaded = await uploadMedia(file.tempFilePath, app.globalData.user.id, isVideo ? "video" : "image")
        this.setData({ media: this.data.media.concat([{ ...uploaded, localPath: file.tempFilePath }]) })
      }
    } catch (error) {
      if (error && error.errMsg && error.errMsg.includes("cancel")) return
      wx.showToast({ title: "上传失败，请稍后重试", icon: "none" })
    }
  },

  onRemoveMedia(event) {
    const index = Number(event.currentTarget.dataset.index)
    if (!Number.isFinite(index)) return
    const media = this.data.media.slice()
    media.splice(index, 1)
    this.setData({ media })
  },

  async onSubmit() {
    const form = this.data.form
    if (this.data.submitting) return
    if (!form.name_zh || !form.summary_zh || !form.city || !form.county || !form.latitude || !form.longitude) {
      wx.showToast({ title: "请填写名称、简介、区县和经纬度", icon: "none" })
      return
    }
    const latitude = Number(form.latitude)
    const longitude = Number(form.longitude)
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      wx.showToast({ title: "经纬度格式不正确", icon: "none" })
      return
    }
    this.setData({ submitting: true })
    try {
      await request("/mini/spot-recommendations", {
        method: "POST",
        data: {
          user_id: app.globalData.user.id,
          ...form,
          latitude: String(latitude),
          longitude: String(longitude),
          recommendation_level: Number(form.recommendation_level || 0),
          tag_ids: this.data.selectedTagIds,
          media: this.data.media.map((item) => ({ media_url: item.media_url, media_type: item.media_type })),
        },
      })
      wx.showModal({ title: "提交成功", content: "管理员审核通过后将发布到秘境目录。", showCancel: false, success: () => wx.navigateBack() })
    } catch (error) {
      wx.showToast({ title: "提交失败，请稍后重试", icon: "none" })
    } finally {
      this.setData({ submitting: false })
    }
  },
})
