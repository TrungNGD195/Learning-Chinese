import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const folder = resolve('../.impeccable/review/spatial-great-wall/step-input')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] })
const errors = [], unexpected = [], writes = [], checks = []
const snapshot = page => page.locator('.forward-viewport').evaluate(view => ({ progress: Number(view.dataset.progress), distance: Number(view.dataset.worldDistance), elevation: Number(view.dataset.elevation), eye: JSON.parse(view.dataset.worldPosition), level: view.dataset.level }))
async function settled(page) {
  await page.waitForTimeout(120)
  await page.waitForFunction(() => !document.querySelector('.forward-viewport')?.dataset.cameraMoving, undefined, { timeout: 60000 })
  await page.waitForTimeout(300)
}
async function ready(page, level = 1) {
  await page.locator(`.forward-viewport[data-level="${level}"][data-ready=true]`).waitFor({ timeout: 60000 })
  await page.evaluate(() => document.fonts.ready)
  await settled(page)
}
async function at(page, value) {
  await page.waitForFunction(value => Math.abs(Number(document.querySelector('.forward-viewport').dataset.progress) - value) < .0001, value, { timeout: 60000 })
  await settled(page)
  return snapshot(page)
}
async function capture(page, name, width) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  await page.screenshot({ path: `${folder}/${name}-${width}.png` })
}
async function wheel(page, delta) {
  const box = await page.locator('.forward-viewport').boundingBox()
  await page.mouse.move(box.x + box.width - 30, box.y + box.height / 2)
  await page.mouse.wheel(0, delta)
}
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 920 } })
    await installJourneyFixture(context, { unexpected, writes })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('http://127.0.0.1:5173/hsk/1', { waitUntil: 'domcontentloaded' })
    await ready(page)
    const base = await snapshot(page)
    assert.equal(base.distance, base.progress * 15, 'Updated compact world is running')
    await capture(page, 'compact-stairs', width)
    const up = page.getByRole('button', { name: 'Lên một bậc', exact: true })
    const down = page.getByRole('button', { name: 'Lùi một bậc', exact: true })
    await up.click()
    const first = await at(page, base.progress + .1)
    assert(Math.abs(first.distance - base.distance - 1.5) < .001, 'One button advances exactly one physical tread')
    assert(Math.abs(first.elevation - base.elevation - .675) < .001, 'Bo climbs the taller actual riser')
    await down.click();await at(page, base.progress)
    await wheel(page, -120);await at(page, base.progress + .1)
    await page.keyboard.press('ArrowDown');await at(page, base.progress)
    await page.keyboard.down('ArrowUp')
    await page.keyboard.down('ArrowUp')
    await page.keyboard.up('ArrowUp')
    await at(page, base.progress + .1)
    await page.locator('.forward-viewport').evaluate(view => {
      for (const deltaY of [-46, -24, -12, -3]) view.dispatchEvent(new WheelEvent('wheel', { deltaY, bubbles: true, cancelable: true }))
    })
    await at(page, base.progress + .2)
    await up.click();await up.click();await up.click()
    const queued = await at(page, base.progress + .5)
    await capture(page, 'five-steps', width)
    await wheel(page, 120);await at(page, base.progress + .4)
    await page.reload({ waitUntil: 'domcontentloaded' });await ready(page)
    assert(Math.abs((await snapshot(page)).progress - base.progress - .4) < .001, 'Reload retains tread position')
    await page.getByRole('button', { name: 'Xem toàn bộ lộ trình', exact: true }).click()
    await page.getByRole('button', { name: 'Định vị Phát âm trên Trường Thành', exact: true }).click()
    await ready(page);await at(page, 0)
    assert(await down.isDisabled())
    await wheel(page, 120);await at(page, 0)
    await page.keyboard.press('ArrowUp');await at(page, .1)
    assert(await down.isEnabled(), 'Back enables after the first tread, without waiting for a full gate')
    await page.getByRole('button', { name: 'Xem toàn bộ lộ trình', exact: true }).click()
    await page.getByRole('button', { name: 'Đến tháp canh HSK 1', exact: true }).click()
    await ready(page);const end1 = await at(page, 16)
    await capture(page, 'compact-milestone', width)
    await page.getByRole('link', { name: 'Đi đến HSK 2', exact: true }).click()
    await page.waitForURL('**/hsk/2');await ready(page, 2)
    const start2 = await at(page, .5)
    assert.equal(start2.distance, end1.distance+7.5)
    assert.equal(await page.locator('.forward-gate').count(), 10)
    await page.keyboard.press('ArrowUp')
    const hsk2Step = await at(page, .6)
    assert(Math.abs(hsk2Step.distance - start2.distance - 1.5) < .001)
    checks.push({ width, base, first, queued, end1, start2, hsk2Step })
    await context.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  assert.deepEqual(writes, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ checks, errors, unexpected, writes }, null, 2))
}
console.log('PASS: physical tread / taller riser, buttons, arrows, wheel and inertia, queued steps, bounds, reload and shared HSK milestone at desktop/mobile sizes.')
