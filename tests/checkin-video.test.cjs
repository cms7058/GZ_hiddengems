const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')

function setup() {
  let page
  const calls = { uploads: 0, requests: [], notices: [] }
  const wx = {
    showToast: (value) => calls.notices.push(value),
    showModal: (value) => calls.notices.push(value),
    createVideoContext: () => ({ pause() {} }),
    chooseVideo: (options) => {
      calls.camera = options
      options.success({ tempFilePath: 'local.mp4', duration: 3, size: 1000 })
    },
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../miniprogram_GZ/pages/spot-submit/spot-submit.js'), 'utf8'), {
    Page: (value) => { page = value }, wx, console,
    getApp: () => ({ globalData: { user: { id: 1 } } }),
    require: () => ({
      resolveMediaUrl: (url) => url,
      isServiceClosedError: () => false,
      uploadMedia: async () => { calls.uploads++; return { media_url: '/media/test.mp4' } },
      request: async (url, options) => {
        calls.requests.push(options.data)
        if (calls.failRequest) throw new Error('network failure')
        return { status: 'approved', review_note: 'OK' }
      },
    }),
  })
  page.setData = (values) => Object.assign(page.data, values)
  page.data.spot = { id: 7 }
  page.loadSpot = async () => {}
  page.getLocation = async () => ({ latitude: 26, longitude: 106 })
  return { page, wx, calls }
}

test('camera-only three-second recording is uploaded only on submission', async () => {
  const { page, calls } = setup()
  await page.onChooseCheckinVideo()
  assert.equal(calls.camera.maxDuration, 3)
  assert.deepEqual(Array.from(calls.camera.sourceType), ['camera'])
  assert.equal(page.data.checkinMedia[0].tempFilePath, 'local.mp4')
  assert.equal(calls.uploads, 0)
  await page.onSubmitCheckin()
  assert.equal(calls.uploads, 1)
  assert.equal(calls.requests[0].media_type, 'video')
  assert.equal(calls.requests[0].video_duration, 3)
  assert.equal(calls.requests[0].image_url, undefined)
  assert.equal(page.data.checkinMedia.length, 0)
})

test('cancelled or invalid retake preserves previous video', async () => {
  const { page, wx, calls } = setup()
  await page.onChooseCheckinVideo()
  wx.chooseVideo = (options) => options.fail({ errMsg: 'chooseVideo:fail cancel' })
  await page.onChooseCheckinVideo()
  assert.equal(calls.notices.length, 0)
  for (const duration of [1, 10, NaN]) {
    wx.chooseVideo = (options) => options.success({ tempFilePath: 'invalid.mp4', duration })
    await page.onChooseCheckinVideo()
    assert.equal(page.data.checkinMedia[0].tempFilePath, 'local.mp4')
  }
  assert.equal(page.data.choosingVideo, false)
})

test('failed submission clears video and requires recording again', async () => {
  const { page, calls } = setup()
  await page.onChooseCheckinVideo()
  calls.failRequest = true
  await page.onSubmitCheckin()
  assert.equal(page.data.checkinMedia.length, 0)
  assert.equal(page.data.submitting, false)
  calls.failRequest = false
  await page.onSubmitCheckin()
  assert.equal(calls.uploads, 1)
  assert.equal(calls.requests.length, 1)
  await page.onChooseCheckinVideo()
  await page.onSubmitCheckin()
  assert.equal(calls.uploads, 2)
  assert.equal(page.data.checkinMedia.length, 0)
})

test('empty video and denied recording permission do not submit', async () => {
  const { page, calls } = setup()
  await page.onSubmitCheckin()
  page.data.user.can_upload_video = false
  await page.onChooseCheckinVideo()
  assert.equal(calls.camera, undefined)
  assert.equal(calls.requests.length, 0)
})

test('draft video has no playback element before successful submission', () => {
  const wxml = fs.readFileSync(path.join(__dirname, '../miniprogram_GZ/pages/spot-submit/spot-submit.wxml'), 'utf8')
  assert.equal(wxml.includes('id="checkin-preview"'), false)
  assert.ok(wxml.includes("item.media_type === 'video' && item.media_url"))
})
