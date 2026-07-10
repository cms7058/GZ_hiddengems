const NAV_TEXT = {
  "zh-CN": {
    systemMap: "选择地图 App 导航",
    twoSteps: "两步路户外助手--记录",
    twoStepsTitle: "两步路接入未配置",
    twoStepsContent:
      "暂未获得两步路官方接入信息。可先选择已安装的地图 App 进行导航。",
    openMapApp: "选择地图 App",
    cancel: "取消",
    mapUnavailableTitle: "无法打开地图 App",
    mapUnavailableContent: "请更新微信并安装可用的地图 App 后重试。为保护秘境位置信息，系统不会打开微信内置位置页。",
  },
  "en-US": {
    systemMap: "Choose a Map App",
    twoSteps: "2bulu Outdoor--Record",
    twoStepsTitle: "2bulu integration missing",
    twoStepsContent:
      "2bulu has not provided an approved integration. Choose an installed map app for navigation instead.",
    openMapApp: "Choose Map App",
    cancel: "Cancel",
    mapUnavailableTitle: "Map app unavailable",
    mapUnavailableContent: "Update WeChat and install a supported map app, then try again. The built-in WeChat location page will not be opened to protect spot data.",
  },
}

function showMapUnavailable(text) {
  wx.showModal({
    title: text.mapUnavailableTitle,
    content: text.mapUnavailableContent,
    showCancel: false,
  })
}

function openMapApp({ spot, mapId, page, text }) {
  if (!wx.createMapContext || !mapId || !page) {
    showMapUnavailable(text)
    return
  }

  const mapContext = wx.createMapContext(mapId, page)
  if (!mapContext || typeof mapContext.openMapApp !== "function") {
    showMapUnavailable(text)
    return
  }

  mapContext.openMapApp({
    latitude: Number(spot.latitude),
    longitude: Number(spot.longitude),
    destination: spot.name,
    fail: (error) => {
      if (String((error && error.errMsg) || "").toLowerCase().includes("cancel")) return
      showMapUnavailable(text)
    },
  })
}

function chooseNavigationApp({ spot, mapId, page, lang = "zh-CN" }) {
  const text = NAV_TEXT[lang] || NAV_TEXT["zh-CN"]
  wx.showActionSheet({
    itemList: [text.systemMap, text.twoSteps],
    success(res) {
      if (res.tapIndex === 0) {
        openMapApp({ spot, mapId, page, text })
        return
      }

      wx.showModal({
        title: text.twoStepsTitle,
        content: text.twoStepsContent,
        confirmText: text.openMapApp,
        cancelText: text.cancel,
        success(modalRes) {
          if (modalRes.confirm) {
            openMapApp({ spot, mapId, page, text })
          }
        },
      })
    },
  })
}

module.exports = {
  chooseNavigationApp,
}
