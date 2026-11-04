import { expect, test } from '@playwright/test'

const password = process.env.STEP81_TEST_PASSWORD
if (!password) throw new Error('Playwright global setup did not provide its ephemeral test password')
const learnerEmail = 'step81-learner@example.invalid'
const adminEmail = 'step81-admin@example.invalid'
const lessonA = '0e63a248-4b5a-5c14-aad6-dadd22b8a91d'
let r2ResultPath = ''

test('B1 new learner can complete required pronunciation flow and unlock Lesson A', async ({ page }) => {
  const email = `step81-new-${Date.now()}@example.invalid`
  await page.goto('/register')
  await page.getByLabel('Full name').fill('Step 8.1 New Learner')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByLabel('Confirm password').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.goto('/pronunciation')
  await expect(page.getByRole('heading', { name: 'Pronunciation Foundations' })).toBeVisible()
  for (const section of ['Tones', 'Initials', 'Finals']) {
    await page.getByRole('button', { name: `Mark ${section} complete` }).click()
    await expect(page.getByRole('heading', { name: section }).locator('..').getByText('Completed')).toBeVisible()
  }
  await page.goto('/dashboard')
  await expect(page.getByText('Lesson · AVAILABLE')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Step 8.1 Lesson A' })).toBeVisible()
  await page.getByRole('link', { name: 'Continue Learning' }).click()
  await expect(page).toHaveURL(new RegExp(`/lessons/${lessonA}$`))
  await expect(page.getByRole('heading', { name: 'Step 8.1 Lesson A' })).toBeVisible()
})

async function login(page, email: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(email === adminEmail ? /\/admin$/ : /\/dashboard$/)
}

async function expectD122Asset(page, selector: string, filename: string) {
  const backgroundImage = await page.locator(selector).evaluate((element) => getComputedStyle(element, '::after').backgroundImage)
  expect(backgroundImage).toContain(filename)
}

async function expectD123Background(page, selector: string, filename: string) {
  const backgroundImage = await page.locator(selector).evaluate((element) => getComputedStyle(element).backgroundImage)
  expect(backgroundImage).toContain(filename)
}

function splitCssLayerList(value: string) {
  const layers: string[] = []
  let depth = 0
  let start = 0
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === '(') depth += 1
    if (value[index] === ')') depth -= 1
    if (value[index] === ',' && depth === 0) {
      layers.push(value.slice(start, index).trim())
      start = index + 1
    }
  }
  layers.push(value.slice(start).trim())
  return layers
}

async function expectAdminBackgroundLayerAlignment(page, label: string, independentLeftArtworkHidden = false) {
  const styles = await page.locator('.admin-main').evaluate((element) => {
    const style = getComputedStyle(element)
    return { image: style.backgroundImage, size: style.backgroundSize, position: style.backgroundPosition }
  })
  console.info(`[admin background layers] ${label}: ${JSON.stringify(styles)}`)
  const imageLayers = splitCssLayerList(styles.image)
  expect(imageLayers).toHaveLength(5)
  expect(splitCssLayerList(styles.size)).toHaveLength(5)
  expect(splitCssLayerList(styles.position)).toHaveLength(5)
  if (independentLeftArtworkHidden) expect(imageLayers[3]).toBe('none')
}

async function expectD123BackgroundAbsent(page, selector: string, filename: string) {
  const backgroundImage = await page.locator(selector).evaluate((element) => getComputedStyle(element).backgroundImage)
  expect(backgroundImage).not.toContain(filename)
}

async function expectD123SingleAssetLayer(page, selector: string, filename: string) {
  const backgroundImage = await page.locator(selector).evaluate((element) => getComputedStyle(element).backgroundImage)
  expect(backgroundImage).toContain(filename)
  expect(backgroundImage.split(filename)).toHaveLength(2)
}

async function expectNoD123ArtworkOnElement(page, selector: string) {
  const backgroundImage = await page.locator(selector).evaluate((element) => getComputedStyle(element).backgroundImage)
  expect(backgroundImage).not.toContain('d122-')
}

async function expectD123PseudoSuppressed(page, selector: string, filename: string) {
  const pseudo = await page.locator(selector).evaluate((element) => {
    const style = getComputedStyle(element, '::after')
    return { display: style.display, backgroundImage: style.backgroundImage }
  })
  expect(pseudo.display === 'none' || !pseudo.backgroundImage.includes(filename)).toBe(true)
}

async function expectNoD122Background(page, selector: string) {
  const hasArtwork = await page.evaluate((targetSelector) => {
    const roots = Array.from(document.querySelectorAll(targetSelector))
    return roots.some((root) => {
      const elements = [root, ...root.querySelectorAll('*')]
      return elements.some((element) => {
        const own = getComputedStyle(element).backgroundImage
        const before = getComputedStyle(element, '::before').backgroundImage
        const after = getComputedStyle(element, '::after').backgroundImage
        return `${own} ${before} ${after}`.includes('d122-')
      })
    })
  }, selector)
  expect(hasArtwork).toBe(false)
}

async function captureD123Screenshot(page, testInfo, name: string, fullPage = false) {
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), animations: 'disabled', fullPage })
}

async function expectNoPageOverflow(page) {
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)
}

test('D-120 strictly separates Learner and Admin routes while preserving both sessions', async ({ page, browser }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login$/)
  await page.goto('/admin')
  await expect(page).toHaveURL(/\/login$/)

  await login(page, learnerEmail)
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.goto('/admin')
  await expect(page.getByTestId('admin-forbidden')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Back to Dashboard' })).toHaveAttribute('href', '/dashboard')
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  const adminContext = await browser.newContext()
  const adminPage = await adminContext.newPage()
  await login(adminPage, adminEmail)
  await expect(adminPage.getByRole('heading', { name: 'Admin Dashboard' })).toBeVisible()
  await adminPage.goto('/dashboard')
  await expect(adminPage.getByTestId('learner-forbidden')).toBeVisible()
  await expect(adminPage.getByRole('link', { name: 'Go to Admin Dashboard' })).toHaveAttribute('href', '/admin')
  await adminPage.goto('/admin')
  await expect(adminPage.getByRole('heading', { name: 'Admin Dashboard' })).toBeVisible()
  await adminContext.close()
})

test('B3 Lesson Chat remains Lesson-scoped and persisted after refresh', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto(`/lessons/${lessonA}`)
  await expect(page.getByRole('heading', { name: 'Step 8.1 Lesson A' })).toBeVisible()
  await page.getByRole('button', { name: 'Open AI chat' }).click()
  await expect(page.getByRole('heading', { name: 'AI Chat' })).toBeVisible()
  await expect(page.getByText('HSK 1 · Lesson 1').first()).toBeVisible()
  await page.getByRole('button', { name: 'Start a conversation' }).click()
  await page.getByRole('textbox', { name: 'Message' }).fill('What does 你好 mean?')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByText('Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này.')).toBeVisible()
  await page.reload()
  await page.goto(`/lessons/${lessonA}`)
  await page.getByRole('button', { name: 'Open AI chat' }).click()
  await expect(page.getByText('What does 你好 mean?')).toBeVisible()
  await expect(page.getByText('Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này.')).toBeVisible()
})

test('T09 learner session cannot enter Admin UI', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto('/admin')
  await expect(page.getByTestId('admin-forbidden')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible()
})

