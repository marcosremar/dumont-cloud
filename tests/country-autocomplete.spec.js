// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Country Search Autocomplete Test
 * Tests the autocomplete functionality for country/region search in the New Machine wizard
 */

test.describe('Country Search Autocomplete', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the new machine page
    await page.goto('http://localhost:4892/demo-app/machines/new');

    // Wait for page to be fully loaded
    await expect(page.locator('text=New GPU Machine')).toBeVisible({ timeout: 10000 });
  });

  test('should display initial state without autocomplete', async ({ page }) => {
    console.log('Step 1: Taking initial snapshot of the page');
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-initial.png', fullPage: true });

    // Search input should be visible
    const searchInput = page.locator('input[placeholder*="Type country or region"]');
    await expect(searchInput).toBeVisible();

    // Autocomplete should not be visible initially
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).not.toBeVisible();
  });

  test('should show autocomplete for "Brasil" search', async ({ page }) => {
    console.log('Step 2: Testing search for "Brasil"');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type "Brasil" (Portuguese)
    await searchInput.fill('Brasil');

    // Wait for autocomplete to appear (min 2 characters required)
    await page.waitForTimeout(500);

    // Autocomplete dropdown should be visible
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).toBeVisible();

    // Should show Brazil in results
    const brazilOption = page.locator('text=Brazil').first();
    await expect(brazilOption).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-brasil.png', fullPage: true });

    console.log('Brasil search completed - autocomplete visible');
  });

  test('should show autocomplete for "Brazil" search', async ({ page }) => {
    console.log('Step 3: Testing search for "Brazil" (English)');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type "Brazil" (English)
    await searchInput.fill('Brazil');

    // Wait for autocomplete to appear
    await page.waitForTimeout(500);

    // Autocomplete dropdown should be visible
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).toBeVisible();

    // Should show Brazil in results
    const brazilOption = page.locator('text=Brazil').first();
    await expect(brazilOption).toBeVisible();

    // Should show country code BR
    const countryCode = page.locator('text=Country • BR');
    await expect(countryCode).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-brazil.png', fullPage: true });

    console.log('Brazil search completed - autocomplete visible');
  });

  test('should filter and show region "Europe"', async ({ page }) => {
    console.log('Step 4: Testing search for "Europe" region');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type "Europe"
    await searchInput.fill('Europe');

    // Wait for autocomplete to appear
    await page.waitForTimeout(500);

    // Autocomplete dropdown should be visible
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).toBeVisible();

    // Should show Europe as a region with country count
    const europeOption = page.locator('text=Europe').first();
    await expect(europeOption).toBeVisible();

    // Should indicate it's a region
    const regionIndicator = page.locator('text=/Region • \\d+ countries/');
    await expect(regionIndicator).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-europe.png', fullPage: true });

    console.log('Europe search completed - region shown in autocomplete');
  });

  test('should select country from autocomplete', async ({ page }) => {
    console.log('Step 5: Testing selection of Brazil from autocomplete');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type "Brazil"
    await searchInput.fill('Brazil');
    await page.waitForTimeout(500);

    // Click on Brazil option
    const brazilOption = page.locator('.absolute.top-full button').filter({ hasText: 'Brazil' }).first();
    await brazilOption.click();

    // Wait for selection to be processed
    await page.waitForTimeout(500);

    // Should show selected location with tag
    const selectedTag = page.locator('text=Selected:');
    await expect(selectedTag).toBeVisible();

    const brazilTag = page.locator('div:has-text("Brazil")').filter({ has: page.locator('button[title="Remove"]') });
    await expect(brazilTag.first()).toBeVisible();

    // Search input should be cleared
    await expect(searchInput).toHaveValue('');

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-selected.png', fullPage: true });

    console.log('Brazil selected successfully');
  });

  test('should show selected indicator when country already selected', async ({ page }) => {
    console.log('Step 6: Testing already selected indicator');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // First, select Brazil
    await searchInput.fill('Brazil');
    await page.waitForTimeout(500);
    const brazilOption = page.locator('.absolute.top-full button').filter({ hasText: 'Brazil' }).first();
    await brazilOption.click();
    await page.waitForTimeout(500);

    // Search for Brazil again
    await searchInput.fill('Brazil');
    await page.waitForTimeout(500);

    // The Brazil option should now show as selected (with check icon)
    const checkIcon = page.locator('.absolute.top-full button:has-text("Brazil")').locator('svg.lucide-check');
    await expect(checkIcon).toBeVisible();

    // The option should be disabled/highlighted
    const selectedOption = page.locator('.absolute.top-full button:has-text("Brazil").bg-brand-500\\/10');
    await expect(selectedOption).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-already-selected.png', fullPage: true });

    console.log('Already selected indicator working correctly');
  });

  test('should show multiple matches for partial search', async ({ page }) => {
    console.log('Step 7: Testing partial search with multiple results');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type "un" to match multiple countries (United States, United Kingdom)
    await searchInput.fill('un');
    await page.waitForTimeout(500);

    // Autocomplete dropdown should be visible
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).toBeVisible();

    // Should show multiple results
    const options = page.locator('.absolute.top-full button');
    const count = await options.count();
    expect(count).toBeGreaterThan(1);

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-multiple.png', fullPage: true });

    console.log(`Found ${count} matching results for "un"`);
  });

  test('should show "no results" for non-matching search', async ({ page }) => {
    console.log('Step 8: Testing no results message');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type something that won't match
    await searchInput.fill('xyz123');
    await page.waitForTimeout(500);

    // Autocomplete dropdown should be visible with no results message
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).toBeVisible();

    // Should show "No countries found" message
    const noResultsMessage = page.locator('text=/No countries found for "xyz123"/');
    await expect(noResultsMessage).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-no-results.png', fullPage: true });

    console.log('No results message shown correctly');
  });

  test('should not show autocomplete with less than 2 characters', async ({ page }) => {
    console.log('Step 9: Testing minimum character requirement');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Type only 1 character
    await searchInput.fill('B');
    await page.waitForTimeout(500);

    // Autocomplete should not be visible
    const autocompleteDropdown = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocompleteDropdown).not.toBeVisible();

    // Now type 2 characters
    await searchInput.fill('Br');
    await page.waitForTimeout(500);

    // Autocomplete should now be visible
    await expect(autocompleteDropdown).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-min-chars.png', fullPage: true });

    console.log('Minimum character requirement working correctly');
  });

  test('should support Portuguese country names', async ({ page }) => {
    console.log('Step 10: Testing Portuguese country names');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Test with "Alemanha" (Germany in Portuguese)
    await searchInput.fill('Alemanha');
    await page.waitForTimeout(500);

    // Should show Germany
    const germanyOption = page.locator('text=Germany').first();
    await expect(germanyOption).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-portuguese.png', fullPage: true });

    console.log('Portuguese country names working correctly');
  });

  test('should clear selection when clicking remove button', async ({ page }) => {
    console.log('Step 11: Testing remove selection');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Select Brazil
    await searchInput.fill('Brazil');
    await page.waitForTimeout(500);
    const brazilOption = page.locator('.absolute.top-full button').filter({ hasText: 'Brazil' }).first();
    await brazilOption.click();
    await page.waitForTimeout(500);

    // Click remove button on the tag
    const removeButton = page.locator('button[title="Remove"]').first();
    await removeButton.click();
    await page.waitForTimeout(500);

    // Selected tag should be gone
    const selectedTag = page.locator('text=Selected:');
    await expect(selectedTag).not.toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-removed.png', fullPage: true });

    console.log('Remove selection working correctly');
  });

  test('should support multi-select of countries', async ({ page }) => {
    console.log('Step 12: Testing multi-select functionality');

    const searchInput = page.locator('input[placeholder*="Type country or region"]');

    // Select Brazil
    await searchInput.fill('Brazil');
    await page.waitForTimeout(500);
    await page.locator('.absolute.top-full button').filter({ hasText: 'Brazil' }).first().click();
    await page.waitForTimeout(500);

    // Select Germany
    await searchInput.fill('Germany');
    await page.waitForTimeout(500);
    await page.locator('.absolute.top-full button').filter({ hasText: 'Germany' }).first().click();
    await page.waitForTimeout(500);

    // Select Japan
    await searchInput.fill('Japan');
    await page.waitForTimeout(500);
    await page.locator('.absolute.top-full button').filter({ hasText: 'Japan' }).first().click();
    await page.waitForTimeout(500);

    // Should show all three selections
    await expect(page.locator('text=Brazil')).toBeVisible();
    await expect(page.locator('text=Germany')).toBeVisible();
    await expect(page.locator('text=Japan')).toBeVisible();

    // Should show "Clear all" button
    const clearAllButton = page.locator('text=Clear all');
    await expect(clearAllButton).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/autocomplete-multi-select.png', fullPage: true });

    console.log('Multi-select working correctly - 3 countries selected');
  });

  test('comprehensive autocomplete test', async ({ page }) => {
    console.log('\n=== COMPREHENSIVE AUTOCOMPLETE TEST ===\n');

    // Take initial snapshot
    console.log('Taking initial page snapshot...');
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/test-1-initial.png', fullPage: true });

    const searchInput = page.locator('input[placeholder*="Type country or region"]');
    await expect(searchInput).toBeVisible();

    // Test 1: Search for "Brasil"
    console.log('\nTest 1: Searching for "Brasil"...');
    await searchInput.fill('Brasil');
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/test-2-brasil-search.png', fullPage: true });

    const autocomplete1 = page.locator('.absolute.top-full.left-0.right-0.mt-1.bg-dark-surface-card');
    await expect(autocomplete1).toBeVisible();
    await expect(page.locator('text=Brazil').first()).toBeVisible();
    console.log('✓ Brasil search shows autocomplete with Brazil');

    // Test 2: Search for "Brazil"
    console.log('\nTest 2: Searching for "Brazil"...');
    await searchInput.clear();
    await searchInput.fill('Brazil');
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/test-3-brazil-search.png', fullPage: true });

    await expect(autocomplete1).toBeVisible();
    await expect(page.locator('text=Brazil').first()).toBeVisible();
    await expect(page.locator('text=Country • BR')).toBeVisible();
    console.log('✓ Brazil search shows autocomplete with country code');

    // Test 3: Select Brazil
    console.log('\nTest 3: Selecting Brazil from autocomplete...');
    await page.locator('.absolute.top-full button').filter({ hasText: 'Brazil' }).first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/test-4-brazil-selected.png', fullPage: true });

    await expect(page.locator('text=Selected:')).toBeVisible();
    await expect(searchInput).toHaveValue('');
    console.log('✓ Brazil selected and shown in tag');

    // Test 4: Search for Europe region
    console.log('\nTest 4: Searching for "Europe" region...');
    await searchInput.fill('Europe');
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/test-5-europe-search.png', fullPage: true });

    await expect(autocomplete1).toBeVisible();
    await expect(page.locator('text=Europe').first()).toBeVisible();
    await expect(page.locator('text=/Region • \\d+ countries/')).toBeVisible();
    console.log('✓ Europe region shown with country count');

    // Test 5: Check already selected indicator
    console.log('\nTest 5: Checking already selected indicator...');
    await searchInput.clear();
    await searchInput.fill('Brazil');
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/Users/marcos/CascadeProjects/dumontcloud/tests/screenshots/test-6-already-selected.png', fullPage: true });

    const checkIcon = page.locator('.absolute.top-full button:has-text("Brazil")').locator('svg.lucide-check');
    await expect(checkIcon).toBeVisible();
    console.log('✓ Already selected indicator (check icon) visible');

    console.log('\n=== ALL AUTOCOMPLETE TESTS PASSED ===\n');
  });
});
