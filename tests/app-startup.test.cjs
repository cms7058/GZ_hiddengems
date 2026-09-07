const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')

for (const broken of [true, false]) {
  test(`App registers and opens with notification module ${broken ? 'missing' : 'available'}`, () => {
    let app
    let started = 0
    let stopped = 0
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../miniprogram_GZ/app.js'), 'utf8'), {
      App: (options) => { app = options },
      console: { warn() {} },
      require: (name) => {
        if (name === './utils/request') return {}
        if (broken) throw new Error('module is not defined')
        return { start: () => started++, stop: () => stopped++ }
      },
    })
    assert.ok(app)
    app.captureReferrerToken = () => false
    assert.doesNotThrow(() => app.onShow())
    assert.doesNotThrow(() => app.onHide())
    assert.equal(started, broken ? 0 : 1)
    assert.equal(stopped, broken ? 0 : 1)
  })
}
