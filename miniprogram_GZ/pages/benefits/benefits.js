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
    selectedIds: [],
    selectedCount: 0,
    selectedPoints: 0,
    batchUnlocking: false,
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
    const selectedIds = new Set(this.data.selectedIds)
    const selectedItems = this.data.spotUnlocks.filter((item) => selectedIds.has(item.benefit_id) && !item.isUnlocked)
    const visible = this.data.activeTab === "spot_unlock"
      ? this.data.spotUnlocks.map((item) => ({
        ...item,
        id: item.benefit_id,
        isSpotUnlock: true,
        selected: selectedIds.has(item.benefit_id),
      }))
      : this.data.catalog.filter((item) => item.category === this.data.activeTab)
    this.setData({
      visible,
      selectedCount: selectedItems.length,
      selectedPoints: selectedItems.reduce((total, item) => total + Number(item.points_cost || 0), 0),
    })
  },

  onTab(event) {
    this.setData({ activeTab: event.currentTarget.dataset.key }, () => this.filter())
  },

  onToggleSpot(event) {
    const benefitId = Number(event.currentTarget.dataset.id)
    const item = this.data.spotUnlocks.find((entry) => entry.benefit_id === benefitId)
    if (!item || item.isUnlocked || this.data.batchUnlocking) return
    const selectedIds = this.data.selectedIds.slice()
    const selectedIndex = selectedIds.indexOf(benefitId)
    if (selectedIndex >= 0) selectedIds.splice(selectedIndex, 1)
    else selectedIds.push(benefitId)
    this.setData({ selectedIds }, () => this.filter())
  },

  onConfirmSpotUnlocks() {
    const selectedIds = this.data.selectedIds.slice()
    if (!selectedIds.length) return
    if (this.data.selectedPoints > Number(this.data.summary.benefit_points || 0)) {
      wx.showToast({ title: "可用积分不足", icon: "none" })
      return
    }
    wx.showModal({
      title: "确认解锁",
      content: `将解锁 ${this.data.selectedCount} 个秘境，扣除 ${this.data.selectedPoints} 积分`,
      success: async (result) => {
        if (!result.confirm) return
        try {
          this.setData({ batchUnlocking: true })
          const data = await request("/benefits/redeem-batch", {
            method: "POST",
            data: { user_id: app.globalData.user.id, benefit_ids: selectedIds },
          })
          const unlockedIds = new Set(selectedIds)
          const spotUnlocks = this.data.spotUnlocks.map((item) => (
            unlockedIds.has(item.benefit_id) ? { ...item, isUnlocked: true } : item
          ))
          const summary = {
            ...this.data.summary,
            benefit_points: data.benefit_points,
            redemptions: [...(data.redemptions || []), ...(this.data.summary.redemptions || [])],
          }
          app.globalData.user = { ...app.globalData.user, benefit_points: data.benefit_points }
          wx.setStorageSync("gzHiddenGemsUser", app.globalData.user)
          this.setData({ spotUnlocks, summary, selectedIds: [], batchUnlocking: false }, () => this.filter())
          wx.showToast({ title: "解锁成功" })
        } catch (error) {
          this.setData({ batchUnlocking: false })
          wx.showModal({ title: "解锁失败", content: error.message || "请稍后重试", showCancel: false })
        }
      },
    })
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
