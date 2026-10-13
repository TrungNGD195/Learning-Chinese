import { expect, test } from '@playwright/test'

const password = process.env.STEP81_TEST_PASSWORD
if (!password) throw new Error('Playwright global setup did not provide its ephemeral test password')
const learnerEmail = 'step81-learner@example.invalid'
const adminEmail = 'step81-admin@example.invalid'
const lessonA = '0e63a248-4b5a-5c14-aad6-dadd22b8a91d'

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
  await expect(page).toHaveURL(/\/dashboard$/)
}

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

test('B2 periodic test failing attempt remains gated and retry pass unlocks the next HSK', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto('/hsk/1')
  await expect(page.getByText('Step 8.1 Periodic Test')).toBeVisible()
  await page.getByRole('link', { name: 'Open Periodic Test' }).click()
  await page.getByRole('button', { name: 'Start / Resume Assessment' }).click()
  await page.getByLabel('你好', { exact: true }).check()
  await page.getByRole('button', { name: 'Submit Assessment' }).click()
  await expect(page.getByText('Not passed')).toBeVisible()
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

test('B4 Admin can publish a Lesson and explicitly manage curriculum membership', async ({ page, browser }) => {
  await login(page, adminEmail)
  await page.goto('/admin/lessons')
  await page.getByRole('button', { name: 'Create Lesson' }).click()
  await page.getByRole('combobox', { name: 'HSK' }).last().selectOption({ label: 'HSK 1' })
  await page.getByLabel('Lesson number').fill('840001')
  await page.getByLabel('Title').fill('Step 8.1 Admin Lifecycle Lesson')
  await page.getByRole('button', { name: 'Create Lesson' }).last().click()
  await expect(page.getByRole('heading', { name: 'Admin Lesson Editor' })).toBeVisible()
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
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Save curriculum' }).click()
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
  await expect(page.getByRole('heading', { name: 'Admin Assessment Editor' })).toBeVisible()
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