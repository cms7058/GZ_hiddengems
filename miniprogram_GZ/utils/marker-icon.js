const iconCache = {}
const pendingIcons = {}
let drawingQueue = Promise.resolve()

function normalizeMarkerColor(color) {
  return /^#[0-9a-fA-F]{6}$/.test(color || "") ? color.toLowerCase() : "#2f6b4f"
}

function drawMarkerIcon(page, canvasId, color) {
  return new Promise((resolve, reject) => {
    const context = wx.createCanvasContext(canvasId, page)
    const width = 40
    const height = 50
    context.clearRect(0, 0, width, height)

    // A compact map pin with a white center keeps the level color readable.
    context.setFillStyle(color)
    context.beginPath()
    context.moveTo(20, 47)
    context.bezierCurveTo(15.5, 39.5, 6, 28.5, 6, 17.5)
    context.arc(20, 17.5, 14, Math.PI, 0, false)
    context.bezierCurveTo(34, 28.5, 24.5, 39.5, 20, 47)
    context.closePath()
    context.fill()

    context.setFillStyle("#ffffff")
    context.beginPath()
    context.arc(20, 17.5, 4.5, 0, Math.PI * 2, false)
    context.fill()

    context.draw(false, () => {
      wx.canvasToTempFilePath({
        canvasId,
        x: 0,
        y: 0,
        width,
        height,
        destWidth: width,
        destHeight: height,
        fileType: "png",
        success: (result) => resolve(result.tempFilePath),
        fail: reject,
      }, page)
    })
  })
}

function getMarkerIcon(page, canvasId, color) {
  const normalizedColor = normalizeMarkerColor(color)
  if (iconCache[normalizedColor]) return Promise.resolve(iconCache[normalizedColor])
  if (pendingIcons[normalizedColor]) return pendingIcons[normalizedColor]

  const task = drawingQueue
    .catch(() => undefined)
    .then(() => drawMarkerIcon(page, canvasId, normalizedColor))
    .then((iconPath) => {
      iconCache[normalizedColor] = iconPath
      return iconPath
    })
    .finally(() => {
      delete pendingIcons[normalizedColor]
    })

  pendingIcons[normalizedColor] = task
  drawingQueue = task
  return task
}

module.exports = {
  getMarkerIcon,
  normalizeMarkerColor,
}