test('R1 Admin keeps the shared logout placement and failure feedback at canonical widths', async ({ page }) => {
  await login(page, adminEmail)
  await page.route('**/api/v1/auth/logout', (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'Temporary failure', details: null } }),
  }))

  for (const width of [1280, 800, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/admin')
    const logout = page.locator('.admin-sidebar > .logout-action')
    await expect(logout).toBeVisible()
    if (width === 1280) {
      const placement = await logout.evaluate((element) => {
        const item = element.getBoundingClientRect()
        const sidebar = element.parentElement!.getBoundingClientRect()
        return { itemTop: item.top, itemRight: item.right, sidebarTop: sidebar.top, sidebarBottom: sidebar.bottom, sidebarLeft: sidebar.left, sidebarRight: sidebar.right }
      })
      expect(placement.itemTop).toBeGreaterThan(placement.sidebarTop + (placement.sidebarBottom - placement.sidebarTop) * 0.65)
      expect(placement.itemRight).toBeLessThanOrEqual(placement.sidebarRight)
      expect(placement.itemRight).toBeGreaterThan(placement.sidebarLeft)
    } else {
      await expect.poll(() => logout.evaluate((element) => getComputedStyle(element).gridArea)).toBe('logout')
    }
    const nav = page.getByRole('navigation', { name: 'Admin navigation' })
    await expect(nav.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/admin')
    await expect(nav.getByRole('link', { name: 'Stats' })).toHaveAttribute('href', '/admin/stats')

    await page.getByRole('button', { name: 'Logout' }).click()
    const alert = page.getByRole('alert')
    await expect(alert).toBeVisible()
    await expect(alert).toContainText('Logout could not be confirmed')
    await expect(page.getByRole('button', { name: 'Retry logout' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Retry logout' })).toBeEnabled()
    const layout = await page.evaluate(() => ({
      viewportWidth: document.documentElement.clientWidth,
      documentWidth: document.documentElement.scrollWidth,
      alertDisplay: getComputedStyle(document.querySelector('[role="alert"]')!).display,
      alertWidth: document.querySelector('[role="alert"]')!.getBoundingClientRect().width,
      alertHeight: document.querySelector('[role="alert"]')!.getBoundingClientRect().height,
    }))
    expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth)
    expect(layout.alertDisplay).not.toBe('none')
    expect(layout.alertWidth).toBeGreaterThan(0)
    expect(layout.alertHeight).toBeGreaterThan(0)
  }
})

test('Admin Curriculum Variant B keeps the desktop cockpit and responsive single-column flow', async ({ page }, testInfo) => {
  await login(page, adminEmail)
  for (const width of [1280, 1750, 800, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/admin/curriculum')
    await expect(page.getByRole('heading', { name: 'Admin Curriculum', level: 1 })).toBeVisible()
    await expect(page.getByLabel('Select HSK')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Current curriculum' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Candidate library' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save HSK metadata' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save curriculum' })).toBeVisible()
    await expectD123Background(page, '.admin-main', 'd122-curriculum-manuscript.webp')
    if (width >= 800) await expectD123Background(page, '.admin-main', 'd122-ink-data-rhythm.webp')
    else await expectD123BackgroundAbsent(page, '.admin-main', 'd122-ink-data-rhythm.webp')
    await expectNoD122Background(page, '.admin-curriculum-workspace')
    await expectNoD122Background(page, '.admin-editor-card')

    const layout = await page.evaluate(() => {
      const rect = (selector: string) => {
        const element = document.querySelector(selector)
        if (!element) throw new Error(`Missing ${selector}`)
        const box = element.getBoundingClientRect()
        return { x: box.x, y: box.y, right: box.right, bottom: box.bottom, width: box.width, height: box.height }
      }
      const root = document.querySelector('.admin-curriculum-page')
      const workspace = document.querySelector('.admin-curriculum-workspace')
      if (!root || !workspace) throw new Error('Curriculum root/workspace missing')
      const save = document.querySelector('.admin-save-bar')
      return {
        viewport: document.documentElement.clientWidth,
        document: document.documentElement.scrollWidth,
        rootColumns: getComputedStyle(root).gridTemplateColumns.trim().split(/\s+/).length,
        workspaceColumns: getComputedStyle(workspace).gridTemplateColumns.trim().split(/\s+/).length,
        selector: rect('.admin-curriculum-page > .ui-surface[aria-label="HSK selection"]'),
        metadata: rect('.admin-curriculum-page > .admin-editor-card'),
        workspace: rect('.admin-curriculum-page > .admin-editor-section:not(.admin-editor-card) .admin-curriculum-workspace'),
        current: rect('.admin-curriculum-list'),
        candidate: rect('.admin-candidate-group'),
        savePosition: save ? getComputedStyle(save).position : null,
      }
    })
    expect(layout.document).toBeLessThanOrEqual(layout.viewport + 2)
    if (width >= 1280) {
      expect(layout.rootColumns).toBe(2)
      expect(layout.workspaceColumns).toBe(2)
      expect(layout.selector.x).toBeLessThan(layout.metadata.x)
      expect(Math.abs(layout.selector.y - layout.metadata.y)).toBeLessThanOrEqual(2)
      expect(layout.selector.right).toBeLessThanOrEqual(layout.metadata.x)
      expect(layout.workspace.y).toBeGreaterThanOrEqual(layout.metadata.bottom)
      expect(layout.candidate.x).toBeGreaterThan(layout.current.x)
      expect(layout.candidate.width / layout.current.width).toBeGreaterThan(1.4)
      expect(layout.savePosition).toBe('sticky')
    } else {
      expect(layout.rootColumns).toBe(1)
      expect(layout.selector.bottom).toBeLessThanOrEqual(layout.metadata.y)
      if (width <= 1024) expect(layout.workspaceColumns).toBe(1)
      expect(layout.savePosition).toBe(width === 390 ? 'static' : 'sticky')
    }

    await captureD123Screenshot(page, testInfo, `after-selected-${width}`, true)
    if (width === 390) {
      const removeButton = page.getByRole('button', { name: /^Remove .+ from curriculum$/ }).first()
      await removeButton.scrollIntoViewIfNeeded()
      await expect(removeButton).toBeVisible()
      await removeButton.focus()
      await expect(removeButton).toBeFocused()
      await page.screenshot({ path: testInfo.outputPath('after-selected-390-action-focus.png'), animations: 'disabled' })
    }
  }
})

test('Admin Curriculum Variant B preserves no-HSK and empty-membership states', async ({ browser }, testInfo) => {
  const emptyContext = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
  const emptyPage = await emptyContext.newPage()
  await emptyPage.route('**/api/v1/admin/hsk-levels', (route) => route.fulfill({ json: [] }))
  await login(emptyPage, adminEmail)
  for (const width of [1280, 1750, 800, 390]) {
    await emptyPage.setViewportSize({ width, height: 1000 })
    await emptyPage.goto('/admin/curriculum')
    await expect(emptyPage.getByRole('heading', { name: 'No HSK levels' })).toBeVisible()
    await expect(emptyPage.getByText('No HSK levels are available.')).toBeVisible()
    await expect(emptyPage.getByLabel('Select HSK')).toBeVisible()
    const noHsk = await emptyPage.evaluate(() => {
      const root = document.querySelector('.admin-curriculum-page')!
      const selector = document.querySelector('.admin-curriculum-page > .ui-surface[aria-label="HSK selection"]')!
      const state = document.querySelector('.admin-curriculum-page > .ui-page-state')!
      const a = selector.getBoundingClientRect()
      const b = state.getBoundingClientRect()
      return { columns: getComputedStyle(root).gridTemplateColumns.trim().split(/\s+/).length, selector: { x: a.x, y: a.y, bottom: a.bottom }, state: { x: b.x, y: b.y, width: b.width }, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }
    })
    expect(noHsk.scroll).toBeLessThanOrEqual(noHsk.client + 2)
    if (width >= 1280) {
      expect(noHsk.columns).toBe(2)
      expect(noHsk.state.x).toBeGreaterThan(noHsk.selector.x)
      expect(Math.abs(noHsk.selector.y - noHsk.state.y)).toBeLessThanOrEqual(2)
    } else {
      expect(noHsk.columns).toBe(1)
      expect(noHsk.state.y).toBeGreaterThanOrEqual(noHsk.selector.bottom)
    }
    await captureD123Screenshot(emptyPage, testInfo, `after-no-hsk-mocked-${width}`, true)
  }
  await emptyContext.close()

  const emptyMembershipContext = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
  const emptyMembershipPage = await emptyMembershipContext.newPage()
  await emptyMembershipPage.route('**/api/v1/admin/hsk-levels/*/curriculum', (route) => route.fulfill({ json: [] }))
  await login(emptyMembershipPage, adminEmail)
  for (const width of [1280, 1750]) {
    await emptyMembershipPage.setViewportSize({ width, height: 1000 })
    await emptyMembershipPage.goto('/admin/curriculum')
    await expect(emptyMembershipPage.getByRole('heading', { name: 'No curriculum units' })).toBeVisible()
    await expect(emptyMembershipPage.getByRole('heading', { name: 'Candidate library' })).toBeVisible()
    await captureD123Screenshot(emptyMembershipPage, testInfo, `after-empty-membership-mocked-${width}`, true)
  }
  await emptyMembershipContext.close()
})

test('Admin Curriculum Variant B keeps initial and curriculum fallbacks full width', async ({ page }, testInfo) => {
  await login(page, adminEmail)

  const loadingPage = await page.context().newPage()
  await loadingPage.setViewportSize({ width: 1280, height: 1000 })
  let releaseLevels!: () => void
  let markLevelsRequested!: () => void
  const levelsGate = new Promise<void>((resolve) => { releaseLevels = resolve })
  const levelsRequested = new Promise<void>((resolve) => { markLevelsRequested = resolve })
  await loadingPage.route('**/api/v1/admin/hsk-levels', async (route) => {
    markLevelsRequested()
    await levelsGate
    await route.fulfill({ json: [] })
  })
  await loadingPage.goto('/admin/curriculum', { waitUntil: 'domcontentloaded' })
  await levelsRequested
  await expect(loadingPage.getByRole('status')).toContainText('Loading HSK levels')
  const initialLoading = await loadingPage.evaluate(() => {
    const root = document.querySelector('.admin-curriculum-page')!.getBoundingClientRect()
    const state = document.querySelector('.admin-curriculum-page > .ui-page-state')!.getBoundingClientRect()
    return { rootX: root.x, rootRight: root.right, stateX: state.x, stateRight: state.right, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }
  })
  expect(initialLoading.stateX).toBe(initialLoading.rootX)
  expect(initialLoading.stateRight).toBeCloseTo(initialLoading.rootRight, 0)
  expect(initialLoading.scroll).toBeLessThanOrEqual(initialLoading.client + 2)
  await captureD123Screenshot(loadingPage, testInfo, 'after-initial-loading-mocked-1280', true)
  releaseLevels()
  await expect(loadingPage.getByRole('heading', { name: 'No HSK levels' })).toBeVisible()
  await loadingPage.close()

  const levelsErrorPage = await page.context().newPage()
  await levelsErrorPage.setViewportSize({ width: 1280, height: 1000 })
  await levelsErrorPage.route('**/api/v1/admin/hsk-levels', (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'Temporary failure', details: null } }),
  }))
  await levelsErrorPage.goto('/admin/curriculum')
  await expect(levelsErrorPage.getByRole('alert').getByRole('button', { name: 'Retry' })).toBeVisible()
  const levelsError = await levelsErrorPage.evaluate(() => {
    const root = document.querySelector('.admin-curriculum-page')!.getBoundingClientRect()
    const alert = document.querySelector('.admin-curriculum-page > .ui-alert')!.getBoundingClientRect()
    return { rootX: root.x, rootRight: root.right, alertX: alert.x, alertRight: alert.right, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }
  })
  expect(levelsError.alertX).toBe(levelsError.rootX)
  expect(levelsError.alertRight).toBeCloseTo(levelsError.rootRight, 0)
  expect(levelsError.scroll).toBeLessThanOrEqual(levelsError.client + 2)
  await captureD123Screenshot(levelsErrorPage, testInfo, 'after-initial-error-mocked-1280', true)
  await levelsErrorPage.close()

  const curriculumLoadingPage = await page.context().newPage()
  await curriculumLoadingPage.setViewportSize({ width: 1280, height: 1000 })
  let releaseCurriculum!: () => void
  let markCurriculumRequested!: () => void
  const curriculumGate = new Promise<void>((resolve) => { releaseCurriculum = resolve })
  const curriculumRequested = new Promise<void>((resolve) => { markCurriculumRequested = resolve })
  await curriculumLoadingPage.route('**/api/v1/admin/hsk-levels/*/curriculum', async (route) => {
    markCurriculumRequested()
    await curriculumGate
    await route.fulfill({ json: [] })
  })
  await curriculumLoadingPage.goto('/admin/curriculum', { waitUntil: 'domcontentloaded' })
  await curriculumRequested
  await expect(curriculumLoadingPage.getByRole('status')).toContainText('Loading curriculum')
  const curriculumLoading = await curriculumLoadingPage.evaluate(() => {
    const root = document.querySelector('.admin-curriculum-page')!.getBoundingClientRect()
    const fallback = document.querySelector('.admin-curriculum-page > .ui-surface:not([aria-label="HSK selection"]):not(.admin-editor-card)')!.getBoundingClientRect()
    return { rootX: root.x, rootRight: root.right, fallbackX: fallback.x, fallbackRight: fallback.right, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }
  })
  expect(curriculumLoading.fallbackX).toBe(curriculumLoading.rootX)
  expect(curriculumLoading.fallbackRight).toBeCloseTo(curriculumLoading.rootRight, 0)
  expect(curriculumLoading.scroll).toBeLessThanOrEqual(curriculumLoading.client + 2)
  await captureD123Screenshot(curriculumLoadingPage, testInfo, 'after-curriculum-loading-mocked-1280', true)
  releaseCurriculum()
  await expect(curriculumLoadingPage.getByRole('heading', { name: 'Current curriculum' })).toBeVisible()
  await curriculumLoadingPage.close()

  const curriculumErrorPage = await page.context().newPage()
  await curriculumErrorPage.setViewportSize({ width: 1280, height: 1000 })
  await curriculumErrorPage.route('**/api/v1/admin/hsk-levels/*/curriculum', (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'Temporary failure', details: null } }),
  }))
  await curriculumErrorPage.goto('/admin/curriculum')
  const curriculumFallback = curriculumErrorPage.locator('.admin-curriculum-page > .ui-surface:not([aria-label="HSK selection"]):not(.admin-editor-card)')
  await expect(curriculumFallback.getByRole('alert').getByRole('button', { name: 'Retry' })).toBeVisible()
  const curriculumError = await curriculumErrorPage.evaluate(() => {
    const root = document.querySelector('.admin-curriculum-page')!.getBoundingClientRect()
    const fallback = document.querySelector('.admin-curriculum-page > .ui-surface:not([aria-label="HSK selection"]):not(.admin-editor-card)')!.getBoundingClientRect()
    return { rootX: root.x, rootRight: root.right, fallbackX: fallback.x, fallbackRight: fallback.right, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }
  })
  expect(curriculumError.fallbackX).toBe(curriculumError.rootX)
  expect(curriculumError.fallbackRight).toBeCloseTo(curriculumError.rootRight, 0)
  expect(curriculumError.scroll).toBeLessThanOrEqual(curriculumError.client + 2)
  await captureD123Screenshot(curriculumErrorPage, testInfo, 'after-curriculum-error-mocked-1280', true)
  await curriculumErrorPage.close()
})

