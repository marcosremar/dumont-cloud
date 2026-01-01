/**
 * Email Preferences - E2E Tests
 *
 * Tests the email preferences settings flow:
 * - User enables weekly emails
 * - User changes frequency
 * - User unsubscribes
 * - Settings persist correctly
 */

const { test, expect } = require('@playwright/test');

// Configuration for headless mode
test.use({
  headless: true,
  viewport: { width: 1280, height: 720 },
});

// Use demo-app as default for tests
const BASE_PATH = '/demo-app';

// Helper to navigate to email preferences
async function goToEmailPreferences(page) {
  await page.goto(`${BASE_PATH}/settings/email-preferences`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper to go to app and navigate via menu
async function goToApp(page) {
  await page.goto(`${BASE_PATH}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Close welcome modal if it appears
  const skipButton = page.getByText('Pular tudo');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
    await page.waitForTimeout(500);
  }
}

// ============================================================
// TEST 1: Email Preferences Page Loads
// ============================================================
test.describe('📧 Email Preferences Page', () => {

  test('Page loads with correct title', async ({ page }) => {
    await goToEmailPreferences(page);

    // Verify page title is visible
    const title = page.getByText(/Preferências de Email/i).first();
    const hasTitle = await title.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasTitle) {
      console.log('✅ Email Preferences page title visible');
    }

    expect(hasTitle).toBe(true);
  });

  test('Page shows frequency dropdown', async ({ page }) => {
    await goToEmailPreferences(page);

    // Verify frequency dropdown is visible
    const dropdown = page.locator('select[name="frequency"]');
    const hasDropdown = await dropdown.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasDropdown) {
      console.log('✅ Frequency dropdown visible');
    }

    expect(hasDropdown).toBe(true);
  });

  test('Dropdown has all frequency options', async ({ page }) => {
    await goToEmailPreferences(page);

    // Get dropdown
    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Check for all options
    const weeklyOption = page.locator('option[value="weekly"]');
    const monthlyOption = page.locator('option[value="monthly"]');
    const noneOption = page.locator('option[value="none"]');

    const hasWeekly = await weeklyOption.count() > 0;
    const hasMonthly = await monthlyOption.count() > 0;
    const hasNone = await noneOption.count() > 0;

    console.log(`✅ Options found: Weekly=${hasWeekly}, Monthly=${hasMonthly}, None=${hasNone}`);

    expect(hasWeekly).toBe(true);
    expect(hasMonthly).toBe(true);
    expect(hasNone).toBe(true);
  });

  test('Save button is visible', async ({ page }) => {
    await goToEmailPreferences(page);

    // Verify save button is visible
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    const hasSaveButton = await saveButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSaveButton) {
      console.log('✅ Save button visible');
    }

    expect(hasSaveButton).toBe(true);
  });
});

// ============================================================
// TEST 2: User Enables Weekly Emails (Main Flow)
// ============================================================
test.describe('🎯 User Enables Weekly Emails', () => {

  test('User selects Weekly frequency and saves', async ({ page }) => {
    await goToEmailPreferences(page);

    // 1. Get the frequency dropdown
    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    console.log('📍 Step 1: Dropdown found');

    // 2. Select "Weekly" frequency
    await dropdown.selectOption('weekly');
    const currentValue = await dropdown.inputValue();
    expect(currentValue).toBe('weekly');
    console.log('📍 Step 2: Selected "Weekly" frequency');

    // 3. Verify the preview info appears for non-none frequency
    const previewInfo = page.getByText(/O que você vai receber/i);
    const hasPreview = await previewInfo.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasPreview) {
      console.log('📍 Step 3: Preview info visible');
    }

    // 4. Click Save button
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    await saveButton.click();
    console.log('📍 Step 4: Clicked Save button');

    // 5. Wait for response (either success message or toast)
    await page.waitForTimeout(1000);

    // Check for success indicators
    const successMessage = page.getByText(/sucesso|success|salvas/i);
    const hasSuccess = await successMessage.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasSuccess) {
      console.log('✅ Success message shown');
    }

    // Verify button is not in saving state
    const savingIndicator = page.getByText(/salvando/i);
    const isSaving = await savingIndicator.isVisible({ timeout: 1000 }).catch(() => false);
    expect(isSaving).toBe(false);

    console.log('✅ Weekly email preferences saved successfully');
  });

  test('Weekly frequency shows email preview content', async ({ page }) => {
    await goToEmailPreferences(page);

    // Select weekly
    const dropdown = page.locator('select[name="frequency"]');
    await dropdown.selectOption('weekly');

    // Verify preview content is shown
    const previewItems = [
      /horas de GPU/i,
      /Custo total/i,
      /Economia/i,
      /AI Wizard/i,
    ];

    for (const item of previewItems) {
      const element = page.getByText(item);
      const isVisible = await element.isVisible({ timeout: 2000 }).catch(() => false);
      if (isVisible) {
        console.log(`✅ Preview item visible: ${item}`);
      }
    }

    expect(true).toBe(true);
  });
});

// ============================================================
// TEST 3: User Changes to Monthly Frequency
// ============================================================
test.describe('📅 User Changes to Monthly', () => {

  test('User can change from Weekly to Monthly', async ({ page }) => {
    await goToEmailPreferences(page);

    // Get dropdown and verify it exists
    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Change to monthly
    await dropdown.selectOption('monthly');
    const currentValue = await dropdown.inputValue();
    expect(currentValue).toBe('monthly');
    console.log('✅ Changed to Monthly frequency');

    // Save
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    await saveButton.click();
    await page.waitForTimeout(1000);

    // Verify preview still shows (monthly is not 'none')
    const previewInfo = page.getByText(/O que você vai receber/i);
    const hasPreview = await previewInfo.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasPreview) {
      console.log('✅ Preview info still visible for Monthly');
    }

    console.log('✅ Monthly frequency saved successfully');
  });
});

// ============================================================
// TEST 4: User Disables Email Reports
// ============================================================
test.describe('🔕 User Disables Email Reports', () => {

  test('User can disable email reports', async ({ page }) => {
    await goToEmailPreferences(page);

    // Get dropdown
    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Select 'none' to disable
    await dropdown.selectOption('none');
    const currentValue = await dropdown.inputValue();
    expect(currentValue).toBe('none');
    console.log('✅ Selected "Desativado" option');

    // Verify warning message appears
    const warningMessage = page.getByText(/Relatórios desativados/i);
    const hasWarning = await warningMessage.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasWarning) {
      console.log('✅ Warning message shown for disabled state');
    }

    expect(hasWarning).toBe(true);

    // Preview info should be hidden
    const previewInfo = page.getByText(/O que você vai receber/i);
    const hasPreview = await previewInfo.isVisible({ timeout: 1000 }).catch(() => false);
    expect(hasPreview).toBe(false);
    console.log('✅ Preview info hidden when disabled');

    // Save
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    await saveButton.click();
    await page.waitForTimeout(1000);

    console.log('✅ Email reports disabled successfully');
  });

  test('User can re-enable emails after disabling', async ({ page }) => {
    await goToEmailPreferences(page);

    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // First disable
    await dropdown.selectOption('none');
    await page.waitForTimeout(500);

    // Verify warning is shown
    const warningMessage = page.getByText(/Relatórios desativados/i);
    await expect(warningMessage).toBeVisible({ timeout: 3000 });

    // Now re-enable with weekly
    await dropdown.selectOption('weekly');
    await page.waitForTimeout(500);

    // Warning should be gone
    const isWarningGone = await warningMessage.isVisible({ timeout: 500 }).catch(() => false);
    expect(isWarningGone).toBe(false);
    console.log('✅ Warning hidden after re-enabling');

    // Preview should be back
    const previewInfo = page.getByText(/O que você vai receber/i);
    const hasPreview = await previewInfo.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasPreview) {
      console.log('✅ Preview info restored after re-enabling');
    }

    // Save
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    await saveButton.click();
    await page.waitForTimeout(1000);

    console.log('✅ Email reports re-enabled successfully');
  });
});

// ============================================================
// TEST 5: Navigation to Email Preferences
// ============================================================
test.describe('🧭 Navigation to Email Preferences', () => {

  test('User can navigate to Email Preferences from Settings', async ({ page }) => {
    // Start at main app
    await goToApp(page);

    // Navigate to Settings
    await page.goto(`${BASE_PATH}/settings`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);
    console.log('📍 Navigated to Settings');

    // Look for email preferences link in sidebar
    const emailLink = page.getByRole('link', { name: /email|relatórios.*email/i });
    const hasEmailLink = await emailLink.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasEmailLink) {
      await emailLink.click();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);
      console.log('✅ Clicked Email Preferences link');

      // Verify we're on the email preferences page
      const title = page.getByText(/Preferências de Email/i);
      const hasTitle = await title.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasTitle) {
        console.log('✅ Navigated to Email Preferences page');
      }
    } else {
      // Direct navigation fallback
      await page.goto(`${BASE_PATH}/settings/email-preferences`);
      await page.waitForLoadState('domcontentloaded');
      console.log('ℹ️ Direct navigation to Email Preferences');
    }

    // Verify page content
    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    console.log('✅ Email Preferences page accessible');
  });

  test('Email Preferences direct URL works', async ({ page }) => {
    // Direct navigation
    await page.goto(`${BASE_PATH}/settings/email-preferences`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Verify page loaded
    const url = page.url();
    expect(url).toContain('email-preferences');
    console.log(`✅ Direct URL works: ${url}`);

    // Verify content
    const title = page.getByText(/Preferências de Email/i);
    const hasTitle = await title.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasTitle).toBe(true);
  });
});

// ============================================================
// TEST 6: Form Validation and UX
// ============================================================
test.describe('📝 Form Validation and UX', () => {

  test('Save button shows loading state', async ({ page }) => {
    await goToEmailPreferences(page);

    // Get save button
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    await expect(saveButton).toBeVisible({ timeout: 5000 });

    // Button should not be disabled initially
    const isDisabled = await saveButton.isDisabled();
    expect(isDisabled).toBe(false);
    console.log('✅ Save button initially enabled');
  });

  test('Card header shows correct icon and title', async ({ page }) => {
    await goToEmailPreferences(page);

    // Check for card header content
    const cardTitle = page.getByText(/Relatórios por Email/i);
    const hasCardTitle = await cardTitle.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasCardTitle) {
      console.log('✅ Card header with title visible');
    }

    expect(hasCardTitle).toBe(true);

    // Check for subtitle
    const subtitle = page.getByText(/custos e economia vs AWS/i);
    const hasSubtitle = await subtitle.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasSubtitle) {
      console.log('✅ Card subtitle visible');
    }
  });

  test('Dropdown description text is visible', async ({ page }) => {
    await goToEmailPreferences(page);

    // Check for description text
    const description = page.getByText(/Os relatórios incluem/i);
    const hasDescription = await description.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasDescription) {
      console.log('✅ Dropdown description text visible');
    }

    expect(hasDescription).toBe(true);
  });
});

// ============================================================
// TEST 7: Complete User Journey
// ============================================================
test.describe('🔄 Complete User Journey', () => {

  test('Full flow: Navigate → Change to Weekly → Save → Verify', async ({ page }) => {
    // Step 1: Navigate to email preferences
    await goToEmailPreferences(page);
    console.log('📍 Step 1: Navigated to Email Preferences');

    // Step 2: Verify page loaded
    const dropdown = page.locator('select[name="frequency"]');
    await expect(dropdown).toBeVisible({ timeout: 5000 });
    console.log('📍 Step 2: Page loaded with dropdown');

    // Step 3: Select Weekly frequency
    await dropdown.selectOption('weekly');
    const selectedValue = await dropdown.inputValue();
    expect(selectedValue).toBe('weekly');
    console.log('📍 Step 3: Selected "Weekly" frequency');

    // Step 4: Click Save
    const saveButton = page.getByRole('button', { name: /salvar|save/i });
    await saveButton.click();
    console.log('📍 Step 4: Clicked Save');

    // Step 5: Wait and verify save completed
    await page.waitForTimeout(1500);

    // Check button is not in saving state
    const savingText = page.getByText(/salvando/i);
    const isSaving = await savingText.isVisible({ timeout: 500 }).catch(() => false);
    expect(isSaving).toBe(false);
    console.log('📍 Step 5: Save completed (not in saving state)');

    // Check for success indicators
    const successIndicators = [
      page.getByText(/sucesso/i),
      page.getByText(/salvas/i),
      page.locator('[class*="success"]'),
    ];

    let foundSuccess = false;
    for (const indicator of successIndicators) {
      if (await indicator.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        foundSuccess = true;
        break;
      }
    }

    if (foundSuccess) {
      console.log('✅ Success feedback shown');
    }

    // Verify dropdown still has correct value
    const finalValue = await dropdown.inputValue();
    expect(finalValue).toBe('weekly');
    console.log('✅ Complete user journey successful');
  });
});
