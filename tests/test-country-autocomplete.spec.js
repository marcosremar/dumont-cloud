import { test, expect } from '@playwright/test'

// Disable auth for this test
test.use({ storageState: undefined })

test('Test country autocomplete on new machines page', async ({ page }) => {
  // Step 1: Navigate to the page
  console.log('Step 1: Navigating to new machines page...')
  await page.goto('http://localhost:4892/demo-app/machines/new')
  await page.waitForLoadState('networkidle')

  // Check current URL
  const currentUrl = page.url()
  console.log(`Current URL: ${currentUrl}`)

  // If we got redirected, try clicking the "New Machine" button from the dashboard
  if (!currentUrl.includes('/machines/new')) {
    console.log('Got redirected. Looking for "New Machine" or "Nova Máquina" button...')

    // Try to find and click "New Machine" button
    const newMachineButton = page.getByText(/Nova Máquina|New Machine/i).first()
    const buttonExists = await newMachineButton.isVisible().catch(() => false)

    if (buttonExists) {
      console.log('Found button, clicking...')
      await newMachineButton.click()
      await page.waitForLoadState('networkidle')
      console.log(`After click, URL: ${page.url()}`)
    } else {
      // Try navigating to machines page first
      console.log('Trying /demo-app/machines first...')
      await page.goto('http://localhost:4892/demo-app/machines')
      await page.waitForLoadState('networkidle')
      await page.screenshot({ path: 'tests/screenshots/country-autocomplete-0-machines-page.png', fullPage: true })

      // Now try to find new machine button
      const newBtn = page.getByText(/Nova Máquina|New Machine|Create Machine/i).first()
      const btnVisible = await newBtn.isVisible().catch(() => false)

      if (btnVisible) {
        console.log('Found "New Machine" button on machines page')
        await newBtn.click()
        await page.waitForLoadState('networkidle')
      }
    }
  }

  // Take initial snapshot
  console.log('Taking initial snapshot...')
  await page.screenshot({ path: 'tests/screenshots/country-autocomplete-1-initial.png', fullPage: true })

  // Step 2: Find the search input
  console.log('Step 2: Looking for country search input...')

  // Try to find the input by placeholder text
  const searchInput = page.getByPlaceholder(/Type country or region|search.*countries/i)
  const inputExists = await searchInput.count()

  console.log(`Found ${inputExists} input(s) with "Search for countries" placeholder`)

  if (inputExists === 0) {
    // Try alternative selectors
    console.log('Trying alternative selectors...')
    const allInputs = await page.locator('input').all()
    console.log(`Total inputs found on page: ${allInputs.length}`)

    for (let i = 0; i < allInputs.length; i++) {
      const input = allInputs[i]
      const placeholder = await input.getAttribute('placeholder')
      const type = await input.getAttribute('type')
      console.log(`Input ${i}: placeholder="${placeholder}", type="${type}"`)
    }
  }

  // Step 3: Type "Brasil" in the search field
  if (inputExists > 0) {
    console.log('Step 3: Typing "Brasil" in search field...')
    await searchInput.fill('Brasil')

    // Wait a moment for autocomplete to appear
    await page.waitForTimeout(1000)

    // Take snapshot after typing
    console.log('Taking snapshot after typing...')
    await page.screenshot({ path: 'tests/screenshots/country-autocomplete-2-after-typing.png', fullPage: true })

    // Step 4: Check if autocomplete dropdown appeared
    console.log('Step 4: Checking for autocomplete dropdown...')

    // Look for common autocomplete patterns
    const dropdowns = await page.locator('[role="listbox"], .autocomplete, .dropdown, ul[class*="suggestion"], div[class*="dropdown"]').all()
    console.log(`Found ${dropdowns.length} potential dropdown elements`)

    for (let i = 0; i < dropdowns.length; i++) {
      const dropdown = dropdowns[i]
      const isVisible = await dropdown.isVisible()
      const text = await dropdown.textContent()
      console.log(`Dropdown ${i}: visible=${isVisible}, text="${text?.substring(0, 100)}"`)
    }

    // Check if "Brasil" appears in any visible element
    const brasilMatches = await page.locator('text=/Brasil/i').all()
    console.log(`Found ${brasilMatches.length} elements containing "Brasil"`)

    for (let i = 0; i < brasilMatches.length; i++) {
      const match = brasilMatches[i]
      const isVisible = await match.isVisible()
      if (isVisible) {
        const text = await match.textContent()
        console.log(`Visible Brasil match ${i}: "${text}"`)
      }
    }

    // Step 5: Try to click on a result if available
    const brasilOption = page.locator('text=/Brasil/i').first()
    const optionVisible = await brasilOption.isVisible().catch(() => false)

    if (optionVisible) {
      console.log('Step 5: Clicking on Brasil option...')
      await brasilOption.click()
      await page.waitForTimeout(500)

      // Take snapshot after selection
      console.log('Taking snapshot after selection...')
      await page.screenshot({ path: 'tests/screenshots/country-autocomplete-3-after-selection.png', fullPage: true })

      // Check for tags
      const tags = await page.locator('[class*="tag"], [class*="chip"], [class*="badge"]').all()
      console.log(`Found ${tags.length} potential tag elements`)

      for (let i = 0; i < tags.length; i++) {
        const tag = tags[i]
        const text = await tag.textContent()
        console.log(`Tag ${i}: "${text}"`)
      }
    } else {
      console.log('Step 5: No Brasil option is visible to click')
    }
  } else {
    console.log('Could not find country search input - test cannot proceed')
    await page.screenshot({ path: 'tests/screenshots/country-autocomplete-ERROR-no-input.png', fullPage: true })
  }

  // Wait a bit before closing
  await page.waitForTimeout(2000)
})
