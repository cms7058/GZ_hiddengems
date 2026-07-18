const app = getApp()
const { isServiceClosedError, request } = require("../../utils/request")

const COPY = {
  "zh-CN": {
    title: "小助手",
    headline: "西部觅境小助手",
    subtitle: "基于已审核秘境资料和你的个人记录提供查询服务。",
    input: "例如：巴喇谷介绍、我的积分、怎么去加榜梯田",
    send: "发送",
    thinking: "正在查询资料…",
    welcome: "你好，我可以查询景点介绍、人文地理、路线导航提示，以及你自己的积分、打卡和权限。",
    empty: "请输入想查询的问题",
    failed: "查询失败，请稍后重试",
    navigate: "打开地图导航",
  },
  "en-US": {
    title: "Assistant",
    headline: "Western Gems Assistant",
    subtitle: "Searches approved gem records and your own activity data.",
    input: "For example: Introduce Balagu, my points, route to Jia Bang",
    send: "Send",
    thinking: "Searching records…",
    welcome: "Hi, I can look up gem introductions, culture, route guidance, and your own points, check-ins, and permissions.",
    empty: "Enter a question first",
    failed: "Search failed. Try again later.",
    navigate: "Open navigation",
  },
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    inputValue: "",
    messages: [],
    thinking: false,
    messageAnchor: "",
  },

  onShow() {
    app.rememberTab("pages/assistant/assistant")
    this.refreshCopy()
  },

  onPullDownRefresh() {
    this.refreshCopy()
    wx.stopPullDownRefresh()
  },

  onLanguageChanged() {
    this.refreshCopy()
  },

  refreshCopy() {
    const lang = app.globalData.lang || "zh-CN"
    const copy = COPY[lang]
    const messages = this.data.messages.length
      ? this.data.messages
      : [{ id: "welcome", role: "assistant", content: copy.welcome, actions: [], suggestions: [] }]
    this.setData({ lang, copy, messages })
    app.applyTabBarLanguage()
  },

  onInputChange(event) {
    this.setData({ inputValue: event.detail.value })
  },

  scrollToLatest(messageAnchor) {
    this.setData({ messageAnchor })
  },

  async onSendTap() {
    const content = (this.data.inputValue || "").trim()
    if (!content || this.data.thinking) {
      if (!content) wx.showToast({ title: this.data.copy.empty, icon: "none" })
      return
    }
    const user = app.globalData.user || {}
    if (!user.id) {
      wx.showToast({ title: this.data.copy.failed, icon: "none" })
      return
    }
    const userMessageId = `user-${Date.now()}`
    const messages = this.data.messages.concat({ id: userMessageId, role: "user", content })
    this.setData({ messages, inputValue: "", thinking: true })
    this.scrollToLatest(userMessageId)
    try {
      const result = await request("/mini/assistant/query", {
        method: "POST",
        data: { user_id: user.id, query: content, lang: this.data.lang },
      })
      const assistantMessageId = `assistant-${Date.now()}`
      this.setData({
        messages: this.data.messages.concat({
          id: assistantMessageId,
          role: "assistant",
          content: result.answer || this.data.copy.failed,
          actions: result.actions || [],
          suggestions: result.suggestions || [],
        }),
      })
      this.scrollToLatest(assistantMessageId)
    } catch (error) {
      if (!isServiceClosedError(error)) {
        const errorMessageId = `assistant-error-${Date.now()}`
        this.setData({
          messages: this.data.messages.concat({
            id: errorMessageId,
            role: "assistant",
            content: error.message || this.data.copy.failed,
            actions: [],
            suggestions: [],
          }),
        })
        this.scrollToLatest(errorMessageId)
      }
    } finally {
      this.setData({ thinking: false })
    }
  },

  onSuggestionTap(event) {
    const name = event.currentTarget.dataset.name
    if (!name) return
    this.setData({ inputValue: `${name}${this.data.lang === "en-US" ? " introduction" : "介绍"}` })
  },

  onAssistantAction(event) {
    const action = event.currentTarget.dataset.action || {}
    if (action.type !== "navigate") return
    wx.openLocation({
      latitude: Number(action.latitude),
      longitude: Number(action.longitude),
      name: action.name || "",
      scale: 14,
      fail: () => wx.showToast({ title: this.data.copy.failed, icon: "none" }),
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
