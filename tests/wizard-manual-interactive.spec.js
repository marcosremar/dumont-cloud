// Interactive Manual Test: GPU Wizard
// Run with: npx playwright test wizard-manual-interactive.spec.js --headed --project=wizard-reservation --debug

import { test, expect } from '@playwright/test'

test.describe('Manual Wizard Test', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true')
    })
  })

  test('interactive wizard navigation', async ({ page }) => {
    // Navigate to demo-app
    await page.goto('http://localhost:4898/demo-app')
    await page.waitForLoadState('networkidle')

    console.log('\n📍 Test paused - Use Playwright Inspector to navigate manually')
    console.log('Steps to test:')
    console.log('1. Click EUA button')
    console.log('2. Click Próximo')
    console.log('3. Click Desenvolver')
    console.log('4. Wait for machines to load')
    console.log('5. Select a machine (RTX 3060 or RTX 3090)')
    console.log('6. Click Próximo')
    console.log('7. Review Step 3 (Estratégia)')
    console.log('8. Click Iniciar/Provisionar')
    console.log('9. Observe provisioning animation')
    console.log('\nPress Continue in Inspector when done\n')

    // Pause for manual interaction
    await page.pause()

    // Take final screenshot
    await page.screenshot({ path: '/tmp/wizard-manual-final.png', fullPage: true })
    console.log('✅ Manual test complete - screenshot saved')
  })
})
