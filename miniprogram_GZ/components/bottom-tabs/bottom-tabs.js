const COPY = {
  "zh-CN": {
    home: "首页",
    assistant: "小助手",
    mine: "我的",
    language: "EN",
  },
  "en-US": {
    home: "Home",
    assistant: "Assistant",
    mine: "My",
    language: "中",
  },
}

Component({
  properties: {
    lang: {
      type: String,
      value: "zh-CN",
    },
  },

  data: {
    copy: COPY["zh-CN"],
  },

  observers: {
    lang(value) {
      this.setData({ copy: COPY[value] || COPY["zh-CN"] })
    },
  },

  lifetimes: {
    attached() {
      this.setData({ copy: COPY[this.data.lang] || COPY["zh-CN"] })
    },
  },

  methods: {
    goHome() {
      wx.switchTab({ url: "/pages/index/index" })
    },
    goAssistant() {
      wx.switchTab({ url: "/pages/assistant/assistant" })
    },
    goMine() {
      wx.switchTab({ url: "/pages/user/user" })
    },
    toggleLanguage() {
      getApp().toggleLanguage()
    },
  },
})