test('Admin Curriculum Variant B preserves candidate states and independent dirty save controls', async ({ page }, testInfo) => {
  await login(page, adminEmail)
  await page.setViewportSize({ width: 1280, height: 1000 })

  const candidateLoadingPage = await page.context().newPage()
  await candidateLoadingPage.setViewportSize({ width: 1280, height: 1000 })
  let releaseLessons!: () => void
  let releaseAssessments!: () => void
  let markLessonsRequested!: () => void
  let markAssessmentsRequested!: () => void
  const lessonsGate = new Promise<void>((resolve) => { releaseLessons = resolve })
  const assessmentsGate = new Promise<void>((resolve) => { releaseAssessments = resolve })
  const lessonsRequested = new Promise<void>((resolve) => { markLessonsRequested = resolve })
  const assessmentsRequested = new Promise<void>((resolve) => { markAssessmentsRequested = resolve })
  await candidateLoadingPage.route('**/api/v1/admin/lessons**', async (route) => {
    markLessonsRequested()
    await lessonsGate
    await route.continue()
  })
  await candidateLoadingPage.route('**/api/v1/admin/assessments**', async (route) => {
    markAssessmentsRequested()
    await assessmentsGate
    await route.continue()
  })
  await candidateLoadingPage.goto('/admin/curriculum', { waitUntil: 'domcontentloaded' })
  await Promise.all([lessonsRequested, assessmentsRequested])
  await expect(candidateLoadingPage.getByText(/Loading published Lessons/)).toBeVisible()
  await expect(candidateLoadingPage.getByText(/Loading published Periodic Tests/)).toBeVisible()
  await captureD123Screenshot(candidateLoadingPage, testInfo, 'after-candidate-loading-mocked-1280', true)
  releaseLessons()
  releaseAssessments()
  await expect(candidateLoadingPage.getByRole('heading', { name: 'Candidate library' })).toBeVisible()
  await candidateLoadingPage.close()

  const candidateErrorPage = await page.context().newPage()
  await candidateErrorPage.setViewportSize({ width: 1280, height: 1000 })
  const failure = {
    status: 503,
    contentType: 'application/json' as const,
    body: JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'Temporary failure', details: null } }),
  }
  await candidateErrorPage.route('**/api/v1/admin/lessons**', (route) => route.fulfill(failure))
  await candidateErrorPage.route('**/api/v1/admin/assessments**', (route) => route.fulfill(failure))
  await candidateErrorPage.goto('/admin/curriculum')
  await expect(candidateErrorPage.getByRole('button', { name: 'Retry Lessons' })).toBeVisible()
  await expect(candidateErrorPage.getByRole('button', { name: 'Retry Periodic Tests' })).toBeVisible()
  await captureD123Screenshot(candidateErrorPage, testInfo, 'after-candidate-errors-mocked-1280', true)
  await candidateErrorPage.close()

  await page.goto('/admin/curriculum')
  const metadataTitle = page.locator('.admin-editor-card').getByLabel('Title')
  await metadataTitle.fill(`${await metadataTitle.inputValue()} Variant B review`)
  const metadataSave = page.getByRole('button', { name: 'Save HSK metadata' })
  await expect(metadataSave).toBeEnabled()
  await expect(page.getByText('Unsaved metadata changes')).toBeVisible()
  await captureD123Screenshot(page, testInfo, 'after-metadata-dirty-1280', true)

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Current curriculum' })).toBeVisible()
  const moveDown = page.getByRole('button', { name: /^Move .+ down$/ }).first()
  await expect(moveDown).toBeEnabled()
  await moveDown.click()
  await expect(page.getByText('Unsaved curriculum changes')).toBeVisible()
  const saveBar = page.locator('.admin-save-bar')
  await expect(saveBar).toHaveCSS('position', 'sticky')
  const saveCurriculum = page.getByRole('button', { name: 'Save curriculum' })
  await saveCurriculum.scrollIntoViewIfNeeded()
  await expect(saveCurriculum).toBeVisible()
  await saveCurriculum.click()
  const saveDialog = page.getByRole('dialog', { name: 'Save curriculum changes?' })
  await expect(saveDialog).toBeVisible()
  await captureD123Screenshot(page, testInfo, 'after-membership-dirty-dialog-1280', true)
  await saveDialog.getByRole('button', { name: 'Cancel' }).click()
  await expect(saveDialog).toBeHidden()
})

test('R4 learner logout keeps the shared shell hook at canonical widths', async ({ page }) => {
  await login(page, learnerEmail)
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/dashboard')
    const logout = page.locator('.learner-shell .site-header > .logout-action')
    await expect(logout).toBeVisible()
    if (width === 800) {
      const alignment = await logout.evaluate((element) => {
        const item = element.getBoundingClientRect()
        const header = element.parentElement!.getBoundingClientRect()
        return { itemRight: item.right, headerRight: header.right }
      })
      expect(alignment.itemRight).toBeLessThanOrEqual(alignment.headerRight)
      expect(alignment.itemRight).toBeGreaterThan(alignment.headerRight - 48)
    }
    const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)
  }
})

