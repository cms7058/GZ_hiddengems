const { request } = require("./request")
const config = require("./config")

let loginPromise = null
async function token(force = false) {
  const app = getApp()
  if (force || !app.globalData.user.community_token) {
    if (!loginPromise) loginPromise = app.bootstrapUser({ force: true }).finally(() => { loginPromise = null })
    await loginPromise
  }
  const value = app.globalData.user.community_token
  if (!value) throw new Error("请重新登录后再试")
  return value
}

async function communityRequest(path, options = {}) {
  const send = async (force) => request(`/mini/community${path}`, { ...options, header: { Authorization: `Bearer ${await token(force)}` } })
  try { return await send(false) } catch (error) {
    if (error.statusCode === 401) return send(true)
    throw error
  }
}

async function communityUpload(filePath, purpose, mediaType) {
  const accessToken = await token()
  return new Promise((resolve, reject) => wx.uploadFile({
    url: `${config.apiBaseUrl}/mini/community/uploads`, filePath, name: "file",
    header: { Authorization: `Bearer ${accessToken}` }, formData: { purpose, media_type: mediaType },
    success(res) {
      try {
        const data = JSON.parse(res.data)
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(data)
        else reject(new Error(typeof data.detail === "string" ? data.detail : "上传失败，请重试"))
      } catch (error) { reject(error) }
    }, fail: reject,
  }))
}

module.exports = { communityRequest, communityUpload }
