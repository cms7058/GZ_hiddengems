const app = getApp()

const COPY = {
  "zh-CN": {
    title: "智能小助手",
    headline: "秘境 AI 小助手",
    subtitle: "后续可接入路线建议、装备清单、风险提醒和中英文问答。",
    input: "想问点什么？",
    send: "发送",
    message: "你好，我可以帮你规划贵州秘境探索路线。",
  },
  "en-US": {
    title: "AI Assistant",
    headline: "Hidden Gems AI",
    subtitle: "Route planning, gear lists, risk alerts, and bilingual Q&A will be connected here.",
    input: "Ask anything",
    send: "Send",
    message: "Hi, I can help you plan a Guizhou hidden gem route.",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    inputValue: "",
    messages: [],
  },

  onShow() {
    app.applyTabBarLanguage()
    const lang = app.globalData.lang || "zh-CN"
    this.setData({
      lang,
      copy: COPY[lang],
    })
  },

  onInputChange(event) {
    this.setData({ inputValue: event.detail.value })
  },

  onSendTap() {
    const content = (this.data.inputValue || "").trim()
    if (!content) {
      wx.showToast({ title: this.data.copy.input, icon: "none" })
      return
    }
    const messages = this.data.messages.concat({ id: Date.now(), content })
    this.setData({ messages, inputValue: "" })
    wx.showToast({
      title: this.data.copy.message,
      icon: "none",
    })
  },

  onFloatingBackTap() {
    const goHome = () => wx.switchTab({ url: "/pages/index/index" })
    if (getCurrentPages().length > 1) {
      wx.navigateBack({ delta: 1, fail: goHome })
      return
    }
    goHome()
  },
})
