// Investigate Settings route and tabs
import { test, expect } from '@playwright/test'

test('Investigate Settings Page Routing', async ({ page }) => {
  // Try different URLs
  console.log('\n=== Testing Different URLs ===')

  const urls = [
    'http://localhost:4892/demo-app/settings',
    'http://localhost:4892/app/settings',
    'http://localhost:4892/settings',
  ]

  for (const url of urls) {
    console.log(`\nTrying: ${url}`)
    await page.goto(url)
    await page.waitForLoadState('networkidle')

    const title = await page.title()
    const h1Text = await page.locator('h1').first().textContent().catch(() => null)
    const hasSettingsPage = await page.locator('[data-testid="settings-page"]').count()
    const hasFailoverTab = await page.locator('[data-testid="settings-tab-failover"]').count()

    console.log(`  Title: ${title}`)
    console.log(`  H1: ${h1Text}`)
    console.log(`  Has settings-page: ${hasSettingsPage}`)
    console.log(`  Has failover tab: ${hasFailoverTab}`)
  }

  // Try the correct URL with failover tab
  console.log('\n=== Testing Failover Tab ===')
  await page.goto('http://localhost:4892/app/settings?tab=failover')
  await page.waitForLoadState('networkidle')

  // Take screenshot
  await page.screenshot({
    path: '/tmp/settings-failover-tab.png',
    fullPage: true
  })

  // Check if failover tab is active
  const failoverTab = page.locator('[data-testid="settings-tab-failover"]')
  const isFailoverTabVisible = await failoverTab.isVisible()
  console.log(`Failover tab visible: ${isFailoverTabVisible}`)

  if (isFailoverTabVisible) {
    await failoverTab.click()
    await page.waitForTimeout(1000)

    // Check for StandbyConfig component elements
    const standbyElements = await page.locator('text=/auto.*standby/i').count()
    const gcpZoneElements = await page.locator('text=/gcp.*zone/i').count()
    const machineTypeElements = await page.locator('text=/machine.*type/i').count()

    console.log(`Auto standby elements: ${standbyElements}`)
    console.log(`GCP Zone elements: ${gcpZoneElements}`)
    console.log(`Machine Type elements: ${machineTypeElements}`)

    // Take another screenshot after clicking
    await page.screenshot({
      path: '/tmp/settings-failover-clicked.png',
      fullPage: true
    })
  }
})
