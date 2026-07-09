const config = require("./config")

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${config.apiBaseUrl}${path}`,
      method: options.method || "GET",
      data: options.data || {},
      header: {
        "content-type": "application/json",
        ...(options.header || {}),
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        reject(new Error(`request failed: ${res.statusCode}`))
      },
      fail: reject,
    })
  })
}

function uploadMedia(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${config.apiBaseUrl}/mini/uploads`,
      filePath,
      name: "file",
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(res.data))
          } catch (error) {
            reject(error)
          }
          return
        }
        reject(new Error(`upload failed: ${res.statusCode}`))
      },
      fail: reject,
    })
  })
}

module.exports = {
  request,
  uploadMedia,
}
