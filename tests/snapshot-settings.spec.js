// Quick snapshot of Settings page to verify StandbyConfig component
import { test, expect } from '@playwright/test'

test('Snapshot Settings page - StandbyConfig verification', async ({ page }) => {
  // Navigate to settings page
  await page.goto('http://localhost:4892/demo-app/settings')

  // Wait for page to load
  await page.waitForLoadState('networkidle')

  // Take full page screenshot
  await page.screenshot({
    path: '/tmp/settings-snapshot.png',
    fullPage: true
  })

  console.log('Screenshot saved to /tmp/settings-snapshot.png')

  // Check if StandbyConfig component is present by looking for relevant elements
  const pageContent = await page.content()

  // Look for key StandbyConfig elements
  const hasAutoStandby = pageContent.includes('auto-standby') ||
                         pageContent.includes('Auto Standby') ||
                         pageContent.includes('CPU Standby')

  const hasGCPZone = pageContent.includes('GCP Zone') ||
                     pageContent.includes('gcp-zone')

  const hasMachineType = pageContent.includes('Machine Type') ||
                         pageContent.includes('e2-micro')

  const hasFailover = pageContent.includes('failover') ||
                      pageContent.includes('Failover')

  console.log('\n=== StandbyConfig Component Detection ===')
  console.log('Auto Standby elements:', hasAutoStandby)
  console.log('GCP Zone elements:', hasGCPZone)
  console.log('Machine Type elements:', hasMachineType)
  console.log('Failover elements:', hasFailover)

  // List all visible headings/sections
  const headings = await page.locator('h1, h2, h3, h4').allTextContents()
  console.log('\n=== Page Headings ===')
  headings.forEach(h => console.log('-', h))
})
