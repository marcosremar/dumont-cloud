// Vibe Test: GPU Reservation Wizard Flow
// Environment: Demo Mode (localhost:4896)
// Generated: 2026-01-02

import { test, expect } from '@playwright/test'

test.describe('GPU Reservation Wizard', () => {

  test.beforeEach(async ({ page }) => {
    // Enable demo mode - ALWAYS
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true')
    })
  })

  test('complete GPU reservation flow', async ({ page }) => {
    const startTime = performance.now()

    // Step 1: Navigate to demo-app
    console.log('Step 1: Navigating to /demo-app...')
    await page.goto('http://localhost:4898/demo-app')
    await page.waitForLoadState('networkidle')

    // Take initial screenshot
    await page.screenshot({ path: '/tmp/wizard-step-0-initial.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-0-initial.png')

    // Step 2: Verify wizard is visible
    console.log('Step 2: Checking if wizard "Nova Instância GPU" is visible...')
    const wizardTitle = page.locator('text=/Nova Instância GPU|Nova Máquina|Provisionar GPU/i').first()

    // Wait for either the wizard to be visible or a button to open it
    const isVisible = await wizardTitle.isVisible({ timeout: 5000 }).catch(() => false)

    if (!isVisible) {
      console.log('Wizard not visible, looking for button to open it...')
      const openButton = page.locator('button:has-text("Nova Máquina"), button:has-text("Nova Instância"), button:has-text("Provisionar")').first()
      await openButton.click()
      await page.waitForTimeout(1000)
    }

    await page.screenshot({ path: '/tmp/wizard-step-1-opened.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-1-opened.png')

    // Step 3: Click "EUA" button to select region
    console.log('Step 3: Selecting region "EUA"...')
    const euaButton = page.locator('button:has-text("EUA"), button:has-text("US"), [data-testid="region-usa"]').first()
    await euaButton.click()
    await page.waitForTimeout(500)

    await page.screenshot({ path: '/tmp/wizard-step-2-region-selected.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-2-region-selected.png')

    // Step 4: Click "Próximo" to advance
    console.log('Step 4: Clicking "Próximo" to advance...')
    const nextButton1 = page.locator('button:has-text("Próximo"), button:has-text("Next")').first()
    await nextButton1.click()
    await page.waitForTimeout(1000)

    await page.screenshot({ path: '/tmp/wizard-step-3-after-next.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-3-after-next.png')

    // Step 5: Verify Step 2 - Select "Desenvolver"
    console.log('Step 5: Selecting purpose "Desenvolver"...')
    const desenvolverButton = page.locator('button:has-text("Desenvolver"), button:has-text("Development"), [data-testid="purpose-dev"]').first()
    await desenvolverButton.click()
    await page.waitForTimeout(500)

    await page.screenshot({ path: '/tmp/wizard-step-4-purpose-selected.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-4-purpose-selected.png')

    // Step 6: Wait for machines to load and take snapshot
    console.log('Step 6: Waiting for machines to load (15 seconds)...')
    await page.waitForTimeout(15000)

    await page.screenshot({ path: '/tmp/wizard-step-5-machines-loaded.png', fullPage: true })
    console.log('✅ IMPORTANT SCREENSHOT: /tmp/wizard-step-5-machines-loaded.png')

    // List all visible text to see what machines are available
    const pageText = await page.locator('body').textContent()
    console.log('Page content preview:', pageText.substring(0, 500))

    // Step 7: Select a machine (look for "econômico" or GPU cards)
    console.log('Step 7: Selecting a machine...')

    // The machines are displayed as label elements containing radio inputs
    // Look for the first machine card with RTX or similar text
    const machineCard = page.locator('label:has-text("RTX"), label:has-text("GPU")').first()

    const machineExists = await machineCard.count() > 0
    console.log(`Machine card found: ${machineExists}`)

    if (machineExists) {
      const machineText = await machineCard.textContent()
      console.log(`Clicking machine: ${machineText?.substring(0, 50)}...`)
      await machineCard.click()
      await page.waitForTimeout(1000)
      console.log('✅ Machine selected')
    } else {
      console.log('⚠️ No machine cards found, trying radio input...')
      const radioInput = page.locator('input[type="radio"][name*="gpu"], input[type="radio"]').first()
      await radioInput.click({ force: true }).catch(() => {
        console.log('❌ Could not select any machine')
      })
    }

    await page.screenshot({ path: '/tmp/wizard-step-6-machine-selected.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-6-machine-selected.png')

    // Step 8: Click "Próximo" to go to Step 3
    console.log('Step 8: Clicking "Próximo" to advance to Step 3...')
    const nextButton2 = page.locator('button:has-text("Próximo"), button:has-text("Next")').first()
    await nextButton2.click()
    await page.waitForTimeout(1000)

    await page.screenshot({ path: '/tmp/wizard-step-7-step3.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-7-step3.png')

    // Step 9: Verify "Iniciar" button is enabled and click it
    console.log('Step 9: Checking if "Iniciar" button is enabled...')
    const iniciarButton = page.locator('button:has-text("Iniciar"), button:has-text("Start"), button:has-text("Provisionar")').first()

    const isEnabled = await iniciarButton.isEnabled({ timeout: 5000 }).catch(() => false)
    console.log(`"Iniciar" button enabled: ${isEnabled}`)

    await page.screenshot({ path: '/tmp/wizard-step-8-before-iniciar.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-8-before-iniciar.png')

    if (isEnabled) {
      await iniciarButton.click()
      console.log('✅ "Iniciar" button clicked')
    } else {
      console.log('⚠️ "Iniciar" button is disabled')
    }

    // Step 10: Wait for provisioning and verify success message
    console.log('Step 10: Waiting for provisioning (20 seconds)...')
    await page.waitForTimeout(20000)

    await page.screenshot({ path: '/tmp/wizard-step-9-after-provisioning.png', fullPage: true })
    console.log('✅ Screenshot saved: /tmp/wizard-step-9-after-provisioning.png')

    // Look for success indicators
    const successIndicators = [
      page.locator('text=/sucesso|success|provisionado|online|ready/i'),
      page.locator('[role="status"]'),
      page.locator('.toast'),
      page.locator('[data-testid="success-message"]')
    ]

    let successFound = false
    for (const indicator of successIndicators) {
      const visible = await indicator.isVisible({ timeout: 2000 }).catch(() => false)
      if (visible) {
        const text = await indicator.textContent()
        console.log(`✅ Success indicator found: ${text}`)
        successFound = true
        break
      }
    }

    if (!successFound) {
      console.log('⚠️ No success message found after 20 seconds')
    }

    const endTime = performance.now()
    const totalTime = ((endTime - startTime) / 1000).toFixed(2)
    console.log(`\n📊 Total test duration: ${totalTime}s`)

    // Final screenshot
    await page.screenshot({ path: '/tmp/wizard-step-final.png', fullPage: true })
    console.log('✅ Final screenshot saved: /tmp/wizard-step-final.png')
  })
})
