const app = getApp()

Page({
  onShow() {
    const destination = app.globalData.lastTabPath || "pages/index/index"
    app.toggleLanguage()
    wx.switchTab({ url: `/${destination}` })
  },
})
