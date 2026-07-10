const NAV_TEXT = {
  "zh-CN": {
    systemMap: "系统地图导航",
    twoSteps: "两步路户外助手--记录",
    twoStepsTitle: "两步路接入未配置",
    twoStepsContent:
      "微信小程序不能直接拉起任意第三方 App 并传递路线。请提供两步路官方 AppID、URL Scheme 或接入文档。当前可先打开系统位置页。",
    openLocation: "打开位置",
    cancel: "取消",
  },
  "en-US": {
    systemMap: "System Map",
    twoSteps: "2bulu Outdoor--Record",
    twoStepsTitle: "2bulu integration missing",
    twoStepsContent:
      "A WeChat mini program cannot launch an arbitrary third-party app with route parameters unless the app provides an approved integration. Provide the 2bulu AppID, URL scheme, or integration docs. For now, open the system location page.",
    openLocation: "Open Location",
    cancel: "Cancel",
  },
}

function openLocation(spot) {
  wx.openLocation({
    latitude: Number(spot.latitude),
    longitude: Number(spot.longitude),
    name: spot.name,
    address: [spot.city, spot.county, spot.summary].filter(Boolean).join(" "),
    scale: 16,
  })
}

function chooseNavigationApp({ spot, lang = "zh-CN" }) {
  const text = NAV_TEXT[lang] || NAV_TEXT["zh-CN"]
  wx.showActionSheet({
    itemList: [text.systemMap, text.twoSteps],
    success(res) {
      if (res.tapIndex === 0) {
        openLocation(spot)
        return
      }

      wx.showModal({
        title: text.twoStepsTitle,
        content: text.twoStepsContent,
        confirmText: text.openLocation,
        cancelText: text.cancel,
        success(modalRes) {
          if (modalRes.confirm) {
            openLocation(spot)
          }
        },
      })
    },
  })
}

module.exports = {
  chooseNavigationApp,
}
