const app = getApp()

const COPY = {
  "zh-CN": {
    imageTitle: "图片查看",
    videoTitle: "视频播放",
  },
  "en-US": {
    imageTitle: "Photo Viewer",
    videoTitle: "Video Player",
  },
}

Page({
  data: {
    lang: "zh-CN",
    title: "图片查看",
    mediaType: "image",
    currentUrl: "",
    imageUrls: [],
    currentIndex: 0,
  },

  onLoad(options) {
    this.hideShareMenu()
    const media = app.globalData.spotMediaViewer || {}
    const lang = app.globalData.lang || "zh-CN"
    const mediaType = media.mediaType === "video" ? "video" : "image"
    const currentUrl = media.currentUrl || decodeURIComponent(options.url || "")
    const imageUrls = (media.imageUrls || []).filter(Boolean)
    const currentIndex = Math.max(imageUrls.indexOf(currentUrl), 0)
    this.setData({
      lang,
      title: mediaType === "video" ? COPY[lang].videoTitle : COPY[lang].imageTitle,
      mediaType,
      currentUrl,
      imageUrls: imageUrls.length ? imageUrls : (currentUrl ? [currentUrl] : []),
      currentIndex,
    })
  },

  onFloatingBackTap() {
    const goHome = () => wx.switchTab({ url: "/pages/index/index" })
    wx.navigateBack({ delta: 1, fail: goHome })
  },

  hideShareMenu() {
    if (wx.hideShareMenu) wx.hideShareMenu({ menus: ["shareAppMessage", "shareTimeline"] })
    if (wx.hideOptionMenu) wx.hideOptionMenu()
  },
})
