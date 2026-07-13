const iconCache = {}
const pendingIcons = {}
let drawingQueue = Promise.resolve()

function normalizeMarkerColor(color) {
  return /^#[0-9a-fA-F]{6}$/.test(color || "") ? color.toLowerCase() : "#2f6b4f"
}

function drawMarkerIcon(page, canvasId, color) {
  return new Promise((resolve, reject) => {
    const context = wx.createCanvasContext(canvasId, page)
    const width = 80
    const height = 100
    context.clearRect(0, 0, width, height)

    // A compact map pin with a white center keeps the level color readable.
    context.setFillStyle(color)
    context.beginPath()
    context.moveTo(40, 94)
    context.bezierCurveTo(31, 79, 12, 57, 12, 35)
    context.arc(40, 35, 28, Math.PI, 0, false)
    context.bezierCurveTo(68, 57, 49, 79, 40, 94)
    context.closePath()
    context.fill()

    context.setFillStyle("#ffffff")
    context.beginPath()
    context.arc(40, 35, 9, 0, Math.PI * 2, false)
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
