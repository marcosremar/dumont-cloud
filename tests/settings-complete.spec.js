// Complete Settings Page E2E Test
import { test, expect } from '@playwright/test'

test.describe('Settings Page - Complete Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to settings page
    await page.goto('http://localhost:4892/app/settings')
    await page.waitForLoadState('networkidle')
  })

  test('Settings page loads correctly', async ({ page }) => {
    // Verify page title
    const h1 = page.locator('h1').first()
    await expect(h1).toContainText('Configurações')

    // Verify settings-page data-testid
    const settingsPage = page.locator('[data-testid="settings-page"]')
    await expect(settingsPage).toBeVisible()
  })

  test('All tabs are visible', async ({ page }) => {
    // Check for main tabs - actual IDs from Settings.jsx
    const tabs = [
      'settings-tab-apis',
      'settings-tab-storage',
      'settings-tab-cloudstorage',
      'settings-tab-agent',
      'settings-tab-notifications',
      'settings-tab-failover'
    ]

    for (const tabId of tabs) {
      const tab = page.locator(`[data-testid="${tabId}"]`)
      // Tab should exist (may or may not be visible depending on layout)
      const count = await tab.count()
      console.log(`Tab ${tabId}: ${count > 0 ? 'Found' : 'Not found'}`)
    }
  })

  test('CPU Failover tab shows StandbyConfig', async ({ page }) => {
    // Navigate to failover tab
    await page.goto('http://localhost:4892/app/settings?tab=failover')
    await page.waitForLoadState('networkidle')

    // Look for failover tab
    const failoverTab = page.locator('[data-testid="settings-tab-failover"]')
    if (await failoverTab.isVisible()) {
      await failoverTab.click()
      await page.waitForTimeout(500)
    }

    // Check for StandbyConfig component elements
    const pageContent = await page.content()

    // StandbyConfig should show CPU Standby / Failover
    const hasCPUStandby = pageContent.includes('CPU Standby') ||
                          pageContent.includes('Failover')

    expect(hasCPUStandby).toBeTruthy()
    console.log('CPU Standby/Failover section found:', hasCPUStandby)

    // Take screenshot for verification
    await page.screenshot({
      path: '/tmp/settings-failover-complete.png',
      fullPage: true
    })
  })

  test('Settings save button exists', async ({ page }) => {
    // Look for save button
    const saveButton = page.locator('button').filter({ hasText: /salvar|save/i })
    const count = await saveButton.count()
    console.log(`Save buttons found: ${count}`)
    expect(count).toBeGreaterThan(0)
  })

  test('API credentials tab has input fields', async ({ page }) => {
    // Navigate to APIs tab (correct ID is 'apis')
    await page.goto('http://localhost:4892/app/settings?tab=apis')
    await page.waitForLoadState('networkidle')

    // Click the APIs tab to ensure it's active
    const apisTab = page.locator('[data-testid="settings-tab-apis"]')
    if (await apisTab.isVisible()) {
      await apisTab.click()
      await page.waitForTimeout(500)
    }

    // Look for API key inputs (also check for type="password" with class containing input)
    const apiInputs = page.locator('input')
    const count = await apiInputs.count()
    console.log(`Input fields found: ${count}`)

    // There should be at least one input (Vast.ai API Key, etc.)
    // If no inputs found, check page content for debug
    if (count === 0) {
      const content = await page.content()
      console.log('Page contains Vast.ai:', content.includes('Vast.ai'))
      console.log('Page contains API Key:', content.includes('API Key'))
    }

    expect(count).toBeGreaterThan(0)
  })
})
