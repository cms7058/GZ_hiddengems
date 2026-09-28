const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')

function setup(mode = 'eco') {
  let page
  const calls = []
  let records = []
  const policy = { min_photos: 1, max_photos: 3, max_video_seconds: 3, reward_points: 5 }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../miniprogram_GZ/pages/community/community.js'), 'utf8'), {
    Page: (options) => { page = options },
    require: () => ({
      resolveMediaUrl: (url) => url,
      communityUpload: async (...args) => { calls.push(['upload', ...args]); return { id: 10 } },
      communityRequest: async (url, options) => {
        calls.push([url, options])
        if (url === '/summary') return { food_policy: policy }
        if (options) { records = [{ id: 1, status: 'pending', media: [] }]; return records[0] }
        if (url.startsWith('/eco')) return records
        return []
      },
    }),
    wx: {
      chooseVideo: (options) => { assert.equal(options.maxDuration, 3); options.success({ duration: 3, size: 1024, tempFilePath: 'camera.mp4' }) },
      showModal: (options) => calls.push(['modal', options]),
    },
  })
  page.setData = (values) => Object.assign(page.data, values)
  page.onLoad({ mode, id: 7 })
  return { page, calls }
}

test('eco selector, recording, submit and pending block work together', async () => {
  const { page, calls } = setup()
  await page.load()
  page.onCategory({ detail: { value: 2 } })
  await page.onRecord()
  await page.onSubmit()
  const payload = calls.find(([url, options]) => url === '/eco' && options)[1].data
  assert.equal(payload.category, 'C')
  assert.equal(payload.spot_id, 7)
  assert.equal(payload.upload_id, 10)
  assert.equal(page.data.blocked, true)
  assert.equal(page.data.video, null)
  const count = calls.length
  await page.onSubmit()
  assert.equal(calls.length, count)
})

test('food missing photos is blocked, filled form uploads and submits once', async () => {
  const { page, calls } = setup('food')
  await page.load()
  await page.onSubmit()
  assert.equal(calls.filter(([url, options]) => url === '/food' && options).length, 0)
  page.onTitle({ detail: { value: 'Food' } }); page.onContent({ detail: { value: 'Description' } })
  page.setData({ photos: [{ tempFilePath: 'food.jpg' }] })
  await page.onSubmit()
  assert.equal(calls.filter(([url, options]) => url === '/food' && options).length, 1)
  assert.equal(page.data.photos.length, 0)
})
