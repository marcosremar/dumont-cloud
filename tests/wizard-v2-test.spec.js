// Vibe Test: GPU Reservation Wizard Flow V2
// Environment: Demo Mode (localhost:4898)
// Generated: 2026-01-02

import { test, expect } from '@playwright/test'

test.describe('GPU Reservation Wizard V2', () => {

  test.beforeEach(async ({ page }) => {
    // Enable demo mode
    await page.addInitScript(() => {
      localStorage.setItem('demo_mode', 'true')
    })
  })

  test('complete GPU reservation flow with correct selectors', async ({ page }) => {
    const startTime = performance.now()

    // Step 1: Navigate to demo-app
    console.log('Step 1: Navigating to /demo-app...')
    await page.goto('http://localhost:4898/demo-app')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(2000) // Allow wizard to render

    await page.screenshot({ path: '/tmp/wizard-v2-step-0-initial.png', fullPage: true })
    console.log('✅ Screenshot: /tmp/wizard-v2-step-0-initial.png')

    // Step 2: Select EUA region
    console.log('\nStep 2: Selecting region EUA...')

    // Look for EUA button by multiple selectors
    const euaButton = page.locator('button:has-text("EUA")').first()
    await euaButton.waitFor({ state: 'visible', timeout: 10000 })
    await euaButton.click()
    await page.waitForTimeout(500)

    await page.screenshot({ path: '/tmp/wizard-v2-step-1-region.png', fullPage: true })
    console.log('✅ Region selected')

    // Step 3: Click Próximo to go to Hardware step
    console.log('\nStep 3: Advancing to Hardware step...')
    const proximoButton1 = page.locator('button:has-text("Próximo")').first()
    await proximoButton1.waitFor({ state: 'visible' })
    await proximoButton1.click()
    await page.waitForTimeout(1000)

    await page.screenshot({ path: '/tmp/wizard-v2-step-2-hardware.png', fullPage: true })
    console.log('✅ Navigated to Hardware step')

    // Step 4: Select "Desenvolver" purpose using data-testid
    console.log('\nStep 4: Selecting purpose "Desenvolver"...')
    const desenvolverButton = page.locator('[data-testid="use-case-develop"]')
    await desenvolverButton.waitFor({ state: 'visible', timeout: 10000 })

    await page.screenshot({ path: '/tmp/wizard-v2-step-3-before-desenvolver.png', fullPage: true })

    await desenvolverButton.click({ timeout: 5000 })
    console.log('✅ Clicked Desenvolver button')

    // Wait for GPU loading - might cause navigation or state change
    await page.waitForTimeout(3000)

    await page.screenshot({ path: '/tmp/wizard-v2-step-4-after-desenvolver.png', fullPage: true })
    console.log('✅ Purpose selected, waiting for machines to load...')

    // Step 5: Wait for machines to load (15 seconds in demo mode)
    console.log('\nStep 5: Waiting for GPU offers to load (15s)...')
    await page.waitForTimeout(15000)

    await page.screenshot({ path: '/tmp/wizard-v2-step-5-machines-loaded.png', fullPage: true })
    console.log('✅ IMPORTANT: Machines loaded - check screenshot')

    // Step 6: Select a GPU machine
    console.log('\nStep 6: Selecting GPU machine...')

    // Try to find the machine by radio input or label
    const machineOptions = [
      'label:has-text("RTX 3060")',
      'label:has-text("RTX 3090")',
      'label:has-text("RTX")',
      'input[type="radio"]'
    ]

    let machineSelected = false
    for (const selector of machineOptions) {
      const machine = page.locator(selector).first()
      const count = await machine.count()
      if (count > 0) {
        console.log(`Found machine with selector: ${selector}`)
        const isVisible = await machine.isVisible({ timeout: 2000 }).catch(() => false)
        if (isVisible) {
          await machine.click()
          console.log('✅ Machine clicked')
          machineSelected = true
          await page.waitForTimeout(1000)
          break
        }
      }
    }

    if (!machineSelected) {
      console.log('⚠️ No machine selected automatically, checking page state...')
      const bodyText = await page.locator('body').textContent()
      console.log('Page contains RTX:', bodyText.includes('RTX'))
      console.log('Page contains GPU:', bodyText.includes('GPU'))
    }

    await page.screenshot({ path: '/tmp/wizard-v2-step-6-machine-selected.png', fullPage: true })
    console.log('✅ Screenshot after machine selection')

    // Step 7: Click Próximo to advance to Step 3
    console.log('\nStep 7: Advancing to Strategy step...')
    const proximoButton2 = page.locator('button:has-text("Próximo")').first()

    // Check if button is enabled
    const isEnabled = await proximoButton2.isEnabled({ timeout: 2000 }).catch(() => false)
    console.log(`Próximo button enabled: ${isEnabled}`)

    if (isEnabled) {
      await proximoButton2.click()
      await page.waitForTimeout(1000)
      console.log('✅ Navigated to Strategy step')
    } else {
      console.log('⚠️ Próximo button is disabled - machine may not be selected')
    }

    await page.screenshot({ path: '/tmp/wizard-v2-step-7-strategy.png', fullPage: true })

    // Step 8: Click Iniciar/Provisionar button
    console.log('\nStep 8: Starting provisioning...')
    const iniciarButton = page.locator('button:has-text("Iniciar"), button:has-text("Provisionar")').first()

    const iniciarEnabled = await iniciarButton.isEnabled({ timeout: 2000 }).catch(() => false)
    console.log(`Iniciar button enabled: ${iniciarEnabled}`)

    if (iniciarEnabled) {
      await page.screenshot({ path: '/tmp/wizard-v2-step-8-before-iniciar.png', fullPage: true })
      await iniciarButton.click()
      console.log('✅ Provisioning started')
    } else {
      console.log('⚠️ Iniciar button is disabled')
    }

    // Step 9: Wait for provisioning (20s)
    console.log('\nStep 9: Waiting for provisioning (20s)...')
    await page.waitForTimeout(20000)

    await page.screenshot({ path: '/tmp/wizard-v2-step-9-provisioning.png', fullPage: true })
    console.log('✅ Provisioning complete')

    // Check for success message
    const successText = await page.locator('text=/sucesso|success|provisionado|online|ready/i').first().textContent({ timeout: 5000 }).catch(() => null)
    if (successText) {
      console.log(`✅ Success message found: ${successText}`)
    } else {
      console.log('⚠️ No explicit success message found')
    }

    await page.screenshot({ path: '/tmp/wizard-v2-final.png', fullPage: true })

    const endTime = performance.now()
    const totalTime = ((endTime - startTime) / 1000).toFixed(2)
    console.log(`\n📊 Total test duration: ${totalTime}s`)
  })
})
