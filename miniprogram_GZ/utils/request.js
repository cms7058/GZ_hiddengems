const config = require("./config")

const SERVICE_CLOSED_CODE = "SERVICE_CLOSED"
const DEFAULT_SERVICE_HOURS = {
  enabled: false,
  open_hour: 8,
  close_hour: 24,
}

let serviceHours = { ...DEFAULT_SERVICE_HOURS }
let serviceHoursLoaded = false
let serviceHoursPromise = null
let hasShownClosedNotice = false

function getBeijingHour(date = new Date()) {
  return new Date(date.getTime() + 8 * 60 * 60 * 1000).getUTCHours()
}

function normalizeServiceHours(data = {}) {
  const openHour = Number(data.open_hour)
  const closeHour = Number(data.close_hour)
  if (!Number.isInteger(openHour) || !Number.isInteger(closeHour) || openHour < 0 || openHour >= closeHour || closeHour > 24) {
    return { ...DEFAULT_SERVICE_HOURS }
  }
  return {
    enabled: data.enabled === true || data.enabled === "true",
    open_hour: openHour,
    close_hour: closeHour,
  }
}

function applyServiceHours(data) {
  serviceHours = normalizeServiceHours(data)
  return serviceHours
}

function preloadServiceHours(force = false) {
  if (serviceHoursLoaded && !force) return Promise.resolve(serviceHours)
  if (serviceHoursPromise) return serviceHoursPromise

  serviceHoursPromise = new Promise((resolve) => {
    const finish = () => {
      serviceHoursLoaded = true
      serviceHoursPromise = null
      resolve(serviceHours)
    }
    wx.request({
      url: `${config.apiBaseUrl}/mini/service-hours`,
      method: "GET",
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          applyServiceHours(res.data)
        }
        finish()
      },
      fail: finish,
    })
  })
  return serviceHoursPromise
}

function isServiceOpen(date = new Date(), hours = serviceHours) {
  if (!hours.enabled) return true
  const hour = getBeijingHour(date)
  return hour >= hours.open_hour && hour < hours.close_hour
}

function getLanguage() {
  try {
    return getApp().globalData.lang || "zh-CN"
  } catch (error) {
    return "zh-CN"
  }
}

function resolveMediaUrl(url) {
  if (!url || !String(url).startsWith("/")) return url
  return `${config.apiBaseUrl.replace(/\/api\/v1$/, "")}${url}`
}

function serviceHoursText(hours = serviceHours) {
  const start = `${String(hours.open_hour).padStart(2, "0")}:00`
  const end = `${String(hours.close_hour).padStart(2, "0")}:00`
  return `${start}-${end}`
}

function createServiceClosedError() {
  const error = new Error(`Backend data service is available from ${serviceHoursText()} Beijing time`)
  error.code = SERVICE_CLOSED_CODE
  return error
}

function showServiceClosedNotice() {
  if (hasShownClosedNotice) return
  hasShownClosedNotice = true
  const isEnglish = getLanguage() === "en-US"
  const hoursText = serviceHoursText()
  wx.showModal({
    title: isEnglish ? "Service Hours" : "服务时间提醒",
    content: isEnglish
      ? `For exploration safety, data is available daily from ${hoursText} Beijing time. Please return during service hours.`
      : `为保障探秘安全，后台数据服务开放时间为每天北京时间 ${hoursText}。当前不在开放时段，请在开放时间内使用。`,
    showCancel: false,
    confirmText: isEnglish ? "OK" : "我知道了",
  })
}

function checkServiceHours() {
  if (isServiceOpen()) return null
  showServiceClosedNotice()
  return createServiceClosedError()
}

function notifyServiceClosedIfNeeded() {
  return checkServiceHours()
}

function isServiceClosedError(error) {
  return Boolean(error && error.code === SERVICE_CLOSED_CODE)
}

function applyServiceHoursFromError(data) {
  if (data && data.code === SERVICE_CLOSED_CODE) {
    applyServiceHours({
      enabled: true,
      open_hour: data.open_hour,
      close_hour: data.close_hour,
    })
    showServiceClosedNotice()
  }
}

function request(path, options = {}) {
  return preloadServiceHours().then(() => {
    const serviceClosedError = checkServiceHours()
    if (serviceClosedError) return Promise.reject(serviceClosedError)

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
          const detail = res.data && (res.data.detail || res.data.message)
          const errorText = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : "")
          const error = new Error(errorText || `request failed: ${res.statusCode}`)
          error.statusCode = res.statusCode
          if (res.data && res.data.code === SERVICE_CLOSED_CODE) {
            error.code = SERVICE_CLOSED_CODE
            applyServiceHoursFromError(res.data)
          }
          reject(error)
        },
        fail: reject,
      })
    })
  })
}

function miniLogin(payload) {
  return new Promise((resolve, reject) => {
    const url = `${config.apiBaseUrl}/mini/login`
    wx.request({
      url,
      method: "POST",
      data: payload,
      header: {
        "content-type": "application/json",
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
          const detail = res.data && (res.data.detail || res.data.message)
          const text = typeof detail === "string" ? detail : (detail ? JSON.stringify(detail) : "")
          reject(new Error(text || `login failed: ${res.statusCode}`))
      },
      fail(error) {
        reject(new Error(`login request failed: ${url} ${error.errMsg || ""}`))
      },
    })
  })
}

function uploadMedia(filePath, mediaType = "") {
  return preloadServiceHours().then(() => {
    const serviceClosedError = checkServiceHours()
    if (serviceClosedError) return Promise.reject(serviceClosedError)

    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: `${config.apiBaseUrl}/mini/uploads`,
        filePath,
        name: "file",
        formData: {
          user_id: getApp().globalData.user.id,
          media_type: mediaType,
        },
        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(JSON.parse(res.data))
            } catch (error) {
              reject(error)
            }
            return
          }
          let detail = ""
          try {
            const responseData = typeof res.data === "string" ? JSON.parse(res.data) : res.data
            detail = responseData && (responseData.detail || responseData.message || "")
            if (responseData && responseData.code === SERVICE_CLOSED_CODE) {
              error.code = SERVICE_CLOSED_CODE
              applyServiceHoursFromError(responseData)
            }
          } catch (parseError) {
            // Keep the original upload error when the response is not JSON.
          }
          const error = new Error(detail || `upload failed: ${res.statusCode}`)
          reject(error)
        },
        fail: reject,
      })
    })
  })
}

module.exports = {
  isServiceOpen,
  isServiceClosedError,
  miniLogin,
  notifyServiceClosedIfNeeded,
  preloadServiceHours,
  request,
  resolveMediaUrl,
  uploadMedia,
}
