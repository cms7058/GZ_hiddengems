const { request } = require("../../utils/request")
const app = getApp()

Page({
  data: {
    tabs: [
      { key: "spot_unlock", label: "秘境解锁" },
      { key: "food", label: "美食兑换" },
      { key: "advanced", label: "高阶探索" },
    ],
    activeTab: "spot_unlock",
    catalog: [],
    spotUnlocks: [],
    visible: [],
    summary: { benefit_points: 0, explore_points: 0, ledgers: [], redemptions: [] },
  },

  onLoad() { this.load() },

  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()) },

  async load() {
    let user = app.globalData.user || {}
    try {
      user = await app.bootstrapUser({ force: true })
      if (!user || !user.id || !user.openid) throw new Error("用户信息尚未同步")
      const summary = await request(`/benefits/me/${user.id}`)
      app.globalData.user = {
        ...user,
        benefit_points: summary.benefit_points,
        explore_points: summary.explore_points,
      }
      wx.setStorageSync("gzHiddenGemsUser", app.globalData.user)
      this.setData({ summary }, () => this.filter())
      const [catalog, spotUnlocks] = await Promise.all([
        request("/benefits/catalog").catch(() => []),
        request(`/benefits/spot-unlocks/${user.id}?lang=${app.globalData.lang || "zh-CN"}`).catch((error) => {
          console.warn("spot unlock candidates unavailable", error)
          return []
        }),
      ])
      this.setData({ catalog, summary, spotUnlocks }, () => this.filter())
    } catch (error) {
      wx.showModal({
        title: "获取权益失败",
        content: error.message || "用户信息与后台同步失败，请稍后重试",
        showCancel: false,
      })
    }
  },

  filter() {
    const visible = this.data.activeTab === "spot_unlock"
      ? this.data.spotUnlocks.map((item) => ({ ...item, id: item.benefit_id, isSpotUnlock: true }))
      : this.data.catalog.filter((item) => item.category === this.data.activeTab)
    this.setData({ visible })
  },

  onTab(event) {
    this.setData({ activeTab: event.currentTarget.dataset.key }, () => this.filter())
  },

  onRedeem(event) {
    const item = this.data.visible.find((entry) => entry.id === Number(event.currentTarget.dataset.id))
    if (!item) return
    if (this.data.summary.benefit_points < item.points_cost) {
      wx.showToast({ title: "可用积分不足", icon: "none" })
      return
    }
    const action = item.isSpotUnlock ? `解锁 ${item.name}` : item.name_zh
    wx.showModal({
      title: "确认兑换",
      content: `将扣除 ${item.points_cost} 积分，${action}`,
      success: async (result) => {
        if (!result.confirm) return
        try {
          await request("/benefits/redeem", {
            method: "POST",
            data: { user_id: app.globalData.user.id, benefit_id: item.id },
          })
          wx.showToast({ title: "兑换成功" })
          this.load()
        } catch (error) {
          wx.showModal({ title: "兑换失败", content: error.message || "请稍后重试", showCancel: false })
        }
      },
    })
  },
})
