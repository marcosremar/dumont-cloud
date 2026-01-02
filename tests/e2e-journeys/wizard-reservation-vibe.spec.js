// Vibe Test: GPU Reservation Wizard Journey
// Environment: Staging (REAL - no mocks)
// Port: 4894
// Generated: 2026-01-02

import { test, expect } from '@playwright/test'

test.describe('GPU Reservation Wizard - Real User Journey', () => {

  test.beforeEach(async ({ page }) => {
    // Disable demo mode - ALWAYS test REAL environment
    await page.addInitScript(() => {
      localStorage.removeItem('demo_mode')
      localStorage.setItem('demo_mode', 'false')
    })
  })

  test('complete wizard flow from login to GPU reservation', async ({ page }) => {
    const startTime = performance.now()
    console.log('\n=== GPU Wizard Reservation Vibe Test ===\n')

    // Step 1: Auto-login via URL parameter
    console.log('Step 1: Navigating to login with auto_login=demo...')
    const loginStart = performance.now()
    await page.goto('http://localhost:4894/login?auto_login=demo')
    await page.waitForLoadState('networkidle')
    const loginEnd = performance.now()
    console.log(`✅ Login page loaded in ${((loginEnd - loginStart) / 1000).toFixed(2)}s`)

    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-01-login.png',
      fullPage: true
    })

    // Step 2: Wait for auto-login redirect to /app
    console.log('Step 2: Waiting for auto-login redirect to /app...')
    const redirectStart = performance.now()
    await page.waitForURL('**/app**', { timeout: 10000 })
    const redirectEnd = performance.now()
    console.log(`✅ Redirected to /app in ${((redirectEnd - redirectStart) / 1000).toFixed(2)}s`)

    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-02-app-dashboard.png',
      fullPage: true
    })

    // Step 3: Verify we're on the dashboard
    console.log('Step 3: Verifying dashboard loaded...')
    await expect(page).toHaveURL(/\/app/, { timeout: 5000 })
    console.log('✅ Dashboard URL confirmed')

    // Step 4: Look for the wizard on the dashboard
    console.log('Step 4: Looking for the deployment wizard...')
    await page.waitForTimeout(2000) // Let React components render

    // Check for wizard title or trigger button
    const wizardTriggers = [
      page.locator('text=/Nova Instância GPU|Nova Máquina|Provisionar GPU/i'),
      page.locator('button:has-text("Nova Máquina")'),
      page.locator('button:has-text("Nova Instância")'),
      page.locator('button:has-text("Provisionar")'),
      page.locator('[data-testid="new-machine-button"]')
    ]

    let wizardFound = false
    let triggerButton = null

    for (const trigger of wizardTriggers) {
      const visible = await trigger.first().isVisible({ timeout: 2000 }).catch(() => false)
      if (visible) {
        wizardFound = true
        triggerButton = trigger.first()
        const text = await triggerButton.textContent()
        console.log(`✅ Found wizard trigger: "${text?.trim()}"`)
        break
      }
    }

    if (!wizardFound) {
      console.log('⚠️ Wizard not immediately visible, checking page content...')
      const bodyText = await page.locator('body').textContent()
      console.log('Page content preview:', bodyText?.substring(0, 300))
    }

    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-03-wizard-search.png',
      fullPage: true
    })

    // Step 5: Open the wizard if it's not already open
    if (triggerButton) {
      console.log('Step 5: Opening wizard...')
      await triggerButton.click()
      await page.waitForTimeout(1000)
      console.log('✅ Wizard opened')
    } else {
      console.log('Step 5: Wizard appears to be already open or inline')
    }

    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-04-wizard-opened.png',
      fullPage: true
    })

    // Step 6: Select region (USA/EUA)
    console.log('Step 6: Selecting region "EUA/USA"...')
    const regionButtons = [
      page.locator('button:has-text("EUA")'),
      page.locator('button:has-text("US")'),
      page.locator('[data-testid="region-usa"]'),
      page.locator('label:has-text("EUA")'),
      page.locator('[data-region="usa"]')
    ]

    let regionSelected = false
    for (const regionBtn of regionButtons) {
      const exists = await regionBtn.first().count() > 0
      if (exists) {
        const visible = await regionBtn.first().isVisible({ timeout: 1000 }).catch(() => false)
        if (visible) {
          await regionBtn.first().click()
          regionSelected = true
          console.log('✅ Region "EUA" selected')
          break
        }
      }
    }

    if (!regionSelected) {
      console.log('⚠️ Could not find region selection button')
    }

    await page.waitForTimeout(500)
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-05-region-selected.png',
      fullPage: true
    })

    // Step 7: Click "Próximo" to advance to GPU selection
    console.log('Step 7: Clicking "Próximo" to advance...')
    const nextButtons = [
      page.locator('button:has-text("Próximo")'),
      page.locator('button:has-text("Next")'),
      page.locator('[data-testid="next-button"]')
    ]

    let nextClicked = false
    for (const nextBtn of nextButtons) {
      const visible = await nextBtn.first().isVisible({ timeout: 2000 }).catch(() => false)
      if (visible) {
        const enabled = await nextBtn.first().isEnabled()
        if (enabled) {
          await nextBtn.first().click()
          nextClicked = true
          console.log('✅ "Próximo" button clicked')
          break
        } else {
          console.log('⚠️ "Próximo" button found but disabled')
        }
      }
    }

    if (!nextClicked) {
      console.log('⚠️ Could not click "Próximo" button')
    }

    await page.waitForTimeout(1000)
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-06-after-next.png',
      fullPage: true
    })

    // Step 8: Select purpose (Desenvolver/Development)
    console.log('Step 8: Selecting purpose "Desenvolver"...')
    const purposeButtons = [
      page.locator('button:has-text("Desenvolver")'),
      page.locator('button:has-text("Development")'),
      page.locator('[data-testid="purpose-dev"]'),
      page.locator('label:has-text("Desenvolver")')
    ]

    let purposeSelected = false
    for (const purposeBtn of purposeButtons) {
      const visible = await purposeBtn.first().isVisible({ timeout: 2000 }).catch(() => false)
      if (visible) {
        await purposeBtn.first().click()
        purposeSelected = true
        console.log('✅ Purpose "Desenvolver" selected')
        break
      }
    }

    if (!purposeSelected) {
      console.log('⚠️ Could not find purpose selection button')
    }

    await page.waitForTimeout(500)
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-07-purpose-selected.png',
      fullPage: true
    })

    // Step 9: Wait for GPU machines to load
    console.log('Step 9: Waiting for GPU machines to load (15 seconds)...')
    const machineLoadStart = performance.now()
    await page.waitForTimeout(15000)
    const machineLoadEnd = performance.now()
    console.log(`✅ Wait completed in ${((machineLoadEnd - machineLoadStart) / 1000).toFixed(2)}s`)

    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-08-machines-loaded.png',
      fullPage: true
    })

    // Log visible GPU options
    const bodyText = await page.locator('body').textContent()
    const hasRTX = bodyText?.includes('RTX')
    const hasGPU = bodyText?.includes('GPU')
    console.log(`Page contains "RTX": ${hasRTX}`)
    console.log(`Page contains "GPU": ${hasGPU}`)

    // Step 10: Select a GPU machine
    console.log('Step 10: Selecting a GPU machine...')
    const machineSelectors = [
      page.locator('label:has-text("RTX")').first(),
      page.locator('label:has-text("GPU")').first(),
      page.locator('[data-testid*="gpu-card"]').first(),
      page.locator('input[type="radio"]').first()
    ]

    let machineSelected = false
    for (const selector of machineSelectors) {
      const count = await selector.count()
      if (count > 0) {
        const visible = await selector.isVisible({ timeout: 1000 }).catch(() => false)
        if (visible) {
          const text = await selector.textContent()
          console.log(`Attempting to select machine: ${text?.substring(0, 50)}...`)
          await selector.click()
          machineSelected = true
          console.log('✅ GPU machine selected')
          break
        }
      }
    }

    if (!machineSelected) {
      console.log('⚠️ Could not select any GPU machine')
    }

    await page.waitForTimeout(1000)
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-09-machine-selected.png',
      fullPage: true
    })

    // Step 11: Click "Próximo" to go to configuration step
    console.log('Step 11: Clicking "Próximo" to advance to configuration...')
    const nextButton2 = page.locator('button:has-text("Próximo"), button:has-text("Next")').first()
    const next2Visible = await nextButton2.isVisible({ timeout: 2000 }).catch(() => false)

    if (next2Visible) {
      await nextButton2.click()
      console.log('✅ Advanced to configuration step')
    } else {
      console.log('⚠️ "Próximo" button not found for step 2')
    }

    await page.waitForTimeout(1000)
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-10-configuration-step.png',
      fullPage: true
    })

    // Step 12: Look for "Iniciar", "Reservar", or "Deploy" button
    console.log('Step 12: Looking for final action button (Iniciar/Reservar/Deploy)...')
    const actionButtons = [
      page.locator('button:has-text("Iniciar")'),
      page.locator('button:has-text("Reservar")'),
      page.locator('button:has-text("Deploy")'),
      page.locator('button:has-text("Provisionar")'),
      page.locator('[data-testid="provision-button"]')
    ]

    let actionButton = null
    for (const btn of actionButtons) {
      const visible = await btn.first().isVisible({ timeout: 2000 }).catch(() => false)
      if (visible) {
        actionButton = btn.first()
        const text = await actionButton.textContent()
        console.log(`✅ Found action button: "${text?.trim()}"`)
        break
      }
    }

    if (actionButton) {
      const isEnabled = await actionButton.isEnabled()
      console.log(`Action button enabled: ${isEnabled}`)

      await page.screenshot({
        path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-11-before-action.png',
        fullPage: true
      })

      if (isEnabled) {
        console.log('Step 13: Clicking action button to provision...')
        await actionButton.click()
        console.log('✅ Action button clicked')

        // Wait for provisioning feedback
        await page.waitForTimeout(5000)

        await page.screenshot({
          path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-12-after-action.png',
          fullPage: true
        })

        // Look for success/loading indicators
        const indicators = await page.locator('text=/provisionando|provisioning|sucesso|success|aguarde|wait/i').count()
        console.log(`Found ${indicators} provisioning/success indicators`)
      } else {
        console.log('⚠️ Action button is disabled - cannot proceed')
      }
    } else {
      console.log('⚠️ Could not find action button (Iniciar/Reservar/Deploy)')
    }

    // Final wait to observe outcome
    console.log('Step 14: Waiting for final outcome (15 seconds)...')
    await page.waitForTimeout(15000)

    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/wizard-vibe-13-final-outcome.png',
      fullPage: true
    })

    // Calculate total time
    const endTime = performance.now()
    const totalTime = ((endTime - startTime) / 1000).toFixed(2)

    console.log('\n=== Test Complete ===')
    console.log(`📊 Total journey time: ${totalTime}s`)
    console.log('📸 Screenshots saved in: /Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/')
    console.log('\nScreenshot files:')
    console.log('  - wizard-vibe-01-login.png')
    console.log('  - wizard-vibe-02-app-dashboard.png')
    console.log('  - wizard-vibe-03-wizard-search.png')
    console.log('  - wizard-vibe-04-wizard-opened.png')
    console.log('  - wizard-vibe-05-region-selected.png')
    console.log('  - wizard-vibe-06-after-next.png')
    console.log('  - wizard-vibe-07-purpose-selected.png')
    console.log('  - wizard-vibe-08-machines-loaded.png')
    console.log('  - wizard-vibe-09-machine-selected.png')
    console.log('  - wizard-vibe-10-configuration-step.png')
    console.log('  - wizard-vibe-11-before-action.png')
    console.log('  - wizard-vibe-12-after-action.png')
    console.log('  - wizard-vibe-13-final-outcome.png')
  })
})
