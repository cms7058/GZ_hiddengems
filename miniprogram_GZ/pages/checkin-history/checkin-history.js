const app = getApp()
const { request, isServiceClosedError } = require("../../utils/request")

const COPY = {
  "zh-CN": {
    title: "我的打卡",
    empty: "暂无打卡记录",
    points: "获得积分",
    review: "系统结论",
    risk: "路线风险",
    approved: "打卡成功",
    rejected: "未通过",
    pending: "待审核",
    normal: "正常",
    warning: "警告",
    suspicious: "可疑",
    watch: "重点关注",
    loadFailed: "打卡记录加载失败",
  },
  "en-US": {
    title: "My Check-ins",
    empty: "No check-in records yet",
    points: "Points earned",
    review: "System result",
    risk: "Route risk",
    approved: "Successful",
    rejected: "Not passed",
    pending: "Pending",
    normal: "Normal",
    warning: "Warning",
    suspicious: "Suspicious",
    watch: "Watch",
    loadFailed: "Could not load check-ins",
  },
}

function formatTime(value) {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).replace("T", " ").slice(0, 16)
  const two = (number) => String(number).padStart(2, "0")
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())} ${two(date.getHours())}:${two(date.getMinutes())}`
}

Page({
  data: {
    lang: "zh-CN",
    copy: COPY["zh-CN"],
    records: [],
    loading: false,
  },

  onShow() {
    this.setData({ lang: app.globalData.lang || "zh-CN", copy: COPY[app.globalData.lang || "zh-CN"] })
    this.load()
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh())
  },

  async load() {
    const user = app.globalData.user || {}
    if (!user.id || this.data.loading) return
    this.setData({ loading: true })
    try {
      const records = await request(`/mini/users/${user.id}/checkins`)
      this.setData({
        records: records.map((record) => ({
          ...record,
          createdText: formatTime(record.created_at),
          statusText: this.data.copy[record.status] || record.status,
          riskText: this.data.copy[record.risk_status] || record.risk_status || this.data.copy.normal,
        })),
      })
    } catch (error) {
      if (!isServiceClosedError(error)) wx.showToast({ title: this.data.copy.loadFailed, icon: "none" })
    } finally {
      this.setData({ loading: false })
    }
  },
})