test('B2 periodic test failing attempt remains gated and retry pass unlocks the next HSK', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, learnerEmail)
  await page.goto('/hsk/1')
  await expect(page.getByText('Step 8.1 Periodic Test')).toBeVisible()
  await page.getByRole('link', { name: 'Open Periodic Test' }).click()
  await page.getByRole('button', { name: 'Start / Resume Assessment' }).click()
  await page.getByLabel('你好', { exact: true }).check()
  await page.getByRole('button', { name: 'Submit Assessment' }).click()
  await expect(page.getByText('Not passed')).toBeVisible()
  r2ResultPath = new URL(page.url()).pathname
  await expect(page.getByRole('link', { name: 'Retry' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
  await page.goto('/hsk/2')
  await expect(page.getByLabel('Lesson locked')).toBeVisible()
  await page.goto('/assessments/c997aaf0-15e3-514e-92bc-a1d55eb6a57b')
  await page.getByRole('button', { name: 'Start / Resume Assessment' }).click()
  await page.getByLabel('再见', { exact: true }).check()
  await page.getByRole('button', { name: 'Submit Assessment' }).click()
  await expect(page.getByText('Passed')).toBeVisible()
  await page.goto('/hsk/2')
  await expect(page.getByText('AVAILABLE')).toBeVisible()
})

test('R2 learner journey remains usable without page overflow at mobile, tablet, and desktop widths', async ({ page }) => {
  test.skip(!r2ResultPath, 'B2 flow did not provide its deterministic result route')
  await login(page, learnerEmail)

  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.locator('.dashboard-hero')).toBeVisible()
    await expect(page.locator('.dashboard-overview')).toBeVisible()
    let layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto('/pronunciation')
    await expect(page.getByRole('heading', { name: 'Pronunciation Foundations' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Mark Tones complete' }).or(page.getByText('Completed').first())).toBeVisible()
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto('/hsk/1')
    await expect(page.getByRole('heading', { name: 'HSK 1 Curriculum' })).toBeVisible()
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto(`/lessons/${lessonA}`)
    await expect(page.getByRole('heading', { name: 'Step 8.1 Lesson A' })).toBeVisible()
    const lessonNavigation = page.getByRole('navigation', { name: 'Lesson sections' })
    await expect(lessonNavigation.getByRole('link', { name: /Vocabulary/ })).toBeVisible()
    await expect(lessonNavigation.getByRole('link', { name: /Grammar/ })).toHaveAttribute('href', '#grammar')
    await expect(lessonNavigation.getByRole('link', { name: /Practice/ })).toHaveAttribute('href', '#exercise')
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto('/assessments/c997aaf0-15e3-514e-92bc-a1d55eb6a57b')
    await expect(page.getByRole('heading', { name: 'Step 8.1 Periodic Test' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Start / Resume Assessment' })).toBeVisible()
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto(r2ResultPath)
    await expect(page.getByRole('heading', { name: 'Assessment Result' })).toBeVisible()
    await expect(page.getByText('Not passed')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Retry' })).toBeVisible()
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)
  }
})

test('B4 Admin can publish a Lesson and explicitly manage curriculum membership', async ({ page, browser }) => {
  await login(page, adminEmail)
  await page.goto('/admin/lessons')
  await page.getByRole('button', { name: 'Create Lesson' }).click()
  await page.getByRole('combobox', { name: 'HSK' }).first().selectOption({ label: 'HSK 1' })
  await page.getByLabel('Lesson number').fill('840001')
  await page.getByLabel('Title').fill('Step 8.1 Admin Lifecycle Lesson')
  await page.getByRole('button', { name: 'Create Lesson' }).last().click()
  await expect(page.getByRole('heading', { name: 'Lesson 840001 · Step 8.1 Admin Lifecycle Lesson' })).toBeVisible()
  await page.getByLabel('Title').fill('Step 8.1 Published Lifecycle Lesson')
  await page.getByRole('button', { name: 'Save metadata' }).click()
  await page.getByRole('button', { name: 'Publish Lesson' }).click()
  await expect(page.getByText('Status: PUBLISHED')).toBeVisible()

  // Publishing alone must not make the Lesson a learner curriculum unit.
  const learnerContext = await browser.newContext()
  const learnerPage = await learnerContext.newPage()
  await login(learnerPage, learnerEmail)
  await learnerPage.goto('/hsk/1')
  await expect(learnerPage.getByRole('heading', { name: 'HSK 1 Curriculum' })).toBeVisible()
  await expect(learnerPage.getByText('Step 8.1 Published Lifecycle Lesson')).toHaveCount(0)

  await page.goto('/admin/curriculum')
  const addLesson = page.getByRole('button', { name: 'Add Step 8.1 Published Lifecycle Lesson to curriculum' })
  await expect(addLesson).toBeVisible()
  await addLesson.click()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Save curriculum' }).click()
  const saveDialog = page.getByRole('dialog', { name: 'Save curriculum changes?' })
  await expect(saveDialog).toBeVisible()
  const dialogBounds = await saveDialog.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    return { left: rect.left, right: rect.right, viewport: document.documentElement.clientWidth }
  })
  expect(dialogBounds.left).toBeGreaterThanOrEqual(0)
  expect(dialogBounds.right).toBeLessThanOrEqual(dialogBounds.viewport)
  await saveDialog.getByRole('button', { name: 'Save curriculum' }).click()
  await page.setViewportSize({ width: 1280, height: 900 })
  await expect(page.getByText(/Step 8.1 Published Lifecycle Lesson/).first()).toBeVisible()

  await learnerPage.reload()
  await expect(learnerPage.getByRole('heading', { name: /Lesson 3: Step 8.1 Published Lifecycle Lesson/ })).toBeVisible()
  await learnerContext.close()
})

test('B5 generated assessment starts as DRAFT and publishes only after explicit review', async ({ page, browser }) => {
  await login(page, adminEmail)
  await page.goto('/admin/assessments')
  await page.getByRole('button', { name: 'Generate AI Draft' }).click()
  await page.getByRole('combobox', { name: 'Lesson', exact: true }).selectOption(lessonA)
  await page.getByLabel('Difficulty').selectOption('EASY')
  await page.getByRole('button', { name: 'Generate Draft' }).click()
  await expect(page.getByRole('heading', { name: 'AI Draft' })).toBeVisible()
  await expect(page.getByText('Status: DRAFT')).toBeVisible()
  const assessmentId = new URL(page.url()).pathname.split('/').at(-1)!
  const learnerContext = await browser.newContext()
  const learnerPage = await learnerContext.newPage()
  await login(learnerPage, learnerEmail)
  await learnerPage.goto(`/assessments/${assessmentId}`)
  await expect(learnerPage.getByText('Could not load assessment.')).toBeVisible()
  await learnerContext.close()
  await page.getByRole('button', { name: 'Submit Review' }).click()
  await expect(page.getByText('Status: REVIEW')).toBeVisible()
  await page.getByRole('button', { name: 'Publish Assessment' }).click()
  await expect(page.getByText('Status: PUBLISHED')).toBeVisible()
  const learnerAfterPublish = await browser.newContext()
  const learnerPublishedPage = await learnerAfterPublish.newPage()
  await login(learnerPublishedPage, learnerEmail)
  await learnerPublishedPage.goto(`/assessments/${assessmentId}`)
  await expect(learnerPublishedPage.getByRole('heading', { name: 'AI Draft' })).toBeVisible()
  await learnerAfterPublish.close()
})

test('R3 Admin Lessons, Curriculum, and Assessments remain usable without page overflow at canonical widths', async ({ page }) => {
  await login(page, adminEmail)

  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/admin/lessons')
    await expect(page.getByRole('heading', { name: 'Lessons', level: 1 })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create Lesson' }).first()).toBeVisible()
    await expect(page.getByLabel('Status')).toBeVisible()
    await expect(page.getByLabel('HSK')).toBeVisible()
    await expect(page.getByRole('region', { name: 'Lessons table' }).evaluate((element) => getComputedStyle(element).overflowX)).resolves.toBe('auto')
    await expect(page.getByRole('navigation', { name: 'Admin navigation' }).getByRole('link', { name: 'Dashboard' })).toBeVisible()
    let layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto('/admin/curriculum')
    await expect(page.getByRole('heading', { name: 'Admin Curriculum', level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Current curriculum' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Candidate library' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save curriculum' })).toBeVisible()
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)

    await page.goto('/admin/assessments')
    await expect(page.getByRole('heading', { name: 'Assessments', level: 1 })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create Assessment' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate AI Draft' })).toBeVisible()
    await expect(page.getByLabel('Status')).toBeVisible()
    await expect(page.getByLabel('Type')).toBeVisible()
    await expect(page.getByRole('region', { name: 'Assessments table' }).evaluate((element) => getComputedStyle(element).overflowX)).resolves.toBe('auto')
    layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)
  }
})

test('R4 Lesson Chat modal remains contained and restores focus at canonical widths', async ({ page }) => {
  await login(page, learnerEmail)

  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/lessons/${lessonA}`)
    const opener = page.getByRole('button', { name: 'Open AI chat' })
    await opener.click()
    const dialog = page.getByRole('dialog', { name: 'AI Tutor Chat' })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Close chat' })).toBeFocused()
    await expect(dialog.getByRole('button', { name: 'New conversation' })).toBeVisible()
    const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(layout.scroll).toBeLessThanOrEqual(layout.client)
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(opener).toBeFocused()
  }
})

test('R4 AI generation groups and Generate action remain readable at 390px', async ({ page }) => {
  await login(page, adminEmail)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/admin/assessments')
  await page.getByRole('button', { name: 'Generate AI Draft' }).click()
  const form = page.getByRole('form', { name: 'Generate AI Draft' })
  await expect(form.getByRole('heading', { name: 'Generate AI Draft' })).toBeVisible()
  await form.locator('select').first().selectOption('PERIODIC_TEST')
  await expect(form.getByRole('region', { name: 'Periodic Test generation scope' })).toBeVisible()
  await form.getByRole('group', { name: 'Select Lessons' }).getByRole('checkbox').first().check()
  await expect(form.getByRole('group', { name: 'Vocabulary' })).toBeVisible()
  await expect(form.getByRole('group', { name: 'Grammar' })).toBeVisible()
  await expect(form.locator('[aria-label="Selected content summary"]')).toBeVisible()
  const generate = form.getByRole('button', { name: 'Generate Draft' })
  await generate.scrollIntoViewIfNeeded()
  await expect(generate).toBeVisible()
  const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
  expect(layout.scroll).toBeLessThanOrEqual(layout.client)
})

test('R5 Public Login remains usable without page overflow at canonical widths', async ({ page }) => {
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    const signIn = page.getByRole('button', { name: 'Sign in' })
    await signIn.scrollIntoViewIfNeeded()
    await expect(signIn).toBeInViewport()
    const brand = page.locator('.public-shell .site-header .brand')
    await expect(brand).toBeVisible()
    await brand.click()
    await expect(page).toHaveURL(/\/login$/)
    const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)
  }
})

test('R5 Learner Progress, Profile, and History remain distinct and usable at canonical widths', async ({ page }) => {
  await login(page, learnerEmail)
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })

    await page.goto('/progress')
    await expect(page.getByRole('heading', { name: 'Progress', level: 1 })).toBeVisible()
    await expect(page.getByText(/Overall progress:/)).toBeVisible()
    let dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)

    await page.goto('/profile')
    await expect(page.getByRole('heading', { name: 'Profile', level: 1 })).toBeVisible()
    const changePassword = page.getByRole('button', { name: 'Change password' })
    await changePassword.scrollIntoViewIfNeeded()
    await expect(changePassword).toBeInViewport()
    dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)

    await page.goto('/history')
    await expect(page.getByRole('heading', { name: 'History', level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'History is not available yet', level: 2 })).toBeVisible()
    await expect(page.getByText('Historical assessment attempts and results will be shown here.')).toBeVisible()
    dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)
  }
})

test('R5 Admin Documents and Stats secondary screens remain usable at canonical widths', async ({ page }) => {
  await login(page, adminEmail)
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })

    await page.goto('/admin/documents')
    await expect(page.getByRole('heading', { name: 'Admin Documents', level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Upload a source document' })).toBeInViewport()
    const documentRegion = page.getByRole('region', { name: 'Documents table' })
    if (await documentRegion.count()) {
      await expect(documentRegion).toHaveAttribute('tabindex', '0')
      const overflow = await documentRegion.evaluate((element) => getComputedStyle(element).overflowX)
      expect(['auto', 'scroll']).toContain(overflow)
      await documentRegion.focus()
      await expect(documentRegion).toBeFocused()
    }
    let dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)

    await page.goto('/admin/stats')
    await expect(page.getByRole('heading', { name: 'Admin Stats', level: 1 })).toBeVisible()
    await expect(page.getByText('Total users')).toBeVisible()
    await expect(page.getByText('Average exercise score')).toBeVisible()
    const statsRegion = page.getByRole('region', { name: 'Users by current HSK table' })
    if (await statsRegion.count()) {
      await expect(statsRegion).toHaveAttribute('tabindex', '0')
      const overflow = await statsRegion.evaluate((element) => getComputedStyle(element).overflowX)
      expect(['auto', 'scroll']).toContain(overflow)
      await statsRegion.focus()
      await expect(statsRegion).toBeFocused()
    }
    dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)
  }
})

test('R5 learner Dashboard skip link is keyboard reachable and targets main content', async ({ page }) => {
  await login(page, learnerEmail)
  const keyboardPage = await page.context().newPage()
  await keyboardPage.goto('/dashboard')
  const skipLink = keyboardPage.getByRole('link', { name: 'Skip to content' })
  const mainContent = keyboardPage.locator('#main-content[data-layout="learner"]')
  await expect(skipLink).toBeAttached()
  await expect(mainContent).toBeAttached()
  await expect(keyboardPage).toHaveURL(/\/dashboard$/)
  await keyboardPage.keyboard.press('Tab')
  await expect(skipLink).toBeFocused()
  await keyboardPage.keyboard.press('Enter')
  await expect(keyboardPage).toHaveURL(/#main-content$/)
  await expect(mainContent).toBeFocused()
  await keyboardPage.close()
})

test('D-121 Public/Auth visual identity stays scoped and usable at canonical widths', async ({ page }) => {
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })

    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'A more thoughtful way to learn Chinese.' })).toBeVisible()
    await expect(page.locator('.public-login-greeting')).toBeVisible()
    const loginVisual = await page.evaluate(() => ({
      columns: getComputedStyle(document.querySelector('.public-login-layout')!).gridTemplateColumns.split(' ').length,
      background: getComputedStyle(document.querySelector('.public-shell')!).backgroundImage,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(loginVisual.columns).toBe(width <= 760 ? 1 : 2)
    expect(loginVisual.background).toContain('login-ink-landscape.png')
    expect(loginVisual.scrollWidth).toBeLessThanOrEqual(loginVisual.clientWidth)

    await page.goto('/register')
    await expect(page.locator('.public-register-page')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible()
    expect(await page.locator('.public-shell').evaluate((element) => getComputedStyle(element).backgroundImage)).toContain('login-ink-landscape.png')

    await page.goto('/forgot-password')
    await expect(page.locator('.public-forgot-page')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Forgot password' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send reset instructions' })).toBeVisible()
    expect(await page.locator('.public-shell').evaluate((element) => getComputedStyle(element).backgroundImage)).toContain('login-ink-landscape.png')

    await page.goto('/reset-password')
    await expect(page.locator('.public-reset-page')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Reset password' })).toBeVisible()
    await expect(page.getByRole('alert')).toBeVisible()
    expect(await page.locator('.public-shell').evaluate((element) => getComputedStyle(element).backgroundImage)).toContain('login-ink-landscape.png')

    const publicOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(publicOverflow).toBe(true)
  }
})

test('D-121 Learner visual identity stays scoped and usable at canonical widths', async ({ page }) => {
  await login(page, learnerEmail)
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: 'Continue Learning' })).toBeVisible()
    expect(await page.locator('.dashboard-hero').evaluate((element) => getComputedStyle(element).backgroundImage)).toContain('login-ink-landscape.png')
    let overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(overflow).toBe(true)

    await page.goto(`/lessons/${lessonA}`)
    await expect(page.getByRole('navigation', { name: 'Lesson sections' })).toBeVisible()
    await expect(page.locator('.lesson-theory-card').first()).toBeVisible()
    overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(overflow).toBe(true)
  }
})

test('D-121 Admin visual identity stays scoped and usable at canonical widths', async ({ page }) => {
  await login(page, adminEmail)
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin Dashboard' })).toBeVisible()
    let adminHasArtwork = await page.evaluate(() => Array.from(document.querySelectorAll('*')).some((element) => getComputedStyle(element).backgroundImage.includes('login-ink-landscape.png')))
    expect(adminHasArtwork).toBe(false)
    let overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(overflow).toBe(true)

    await page.goto('/admin/lessons')
    await expect(page.getByRole('heading', { name: 'Lessons', level: 1 })).toBeVisible()
    adminHasArtwork = await page.evaluate(() => Array.from(document.querySelectorAll('*')).some((element) => getComputedStyle(element).backgroundImage.includes('login-ink-landscape.png')))
    expect(adminHasArtwork).toBe(false)
    overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(overflow).toBe(true)

    await page.goto('/admin/documents')
    await expect(page.getByRole('heading', { name: 'Admin Documents', level: 1 })).toBeVisible()
    adminHasArtwork = await page.evaluate(() => Array.from(document.querySelectorAll('*')).some((element) => getComputedStyle(element).backgroundImage.includes('login-ink-landscape.png')))
    expect(adminHasArtwork).toBe(false)
    overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(overflow).toBe(true)
  }
})

test('D-123 route backgrounds use approved artwork without compromising dense surfaces', async ({ page, browser }, testInfo) => {
  test.setTimeout(180_000)
  const guest = await browser.newPage()
  await guest.route('**/api/v1/auth/me', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }))
  for (const width of [390, 800, 1280]) {
    await guest.setViewportSize({ width, height: 900 })
    await guest.goto('/dashboard')
    await expect(guest.getByRole('heading', { name: 'Session verification' })).toBeVisible()
    await expect(guest.getByRole('button', { name: 'Retry' })).toBeVisible()
    await expectD123Background(guest, 'body', 'd122-ink-circle-bamboo.webp')
    await expectD123PseudoSuppressed(guest, '.public-session-page', 'd122-ink-circle-bamboo.webp')
    await captureD123Screenshot(guest, testInfo, `public-session-${width}`)
    await expectNoPageOverflow(guest)

    await guest.goto('/missing-d122-review-route')
    await expect(guest.getByTestId('not-found')).toBeVisible()
    await expectD123Background(guest, 'body', 'd122-ink-circle-bamboo.webp')
    await expectD123PseudoSuppressed(guest, '.not-found', 'd122-ink-circle-bamboo.webp')
    await captureD123Screenshot(guest, testInfo, `public-not-found-${width}`)
    await expectNoPageOverflow(guest)
  }
  await guest.close()

  await login(page, learnerEmail)
  for (const width of [390, 800, 1280]) {
    await page.setViewportSize({ width, height: 900 })

    await page.goto('/admin')
    await expect(page.getByTestId('admin-forbidden')).toBeVisible()
    await expectD123Background(page, 'body', 'd122-ink-circle-bamboo.webp')
    await expectD123PseudoSuppressed(page, '.public-forbidden-page', 'd122-ink-circle-bamboo.webp')
    await captureD123Screenshot(page, testInfo, `public-forbidden-${width}`)
    await expectNoPageOverflow(page)

    await page.goto('/hsk/1')
    await expect(page.getByRole('heading', { name: 'HSK 1 Curriculum' })).toBeVisible()
    await expect(page.getByText('Follow the unit order and availability returned by your learning plan.')).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123SingleAssetLayer(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123PseudoSuppressed(page, '.curriculum-page .ui-page-header', 'd122-journey-mountains.webp')
    if (width === 1280) await captureD123Screenshot(page, testInfo, `learner-curriculum-${width}`)
    await expectNoPageOverflow(page)

    await page.goto('/pronunciation')
    await expect(page.getByRole('heading', { name: 'Pronunciation Foundations' })).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-language-brush.webp')
    if (width > 639) await expectD123Background(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    if (width === 390) await expectD123BackgroundAbsent(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    await expectD123PseudoSuppressed(page, '.pronunciation-page .ui-page-header', 'd122-language-brush.webp')
    await captureD123Screenshot(page, testInfo, `learner-pronunciation-${width}`)
    await expectNoPageOverflow(page)

    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: 'Continue Learning' })).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123SingleAssetLayer(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123Background(page, '.dashboard-hero', 'login-ink-landscape.png')
    if (width === 800 || width === 1280) await captureD123Screenshot(page, testInfo, `learner-dashboard-${width}`)
    await expectNoPageOverflow(page)

    await page.goto(`/lessons/${lessonA}`)
    await expect(page.getByRole('heading', { name: 'Step 8.1 Lesson A' })).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-study-scroll.webp')
    if (width > 639) await expectD123Background(page, '.learner-shell', 'd122-language-brush.webp')
    if (width === 390) await expectD123BackgroundAbsent(page, '.learner-shell', 'd122-language-brush.webp')
    await expectD123PseudoSuppressed(page, '.lesson-page .ui-page-header', 'd122-study-scroll.webp')
    await expectD122Asset(page, '.lesson-page #vocabulary .lesson-section__heading', 'd122-language-brush.webp')
    await expectD122Asset(page, '.lesson-page #grammar .lesson-section__heading', 'd122-language-brush.webp')
    await expectD122Asset(page, '.lesson-chat-entry', 'd122-language-brush.webp')
    if (width === 1280) await captureD123Screenshot(page, testInfo, `learner-lesson-${width}`)
    await page.getByRole('button', { name: 'Open AI chat' }).click()
    await expect(page.locator('.chat-panel')).toBeVisible()
    await expectNoD122Background(page, '.chat-panel')
    await page.getByRole('button', { name: 'Close chat' }).click()
    await expectNoPageOverflow(page)

    await page.goto('/assessments/c997aaf0-15e3-514e-92bc-a1d55eb6a57b')
    await expect(page.getByRole('heading', { name: 'Step 8.1 Periodic Test' })).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-exam-scroll.webp')
    if (width > 639) await expectD123Background(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    if (width === 390) await expectD123BackgroundAbsent(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    await expectD123PseudoSuppressed(page, '.assessment-screen .ui-page-header', 'd122-exam-scroll.webp')
    if (width === 1280) await captureD123Screenshot(page, testInfo, `learner-assessment-prestart-${width}`)
    await page.getByRole('button', { name: 'Start / Resume Assessment' }).click()
    await expect(page.locator('.assessment-question')).toBeVisible()
    const activeAssessmentBackground = await page.locator('.learner-shell').evaluate((element) => getComputedStyle(element).backgroundImage)
    expect(activeAssessmentBackground).not.toContain('d122-')
    await expectNoD122Background(page, '.assessment-question')
    if (width === 800 || width === 1280) await captureD123Screenshot(page, testInfo, `learner-assessment-active-${width}`)
    await expectNoPageOverflow(page)

    if (r2ResultPath) {
      await page.goto(r2ResultPath)
      await expect(page.getByRole('heading', { name: 'Assessment Result' })).toBeVisible()
      await expectD123Background(page, '.learner-shell', 'd122-exam-scroll.webp')
      await expectD123PseudoSuppressed(page, '.assessment-result-page .ui-page-header', 'd122-exam-scroll.webp')
      if (width === 1280) await captureD123Screenshot(page, testInfo, `learner-assessment-result-${width}`)
      await expectNoPageOverflow(page)
    }

    await page.goto('/progress')
    await expect(page.getByRole('heading', { name: 'Progress', level: 1, exact: true })).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123SingleAssetLayer(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123PseudoSuppressed(page, '.progress-overall', 'd122-journey-mountains.webp')
    const progressMotif = await page.locator('.progress-overall').evaluate((element) => getComputedStyle(element, '::before').borderTopStyle)
    expect(progressMotif).toBe('solid')
    await expectNoPageOverflow(page)

    await page.goto('/history')
    await expect(page.getByRole('heading', { name: 'History is not available yet' })).toBeVisible()
    await expectD123Background(page, '.learner-shell', 'd122-archive-library.webp')
    if (width > 639) await expectD123Background(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    if (width === 390) await expectD123BackgroundAbsent(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    await expectD123PseudoSuppressed(page, '.history-page .ui-page-state', 'd122-archive-library.webp')
    await captureD123Screenshot(page, testInfo, `learner-history-${width}`)
    await expectNoPageOverflow(page)

    await page.goto('/profile')
    await expect(page.getByRole('heading', { name: 'Profile' })).toBeVisible()
    if (width > 639) await expectD123Background(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    await expectD123Background(page, '.learner-shell', 'd122-journey-mountains.webp')
    await expectD123PseudoSuppressed(page, '.profile-page .ui-page-header', 'd122-ink-circle-bamboo.webp')
    await expectNoD122Background(page, '.profile-security')
    await expectNoD122Background(page, '.profile-password-form')
    if (width === 390) await expectD123BackgroundAbsent(page, '.learner-shell', 'd122-ink-circle-bamboo.webp')
    if (width === 1280) await captureD123Screenshot(page, testInfo, `learner-profile-${width}`)
    await expectNoPageOverflow(page)
  }

  await page.setViewportSize({ width: 1750, height: 1000 })
  await page.goto('/hsk/1')
  await expect(page.getByRole('heading', { name: 'HSK 1 Curriculum' })).toBeVisible()
  await expectD123SingleAssetLayer(page, '.learner-shell', 'd122-journey-mountains.webp')
  await captureD123Screenshot(page, testInfo, 'learner-curriculum-1750')
  await expectNoPageOverflow(page)

  const adminContext = await browser.newContext()
  const adminPage = await adminContext.newPage()
  await login(adminPage, adminEmail)
  for (const width of [390, 800, 1280]) {
    await adminPage.setViewportSize({ width, height: 900 })

    const adminPlacements = [
      ['/admin', 'Admin Dashboard', 'd122-ink-circle-bamboo.webp', 'd122-academy-pavilion.webp', '.admin-dashboard-page .ui-page-header'],
      ['/admin/curriculum', 'Admin Curriculum', 'd122-ink-data-rhythm.webp', 'd122-curriculum-manuscript.webp', '.admin-curriculum-page .ui-page-header'],
      ['/admin/lessons', 'Lessons', 'd122-ink-circle-bamboo.webp', 'd122-study-scroll.webp', '.admin-lessons-page .ui-page-header'],
      ['/admin/lessons/0e63a248-4b5a-5c14-aad6-dadd22b8a91d', /^Lesson 1/, 'd122-ink-circle-bamboo.webp', 'd122-study-scroll.webp', '.admin-lesson-editor-page .ui-page-header'],
      ['/admin/assessments', 'Assessments', 'd122-ink-data-rhythm.webp', 'd122-exam-scroll.webp', '.admin-assessments-page .ui-page-header'],
      ['/admin/assessments/c997aaf0-15e3-514e-92bc-a1d55eb6a57b', /Step 8\.1 Periodic Test/, 'd122-ink-data-rhythm.webp', 'd122-exam-scroll.webp', '.admin-assessment-editor-page .ui-page-header'],
      ['/admin/documents', 'Admin Documents', 'd122-ink-circle-bamboo.webp', 'd122-archive-library.webp', '.admin-documents-page .ui-page-header'],
      ['/admin/stats', 'Admin Stats', null, 'd122-ink-data-rhythm.webp', '.admin-stats-page .ui-page-header'],
    ] as const
    for (const [path, heading, leftAsset, rightAsset, headerSelector] of adminPlacements) {
      await adminPage.goto(path)
      await expect(adminPage.getByRole('heading', { name: heading, level: 1 })).toBeVisible()
      if (path === '/admin' || path === '/admin/stats' || path === '/admin/lessons/0e63a248-4b5a-5c14-aad6-dadd22b8a91d') {
        await expectAdminBackgroundLayerAlignment(adminPage, `${path}@${width}`, width === 390 && Boolean(leftAsset))
      }
      await expectD123Background(adminPage, '.admin-main', rightAsset)
      if (leftAsset && width >= 800) await expectD123Background(adminPage, '.admin-main', leftAsset)
      if (leftAsset && width === 390) await expectD123BackgroundAbsent(adminPage, '.admin-main', leftAsset)
      if (rightAsset === 'd122-ink-data-rhythm.webp') await expectD123SingleAssetLayer(adminPage, '.admin-main', rightAsset)
      await expectD123PseudoSuppressed(adminPage, headerSelector, rightAsset)
      await expectNoD122Background(adminPage, '.admin-sidebar')
      if ((width === 1280 || width === 800 || width === 390) && path === '/admin') await captureD123Screenshot(adminPage, testInfo, `admin-dashboard-${width}`)
      if ((width === 800 || width === 390) && path.includes('/lessons/')) await captureD123Screenshot(adminPage, testInfo, `admin-lesson-editor-${width}`)
      if ((width === 800 || width === 390) && path === '/admin/stats') await captureD123Screenshot(adminPage, testInfo, `admin-stats-${width}`)
      if (width === 1280 && path === '/admin/curriculum') await captureD123Screenshot(adminPage, testInfo, `admin-curriculum-${width}`)
      if ((width === 800 || width === 1280) && path === '/admin/lessons') await captureD123Screenshot(adminPage, testInfo, `admin-lessons-${width}`)
      if (width === 1280 && path.includes('/lessons/')) await captureD123Screenshot(adminPage, testInfo, `admin-lesson-editor-${width}`)
      if (width === 1280 && path === '/admin/assessments') await captureD123Screenshot(adminPage, testInfo, `admin-assessments-${width}`)
      if (width === 1280 && path === '/admin/documents') await captureD123Screenshot(adminPage, testInfo, `admin-documents-${width}`)
      if (width === 1280 && path === '/admin/stats') await captureD123Screenshot(adminPage, testInfo, `admin-stats-${width}`)
      if (path === '/admin/curriculum') {
        await expectNoD122Background(adminPage, '.admin-curriculum-workspace')
        await expectNoD122Background(adminPage, '.admin-editor-card')
        await expectNoD122Background(adminPage, '.admin-form-grid')
      }
      if (path.includes('/lessons/')) {
        await expectNoD122Background(adminPage, '.admin-form-grid')
        await expectNoD122Background(adminPage, '.admin-edit-fields')
      }
      if (path.includes('/assessments/')) {
        await expectNoD122Background(adminPage, '.admin-form-grid')
        await expectNoD122Background(adminPage, '.admin-question-form')
      }
      if (path === '/admin/lessons') {
        await expectNoD122Background(adminPage, '.admin-form-grid')
        await expectNoD122Background(adminPage, '.admin-table')
      }
      if (path === '/admin/documents') {
        await expectNoD122Background(adminPage, '.admin-documents-upload-surface')
        await expectNoD122Background(adminPage, '.admin-documents-table-wrap')
      }
      if (path === '/admin/stats') await expectNoD122Background(adminPage, '.admin-stats-grid')
      await expectNoPageOverflow(adminPage)
    }

    await adminPage.goto('/admin/documents/00000000-0000-4000-8000-000000000000')
    await expect(adminPage.getByRole('heading', { name: 'Admin Document', level: 1 })).toBeVisible()
    if (width >= 800) await expectD123Background(adminPage, '.admin-main', 'd122-ink-circle-bamboo.webp')
    if (width === 390) await expectD123BackgroundAbsent(adminPage, '.admin-main', 'd122-ink-circle-bamboo.webp')
    await expectD123Background(adminPage, '.admin-main', 'd122-archive-library.webp')
    await expectD123PseudoSuppressed(adminPage, '.admin-document-detail-page .ui-page-header', 'd122-archive-library.webp')
    await expectNoD122Background(adminPage, '.admin-document-preview')
    if (width === 1280) await captureD123Screenshot(adminPage, testInfo, `admin-document-detail-${width}`)
    await expectNoPageOverflow(adminPage)

    await adminPage.goto('/admin/assessments')
    await adminPage.getByRole('button', { name: 'Generate AI Draft' }).click()
    await expect(adminPage.locator('.admin-ai-generation-header')).toBeVisible()
    await expectD122Asset(adminPage, '.admin-ai-generation-header', 'd122-ink-data-rhythm.webp')
    await expectNoD123ArtworkOnElement(adminPage, '.admin-main')
    await expectNoD122Background(adminPage, '.admin-ai-generation-group')
    await expectNoPageOverflow(adminPage)
  }

  await adminPage.setViewportSize({ width: 1750, height: 1000 })
  await adminPage.goto('/admin')
  await expect(adminPage.getByRole('heading', { name: 'Admin Dashboard', level: 1 })).toBeVisible()
  await expectD123Background(adminPage, '.admin-main', 'd122-ink-circle-bamboo.webp')
  await expectD123Background(adminPage, '.admin-main', 'd122-academy-pavilion.webp')
  await expectAdminBackgroundLayerAlignment(adminPage, '/admin@1750')
  await expectNoD122Background(adminPage, '.admin-sidebar')
  await captureD123Screenshot(adminPage, testInfo, 'admin-dashboard-1750', true)
  await expectNoPageOverflow(adminPage)
  await adminContext.close()
})

const wave1aViewports = [390, 800, 1280, 1750] as const

async function captureWave1AScreenshot(page, testInfo, name: string) {
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), animations: 'disabled', fullPage: true })
}

async function expectWave1ANavGeometry(nav, expectedLinks: readonly { label: string; href: string }[], viewportWidth: number) {
  const geometry = await nav.evaluate((element) => {
    const navRect = element.getBoundingClientRect()
    return {
      scrollWidth: element.scrollWidth,
      clientWidth: element.clientWidth,
      nav: { left: navRect.left, right: navRect.right, top: navRect.top, bottom: navRect.bottom },
      links: Array.from(element.querySelectorAll('a')).map((link) => {
        const rect = link.getBoundingClientRect()
        return {
          label: link.textContent?.trim() ?? '',
          href: new URL((link as HTMLAnchorElement).href).pathname,
          rect: { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height },
        }
      }),
    }
  })
  expect(geometry.links.map(({ label, href }) => ({ label, href }))).toEqual(expectedLinks)
  expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth)
  for (const link of geometry.links) {
    expect(link.rect.width).toBeGreaterThan(0)
    expect(link.rect.height).toBeGreaterThan(0)
    expect(link.rect.left).toBeGreaterThanOrEqual(geometry.nav.left - 1)
    expect(link.rect.right).toBeLessThanOrEqual(Math.min(geometry.nav.right, viewportWidth) + 1)
    expect(link.rect.top).toBeGreaterThanOrEqual(geometry.nav.top - 1)
    expect(link.rect.bottom).toBeLessThanOrEqual(geometry.nav.bottom + 1)
  }
}

async function expectWave1AGridColumns(nav, expectedColumns: number) {
  const tracks = await nav.evaluate((element) => getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length)
  expect(tracks).toBe(expectedColumns)
}

async function expectWave1APageNoOverflow(page) {
  const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client)
}

async function expectWave1AFocusRing(page) {
  const style = await page.evaluate(() => {
    const active = document.activeElement
    if (!(active instanceof HTMLElement)) return null
    const computed = getComputedStyle(active)
    const rect = active.getBoundingClientRect()
    const navRect = active.closest('nav')?.getBoundingClientRect()
    return {
      outlineStyle: computed.outlineStyle,
      outlineWidth: Number.parseFloat(computed.outlineWidth),
      left: rect.left,
      right: rect.right,
      top: rect.top,
      bottom: rect.bottom,
      navLeft: navRect?.left,
      navRight: navRect?.right,
      navTop: navRect?.top,
      navBottom: navRect?.bottom,
    }
  })
  expect(style).not.toBeNull()
  expect(style!.outlineStyle).not.toBe('none')
  expect(style!.outlineWidth).toBeGreaterThan(0)
  expect(style!.left).toBeGreaterThanOrEqual(-1)
  expect(style!.right).toBeLessThanOrEqual((await page.evaluate(() => innerWidth)) + 1)
  expect(style!.top).toBeGreaterThanOrEqual(-1)
  expect(style!.bottom).toBeLessThanOrEqual((await page.evaluate(() => innerHeight)) + 1)
  if (style!.navLeft !== undefined) {
    expect(style!.left).toBeGreaterThanOrEqual(style!.navLeft - 1)
    expect(style!.right).toBeLessThanOrEqual(style!.navRight! + 1)
    expect(style!.top).toBeGreaterThanOrEqual(style!.navTop! - 1)
    expect(style!.bottom).toBeLessThanOrEqual(style!.navBottom! + 1)
  }
}

test('Wave 1A Admin navigation is fully visible and keyboard reachable at canonical widths', async ({ page }, testInfo) => {
  const expectedLinks = [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Curriculum', href: '/admin/curriculum' },
    { label: 'Lessons', href: '/admin/lessons' },
    { label: 'Assessments', href: '/admin/assessments' },
    { label: 'Documents', href: '/admin/documents' },
    { label: 'Stats', href: '/admin/stats' },
  ] as const
  await login(page, adminEmail)

  for (const width of wave1aViewports) {
    await page.setViewportSize({ width, height: 960 })
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin Dashboard', level: 1 })).toBeVisible()
    const nav = page.getByRole('navigation', { name: 'Admin navigation' })
    await expect(nav.getByRole('link')).toHaveCount(6)
    for (const item of expectedLinks) await expect(nav.getByRole('link', { name: item.label, exact: true })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Dashboard', exact: true })).toHaveAttribute('aria-current', 'page')
    await expectWave1ANavGeometry(nav, expectedLinks, width)
    if (width === 390) await expectWave1AGridColumns(nav, 2)
    if (width === 800) await expectWave1AGridColumns(nav, 3)
    await expectWave1APageNoOverflow(page)
    await captureWave1AScreenshot(page, testInfo, `wave1a-admin-dashboard-${width}`)
  }

  await page.setViewportSize({ width: 390, height: 960 })
  await page.goto('/admin')
  const nav = page.getByRole('navigation', { name: 'Admin navigation' })
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Tab')
  await page.keyboard.press('Tab')
  for (const [index, item] of expectedLinks.entries()) {
    await expect(nav.getByRole('link', { name: item.label, exact: true })).toBeFocused()
    await expectWave1AFocusRing(page)
    if (index < expectedLinks.length - 1) await page.keyboard.press('Tab')
  }
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/admin\/stats$/)
  await expect(nav.getByRole('link', { name: 'Stats', exact: true })).toHaveAttribute('aria-current', 'page')
})

test('Workstream B Admin Dashboard Variant B preserves card order and responsive hierarchy', async ({ page }, testInfo) => {
  const expectedCards = [
    { label: 'Curriculum', href: '/admin/curriculum', description: 'Manage HSK metadata, curriculum membership, and order.' },
    { label: 'Lessons', href: '/admin/lessons', description: 'Create, edit, publish, and maintain lesson content.' },
    { label: 'Assessments', href: '/admin/assessments', description: 'Manage assessment metadata, questions, and lifecycle.' },
    { label: 'Documents', href: '/admin/documents', description: 'Review source documents and knowledge-processing workflow.' },
    { label: 'Stats', href: '/admin/stats', description: 'View backend user and exercise aggregates.' },
  ] as const

  await login(page, adminEmail)

  for (const width of wave1aViewports) {
    await page.setViewportSize({ width, height: 960 })
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin Dashboard', level: 1 })).toBeVisible()
    const grid = page.locator('.admin-dashboard-page .admin-link-grid')
    const cards = grid.locator(':scope > a.structural-card')
    await expect(cards).toHaveCount(5)

    const content = await cards.evaluateAll((elements) => elements.map((element) => ({
      label: element.querySelector('h2')?.textContent?.trim() ?? '',
      href: new URL((element as HTMLAnchorElement).href).pathname,
      description: element.querySelector('p')?.textContent?.trim() ?? '',
    })))
    expect(content).toEqual(expectedCards)
    await expectWave1APageNoOverflow(page)

    if (width >= 1200) {
      const desktop = await grid.evaluate((element) => {
        const style = getComputedStyle(element)
        const rects = Array.from(element.querySelectorAll(':scope > a.structural-card')).map((card) => {
          const cardStyle = getComputedStyle(card)
          const rect = card.getBoundingClientRect()
          const heading = card.querySelector('h2')!.getBoundingClientRect()
          const description = card.querySelector('p')!.getBoundingClientRect()
          return {
            columnStart: cardStyle.gridColumnStart,
            top: rect.top,
            bottom: rect.bottom,
            left: rect.left,
            right: rect.right,
            headingTop: heading.top,
            descriptionBottom: description.bottom,
            bottomVoid: rect.bottom - description.bottom,
            height: rect.height,
            paddingInlineStart: Number.parseFloat(cardStyle.paddingInlineStart),
            paddingBlockStart: Number.parseFloat(cardStyle.paddingBlockStart),
            backgroundColor: cardStyle.backgroundColor,
            backgroundImage: cardStyle.backgroundImage,
          }
        })
        return {
          columns: style.gridTemplateColumns.trim().split(/\s+/),
          maxWidth: Number.parseFloat(style.maxWidth),
          cards: rects,
          viewportWidth: innerWidth,
        }
      })
      expect(desktop.columns).toHaveLength(6)
      expect(desktop.maxWidth).toBeLessThanOrEqual(1056)
      expect(desktop.cards.map((card) => card.columnStart)).toEqual(['span 4', 'span 2', 'span 2', 'span 2', 'span 2'])
      expect(Math.abs(desktop.cards[0].top - desktop.cards[1].top)).toBeLessThan(1)
      expect(desktop.cards[2].top).toBeGreaterThan(desktop.cards[0].top)
      expect(Math.abs(desktop.cards[2].top - desktop.cards[3].top)).toBeLessThan(1)
      expect(Math.abs(desktop.cards[3].top - desktop.cards[4].top)).toBeLessThan(1)
      expect(desktop.cards[0].right).toBeLessThanOrEqual(desktop.cards[1].left + 1)
      expect(desktop.cards[2].right).toBeLessThanOrEqual(desktop.cards[3].left + 1)
      expect(desktop.cards[3].right).toBeLessThanOrEqual(desktop.cards[4].left + 1)
      expect(desktop.cards[0].right - desktop.cards[0].left).toBeGreaterThan(desktop.cards[1].right - desktop.cards[1].left)
      expect(desktop.cards[0].height).toBeLessThan(200)
      expect(desktop.cards[1].height).toBeLessThan(200)
      expect(desktop.cards[0].bottomVoid).toBeLessThan(56)
      expect(desktop.cards[1].bottomVoid).toBeLessThan(56)
      expect(desktop.cards.every((card) => card.paddingInlineStart >= 16)).toBe(true)
      expect(desktop.cards.every((card) => card.paddingBlockStart >= 16)).toBe(true)
      for (const card of desktop.cards) expect(card.backgroundColor).toBe('rgb(255, 253, 250)')
      expect(desktop.cards[0].backgroundImage).toContain('linear-gradient')
      expect(desktop.cards.every((card) => !card.backgroundImage.includes('url('))).toBe(true)
      await expectD123Background(page, '.admin-main', 'd122-ink-circle-bamboo.webp')
      await expectD123Background(page, '.admin-main', 'd122-academy-pavilion.webp')
    }

    await captureWave1AScreenshot(page, testInfo, `variant-b-admin-dashboard-${width}`)
  }

  await page.setViewportSize({ width: 390, height: 960 })
  await page.goto('/admin')
  const cards = page.locator('.admin-dashboard-page .admin-link-grid > a.structural-card')
  const firstCard = cards.nth(0)
  let firstCardReached = false
  for (let index = 0; index < 20; index += 1) {
    await page.keyboard.press('Tab')
    if (await firstCard.evaluate((element) => element === document.activeElement)) {
      firstCardReached = true
      break
    }
  }
  expect(firstCardReached).toBe(true)
  for (const index of expectedCards.keys()) {
    await expect(cards.nth(index)).toBeFocused()
    await expectWave1AFocusRing(page)
    if (index < expectedCards.length - 1) {
      await page.keyboard.press('Tab')
    }
  }
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/admin\/stats$/)
})

test('Wave 1A Learner navigation is fully visible and keyboard reachable at canonical widths', async ({ page }, testInfo) => {
  const expectedLinks = [
    { label: 'Góc học tập', href: '/dashboard' },
    { label: 'Hành trình', href: '/pronunciation' },
    { label: 'Lịch sử', href: '/history' },
    { label: 'Hồ sơ', href: '/profile' },
  ] as const
  await login(page, learnerEmail)

  for (const width of wave1aViewports) {
    await page.setViewportSize({ width, height: 960 })
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible()
    const nav = page.getByRole('navigation', { name: width <= 600 ? 'Điều hướng trên điện thoại' : 'Learner navigation', exact: true })
    await expect(nav.getByRole('link')).toHaveCount(4)
    for (const item of expectedLinks) await expect(nav.getByRole('link', { name: item.label, exact: true })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Góc học tập', exact: true })).toHaveAttribute('aria-current', 'page')
    await expectWave1ANavGeometry(nav, expectedLinks, width)
    if (width <= 600) await expectWave1AGridColumns(nav, 4)
    await expectWave1APageNoOverflow(page)
    await captureWave1AScreenshot(page, testInfo, `wave1a-learner-dashboard-${width}`)
  }

  await page.setViewportSize({ width: 390, height: 960 })
  await page.goto('/dashboard')
  const skipLink = page.getByRole('link', { name: 'Skip to content' })
  await page.keyboard.press('Tab')
  await expect(skipLink).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#main-content$/)
  await expect(page.locator('#main-content[data-layout="learner"]')).toBeFocused()

  await page.goto('/dashboard')
  const nav = page.getByRole('navigation', { name: 'Điều hướng trên điện thoại', exact: true })
  await page.keyboard.press('Tab')
  await expect(skipLink).toBeFocused()
  for (let step = 0; step < 15 && !(await nav.getByRole('link').first().evaluate(el => el === document.activeElement)); step++) await page.keyboard.press('Tab')
  for (const [index, item] of expectedLinks.entries()) {
    await expect(nav.getByRole('link', { name: item.label, exact: true })).toBeFocused()
    await expectWave1AFocusRing(page)
    if (index < expectedLinks.length - 1) await page.keyboard.press('Tab')
  }
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/profile$/)
  await expect(nav.getByRole('link', { name: 'Hồ sơ', exact: true })).toHaveAttribute('aria-current', 'page')
})

test('Wave 1A Admin Lessons stays semantic, readable, and internally scrollable', async ({ page }, testInfo) => {
  await login(page, adminEmail)

  for (const width of wave1aViewports) {
    await page.setViewportSize({ width, height: 960 })
    await page.goto('/admin/lessons')
    await expect(page.getByRole('heading', { name: 'Lessons', level: 1 })).toBeVisible()
    const region = page.getByRole('region', { name: 'Lessons table' })
    const table = region.getByRole('table')
    await expect(region).toHaveAttribute('tabindex', '0')
    await expect(region).toHaveCSS('overflow-x', 'auto')
    await expect(table.getByRole('columnheader')).toHaveText(['HSK', 'Lesson', 'Title', 'Status', 'Action'])
    const firstRow = table.getByRole('row').nth(1)
    const titleCell = firstRow.getByRole('cell').nth(2)
    const editorLink = region.getByRole('link', { name: 'Open Editor', exact: true }).first()
    await expect(editorLink).toBeVisible()
    const titleRules = await titleCell.evaluate((element) => {
      const style = getComputedStyle(element)
      return { minWidth: Number.parseFloat(style.minWidth), overflowWrap: style.overflowWrap, wordBreak: style.wordBreak }
    })
    const actionWhiteSpace = await editorLink.evaluate((element) => getComputedStyle(element).whiteSpace)
    if (width <= 800) {
      expect(titleRules.minWidth).toBeGreaterThanOrEqual(200)
      expect(titleRules.overflowWrap).toBe('normal')
      expect(titleRules.wordBreak).toBe('normal')
      expect(actionWhiteSpace).toBe('nowrap')
    }
    await expectWave1APageNoOverflow(page)
    await captureWave1AScreenshot(page, testInfo, `wave1a-admin-lessons-${width}`)

    if (width === 390) {
      const initialScroll = await region.evaluate((element) => ({ scrollWidth: element.scrollWidth, clientWidth: element.clientWidth }))
      expect(initialScroll.scrollWidth).toBeGreaterThan(initialScroll.clientWidth)
      await region.focus()
      for (let index = 0; index < 20; index += 1) await page.keyboard.press('ArrowRight')
      await expect.poll(() => region.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0)
      await page.screenshot({ path: testInfo.outputPath('wave1a-admin-lessons-390-table-keyboard-scrolled-right.png'), animations: 'disabled' })

      await page.keyboard.press('Tab')
      await expect(editorLink).toBeFocused()
      await expectWave1AFocusRing(page)
      const focusedAction = await page.evaluate((link) => {
        const regionElement = document.querySelector('[aria-label="Lessons table"]')!
        const regionRect = regionElement.getBoundingClientRect()
        const linkRect = link.getBoundingClientRect()
        return { scrollLeft: (regionElement as HTMLElement).scrollLeft, left: linkRect.left, right: linkRect.right, regionLeft: regionRect.left, regionRight: regionRect.right }
      }, await editorLink.elementHandle())
      expect(focusedAction.scrollLeft).toBeGreaterThan(0)
      expect(focusedAction.left).toBeGreaterThanOrEqual(focusedAction.regionLeft - 1)
      expect(focusedAction.right).toBeLessThanOrEqual(focusedAction.regionRight + 1)
      await page.screenshot({ path: testInfo.outputPath('wave1a-admin-lessons-390-action-keyboard-focused.png'), animations: 'disabled' })
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL(/\/admin\/lessons\/[^/]+$/)
    }
  }
})

test('Unified List Workspace keeps Admin Lessons and Assessments grouped and responsive', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  const pages = [
    {
      path: '/admin/lessons',
      root: '.admin-lessons-page',
      heading: 'Lessons',
      regionName: 'Lessons table',
      columns: ['HSK', 'Lesson', 'Title', 'Status', 'Action'],
      emptyTitle: 'No matching lessons',
      emptyFilter: 'Archived',
      draftFilter: 'Draft',
      loadingText: 'Loading lessons…',
      label: 'lessons',
    },
    {
      path: '/admin/assessments',
      root: '.admin-assessments-page',
      heading: 'Assessments',
      regionName: 'Assessments table',
      columns: ['Type', 'Title', 'Status', 'Pass threshold', 'Lesson', 'Action'],
      emptyTitle: 'No matching assessments',
      emptyFilter: 'ARCHIVED',
      draftFilter: 'DRAFT',
      loadingText: 'Loading assessments…',
      label: 'assessments',
    },
  ] as const
  const widths = [390, 800, 1280, 1750] as const
  await login(page, adminEmail)

  for (const item of pages) {
    for (const width of widths) {
      await page.setViewportSize({ width, height: 1000 })
      await page.goto(item.path)
      await expect(page.getByRole('heading', { name: item.heading, level: 1 })).toBeVisible()
      await expect(page.getByRole('navigation', { name: 'Admin navigation' })).toBeVisible()
      const root = page.locator(item.root)
      const filter = root.locator(':scope > .admin-filter-toolbar')
      await expect(filter).toBeVisible()
      const filterControls = filter.getByRole('combobox')
      await expect(filterControls).toHaveCount(2)
      await expect(filterControls.nth(0)).toHaveAccessibleName('Status')
      if (item.label === 'lessons') {
        await expect(page.getByRole('button', { name: 'Create Lesson', exact: true })).toBeVisible()
        await expect(filterControls.nth(1)).toHaveAccessibleName('HSK')
      } else {
        await expect(page.getByRole('button', { name: 'Create Assessment', exact: true })).toBeVisible()
        await expect(page.getByRole('button', { name: 'Generate AI Draft', exact: true })).toBeVisible()
        await expect(filterControls.nth(1)).toHaveAccessibleName('Type')
      }

      const region = page.getByRole('region', { name: item.regionName })
      await expect(region).toHaveAttribute('tabindex', '0')
      await expect(region).toHaveCSS('overflow-x', 'auto')
      const table = region.getByRole('table')
      await expect(table.getByRole('columnheader')).toHaveText([...item.columns])
      await expect(region.getByRole('link', { name: 'Open Editor', exact: true }).first()).toHaveAttribute(
        'href',
        item.label === 'lessons' ? /\/admin\/lessons\/[0-9a-f-]+$/i : /\/admin\/assessments\/[0-9a-f-]+$/i,
      )
      const denseSurfaceStyles = await root.locator(':scope > :is(.admin-filter-toolbar, .ui-table-container, .admin-page-controls)').evaluateAll((elements) => elements.map((element) => {
        const style = getComputedStyle(element)
        return { backgroundColor: style.backgroundColor, backgroundImage: style.backgroundImage }
      }))
      expect(denseSurfaceStyles.length).toBe(3)
      for (const style of denseSurfaceStyles) {
        expect(style.backgroundColor).not.toBe('rgba(0, 0, 0, 0)')
        expect(style.backgroundImage).not.toContain('d122-')
      }
      await expectWave1APageNoOverflow(page)
      await page.screenshot({ path: testInfo.outputPath(`unified-list-after-${item.label}-${width}.png`), animations: 'disabled' })

      if (width >= 1280) {
        const contentBounds = await region.evaluate((element) => {
          const rect = element.getBoundingClientRect()
          return { left: rect.left, width: rect.width, top: rect.top, bottom: rect.bottom }
        })
        const filterBounds = await filter.evaluate((element) => {
          const rect = element.getBoundingClientRect()
          return { left: rect.left, width: rect.width, bottom: rect.bottom, topRadius: Number.parseFloat(getComputedStyle(element).borderTopLeftRadius) }
        })
        const footer = root.locator(':scope > .admin-page-controls')
        const footerBounds = await footer.evaluate((element) => {
          const rect = element.getBoundingClientRect()
          const style = getComputedStyle(element)
          return { left: rect.left, width: rect.width, top: rect.top, bottomRadius: Number.parseFloat(style.borderBottomLeftRadius) }
        })
        expect(Math.abs(filterBounds.left - contentBounds.left)).toBeLessThanOrEqual(2)
        expect(Math.abs(filterBounds.width - contentBounds.width)).toBeLessThanOrEqual(2)
        expect(Math.abs(filterBounds.left - footerBounds.left)).toBeLessThanOrEqual(2)
        expect(Math.abs(filterBounds.width - footerBounds.width)).toBeLessThanOrEqual(2)
        expect(Math.abs(filterBounds.bottom - contentBounds.top)).toBeLessThanOrEqual(2)
        expect(Math.abs(contentBounds.bottom - footerBounds.top)).toBeLessThanOrEqual(2)
        expect(filterBounds.topRadius).toBeGreaterThan(0)
        expect(footerBounds.bottomRadius).toBeGreaterThan(0)
      }

      if (item.label === 'lessons' && (width === 390 || width === 800)) {
        const tableWidth = await region.evaluate((element) => ({ scroll: element.scrollWidth, client: element.clientWidth }))
        const lessonTableMinWidth = await table.evaluate((element) => Number.parseFloat(getComputedStyle(element).minWidth))
        expect(lessonTableMinWidth).toBeGreaterThanOrEqual(704)
        if (width === 390) {
          expect(tableWidth.scroll).toBeGreaterThan(tableWidth.client)
          const editorLink = region.getByRole('link', { name: 'Open Editor', exact: true }).first()
          await region.focus()
          for (let index = 0; index < 20; index += 1) await page.keyboard.press('ArrowRight')
          await expect.poll(() => region.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0)
          await page.keyboard.press('Tab')
          await expect(editorLink).toBeFocused()
          await expectWave1AFocusRing(page)
          await page.screenshot({ path: testInfo.outputPath('unified-list-lessons-390-keyboard-focus.png'), animations: 'disabled' })
        }
      }
    }

    await page.setViewportSize({ width: 1280, height: 1000 })
    await page.goto(item.path)
    const filter = page.locator(`${item.root} > .admin-filter-toolbar`)
    await filter.getByRole('combobox').nth(0).selectOption({ label: item.emptyFilter })
    await expect(page.getByRole('heading', { name: item.emptyTitle, exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Previous', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeVisible()
    const root = page.locator(item.root)
    const emptyState = root.locator(':scope > .ui-page-state')
    const footer = root.locator(':scope > .admin-page-controls')
    const emptyGeometry = await Promise.all([
      filter.evaluate((element) => { const rect = element.getBoundingClientRect(); return { left: rect.left, width: rect.width, bottom: rect.bottom, radius: Number.parseFloat(getComputedStyle(element).borderTopLeftRadius) } }),
      emptyState.evaluate((element) => { const rect = element.getBoundingClientRect(); return { left: rect.left, width: rect.width, top: rect.top, bottom: rect.bottom } }),
      footer.evaluate((element) => { const rect = element.getBoundingClientRect(); return { left: rect.left, width: rect.width, top: rect.top, radius: Number.parseFloat(getComputedStyle(element).borderBottomLeftRadius) } }),
    ])
    expect(Math.abs(emptyGeometry[0].left - emptyGeometry[1].left)).toBeLessThanOrEqual(2)
    expect(Math.abs(emptyGeometry[0].width - emptyGeometry[1].width)).toBeLessThanOrEqual(2)
    expect(Math.abs(emptyGeometry[0].left - emptyGeometry[2].left)).toBeLessThanOrEqual(2)
    expect(Math.abs(emptyGeometry[0].width - emptyGeometry[2].width)).toBeLessThanOrEqual(2)
    expect(Math.abs(emptyGeometry[0].bottom - emptyGeometry[1].top)).toBeLessThanOrEqual(2)
    expect(Math.abs(emptyGeometry[1].bottom - emptyGeometry[2].top)).toBeLessThanOrEqual(2)
    expect(emptyGeometry[0].radius).toBeGreaterThan(0)
    expect(emptyGeometry[2].radius).toBeGreaterThan(0)
    await expectWave1APageNoOverflow(page)
    await page.screenshot({ path: testInfo.outputPath(`unified-list-empty-${item.label}-1280.png`), animations: 'disabled' })

    if (item.label === 'lessons') {
      await page.getByRole('button', { name: 'Create Lesson', exact: true }).click()
      const createForm = page.locator('.admin-lessons-page > .admin-editor-section')
      await expect(createForm.getByRole('heading', { name: 'Create Lesson', exact: true })).toBeVisible()
      await expect(createForm).not.toHaveCSS('border-radius', '0px')
      await page.screenshot({ path: testInfo.outputPath('unified-list-lessons-create-form-1280.png'), animations: 'disabled' })
    } else {
      await page.getByRole('button', { name: 'Create Assessment', exact: true }).click()
      const createForm = page.locator('.admin-assessments-page > .admin-editor-section')
      await expect(createForm.getByRole('heading', { name: 'Create Assessment', exact: true })).toBeVisible()
      await expect(createForm).not.toHaveCSS('border-radius', '0px')
      await page.screenshot({ path: testInfo.outputPath('unified-list-assessments-create-form-1280.png'), animations: 'disabled' })
      await page.getByRole('button', { name: 'Close Create Assessment', exact: true }).click()
      await page.getByRole('button', { name: 'Generate AI Draft', exact: true }).click()
      const generationForm = page.locator('.admin-assessments-page > .admin-ai-generation-surface')
      await expect(generationForm.getByRole('heading', { name: 'Generate AI Draft', exact: true })).toBeVisible()
      await expect(generationForm).not.toHaveCSS('border-radius', '0px')
      await page.screenshot({ path: testInfo.outputPath('unified-list-assessments-ai-draft-form-1280.png'), animations: 'disabled' })
      await page.getByRole('button', { name: 'Close AI Draft Form', exact: true }).click()
    }

    await page.unrouteAll()
    await page.locator(`${item.root} > .admin-filter-toolbar`).getByRole('combobox').nth(0).selectOption({ label: item.draftFilter })
    await expect(page.getByRole('heading', { name: item.emptyTitle, exact: true })).toBeVisible()
    await page.route(`**/api/v1/admin/${item.label}**`, (route) => {
      const status = new URL(route.request().url()).searchParams.get('status')
      if (status === null) {
        return route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'Temporary failure', details: null } }),
        })
      }
      return route.continue()
    })
    await page.locator(`${item.root} > .admin-filter-toolbar`).getByRole('combobox').nth(0).selectOption({ label: 'All statuses' })
    const refreshWarning = item.label === 'lessons'
      ? 'Lesson list could not be refreshed. Current results remain visible.'
      : 'Assessment list could not be refreshed. Current results remain visible.'
    await expect(page.getByText(refreshWarning, { exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: item.regionName })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Open Editor', exact: true }).first()).toBeVisible()
    await page.getByText(refreshWarning, { exact: true }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: testInfo.outputPath(`unified-list-refresh-warning-${item.label}-1280.png`), animations: 'disabled' })

    await page.unrouteAll()
    let releaseRequest!: () => void
    const heldRequest = new Promise<void>((resolve) => { releaseRequest = resolve })
    await page.route(`**/api/v1/admin/${item.label}**`, async (route) => {
      await heldRequest
      await route.continue()
    })
    await page.goto(item.path, { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('status').getByText(item.loadingText, { exact: true })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath(`unified-list-loading-${item.label}-1280.png`), animations: 'disabled' })
    releaseRequest()
    await expect(page.getByRole('region', { name: item.regionName })).toBeVisible()
    await page.unrouteAll()

    await page.route(`**/api/v1/admin/${item.label}**`, (route) => route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'Temporary failure', details: null } }),
    }))
    await page.goto(item.path)
    await expect(page.getByRole('alert')).toContainText('A temporary problem prevented this action. Please retry.')
    const errorAlert = page.locator(`${item.root} > .ui-alert`)
    await expect(errorAlert).toBeVisible()
    const errorRadii = await errorAlert.evaluate((element) => {
      const style = getComputedStyle(element)
      return { bottomLeft: Number.parseFloat(style.borderBottomLeftRadius), bottomRight: Number.parseFloat(style.borderBottomRightRadius), background: style.backgroundColor }
    })
    expect(errorRadii.bottomLeft).toBeGreaterThan(0)
    expect(errorRadii.bottomRight).toBeGreaterThan(0)
    expect(errorRadii.background).not.toBe('rgba(0, 0, 0, 0)')
    await page.screenshot({ path: testInfo.outputPath(`unified-list-error-${item.label}-1280.png`), animations: 'disabled' })
    await page.unrouteAll()
  }

  for (const width of [1280, 1750]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/admin')
    await expect(page.getByRole('heading', { name: 'Admin Dashboard', level: 1 })).toBeVisible()
    const dashboardGrid = page.locator('.admin-dashboard-page .admin-link-grid')
    await expect(dashboardGrid.locator(':scope > .structural-card')).toHaveCount(5)
    const dashboardTracks = await dashboardGrid.evaluate((element) => getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length)
    expect(dashboardTracks).toBe(6)
    await expectWave1APageNoOverflow(page)
  }
})
