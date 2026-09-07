const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')

test('review notices are user-scoped, deduplicated and paused in background', async () => {
  const storage = {}
  let interval
  let requests = 0
  const messages = []
  const app = { globalData: { user: { id: 1 }, lang: 'zh-CN' } }
  const module = { exports: {} }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../miniprogram_GZ/utils/checkin-notices.js'), 'utf8'), {
    module, console, getApp: () => app,
    setInterval: (fn) => { interval = fn; return 1 }, clearInterval() {},
    require: () => ({ request: async (url) => {
      requests++
      assert.ok(url.includes(`/users/${app.globalData.user.id}/`))
      return [
        { id: 7, media_type: 'video', status: 'approved', reviewed_at: '2026-09-07', spot_name_zh: 'Test' },
        { id: 8, media_type: 'video', status: 'pending' },
      ]
    } }),
    wx: {
      getStorageSync: (key) => storage[key],
      setStorageSync: (key, value) => { storage[key] = value },
      showModal: (options) => { messages.push(options); options.success(); options.complete() },
    },
  })
  module.exports.start()
  await new Promise(setImmediate)
  assert.equal(messages.length, 1)
  await interval()
  assert.equal(messages.length, 1)
  app.globalData.user.id = 2
  await interval()
  assert.equal(messages.length, 2)
  module.exports.stop()
  const previous = requests
  await interval()
  assert.equal(requests, previous)
})
