const { request } = require("./request")

let timer = null
let active = false
let busy = false

async function poll() {
  if (!active || busy) return
  busy = true
  try {
    const app = getApp()
    const userId = app && app.globalData && app.globalData.user && app.globalData.user.id
    if (!userId) return
    if (app.globalData.user.community_token) {
      try {
        const { communityRequest } = require("./community-client")
        const notices = await communityRequest("/notices")
        if (!active || app.globalData.user.id !== userId) return
        const key = `gzCommunityNotices:${userId}`
        const read = wx.getStorageSync(key) || []
        const fresh = notices.filter((item) => !read.includes(item.key)).slice(0, 5)
        if (fresh.length) {
          await new Promise((resolve) => wx.showModal({
            title: "环保与美食审核通知",
            content: fresh.map((item) => `${item.kind === 'eco' ? '环保视频' : '美食推荐'} #${item.id}：${{ pending: '待审核', approved: '通过', rejected: '不通过' }[item.status]}\n${item.note || ''}`).join("\n\n"),
            showCancel: false,
            success: () => wx.setStorageSync(key, [...read, ...fresh.map((item) => item.key)].slice(-1000)), complete: resolve,
          }))
        }
      } catch (error) { console.warn("community notifications unavailable", error) }
    }
    const records = await request(`/mini/users/${userId}/checkins`)
    if (!active || !app.globalData.user || app.globalData.user.id !== userId || !Array.isArray(records)) return
    const key = `gzCheckinReviews:${userId}`
    const seen = wx.getStorageSync(key) || {}
    const results = records.filter((item) => item.media_type === "video" && item.reviewed_at && ["approved", "rejected"].includes(item.status) && seen[item.id] !== `${item.status}:${item.reviewed_at}`)
    if (!results.length) return
    const english = app.globalData.lang === "en-US"
    const batch = results.slice(0, 5)
    await new Promise((resolve) => wx.showModal({
      title: english ? "Check-in review results" : "打卡审核结果",
      content: batch.map((item) => `${item.spot_name_zh}: ${item.status === "approved" ? (english ? "Approved" : "审核通过") : (english ? "Rejected" : "未通过")}\n${item.review_note || ""}`).join("\n\n"),
      showCancel: false,
      success: () => {
        batch.forEach((item) => { seen[item.id] = `${item.status}:${item.reviewed_at}` })
        wx.setStorageSync(key, seen)
      },
      complete: resolve,
    }))
  } catch (error) {
    console.warn("check-in review notification unavailable", error)
  } finally {
    busy = false
  }
}

function start() {
  active = true
  if (!timer) timer = setInterval(poll, 30000)
  poll()
}

function stop() {
  active = false
  clearInterval(timer)
  timer = null
}

module.exports = { start, stop }
