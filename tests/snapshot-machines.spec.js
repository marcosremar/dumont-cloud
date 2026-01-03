import { test, expect } from '@playwright/test'

test('Snapshot machines page stat cards', async ({ page }) => {
  // Navigate to machines page
  await page.goto('http://localhost:4892/app/machines')

  // Wait for page to load
  await page.waitForLoadState('networkidle')

  // Wait for stat cards to be visible
  await page.waitForTimeout(2000)

  // Take full page screenshot
  await page.screenshot({
    path: '/Users/marcos/CascadeProjects/dumontcloud/screenshots/machines-stat-cards.png',
    fullPage: false
  })

  console.log('Screenshot saved!')
})
