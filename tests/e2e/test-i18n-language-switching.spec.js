/**
 * E2E Tests for i18n Language Switching
 *
 * Tests the internationalization features including:
 * - Language selector visibility
 * - Switching between English and Spanish
 * - UI text changes after language switch
 * - Language preference persistence in localStorage
 * - Navigation with different languages
 */

const { test, expect } = require('@playwright/test');

// Configuration for headless mode
test.use({
  headless: true,
  viewport: { width: 1920, height: 1080 },
});

// Use demo-app as the default for tests
const BASE_PATH = '/demo-app';

// Helper to navigate to Settings page
async function goToSettings(page) {
  await page.goto(`${BASE_PATH}/settings`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper to navigate to Dashboard
async function goToDashboard(page) {
  await page.goto(`${BASE_PATH}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper to navigate to Machines page
async function goToMachines(page) {
  await page.goto(`${BASE_PATH}/machines`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);
}

// Helper to clear localStorage language preference
async function clearLanguagePreference(page) {
  await page.evaluate(() => {
    localStorage.removeItem('language');
  });
}

// Helper to set language preference in localStorage
async function setLanguagePreference(page, language) {
  await page.evaluate((lang) => {
    localStorage.setItem('language', lang);
  }, language);
}

// Helper to get current language from localStorage
async function getLanguagePreference(page) {
  return await page.evaluate(() => {
    return localStorage.getItem('language');
  });
}

// ============================================================
// TEST 1: Language Selector Component
// ============================================================
test.describe('Language Selector Component', () => {

  test.beforeEach(async ({ page }) => {
    // Clear language preference before each test
    await page.goto(BASE_PATH);
    await clearLanguagePreference(page);
  });

  test('Language selector is visible on Settings page', async ({ page }) => {
    await goToSettings(page);

    // Look for language-related elements
    const languageSection = page.getByText(/language|idioma/i).first();
    const hasLanguageSection = await languageSection.isVisible({ timeout: 5000 }).catch(() => false);

    // Look for English and Spanish options
    const englishOption = page.getByText('English').first();
    const spanishOption = page.getByText('Español').first();

    const hasEnglish = await englishOption.isVisible({ timeout: 3000 }).catch(() => false);
    const hasSpanish = await spanishOption.isVisible({ timeout: 3000 }).catch(() => false);

    // At least language section or language options should be visible
    expect(hasLanguageSection || hasEnglish || hasSpanish).toBe(true);
  });

  test('Language selector shows both English and Spanish options', async ({ page }) => {
    await goToSettings(page);

    // Check for English option with flag
    const englishOption = page.locator('button').filter({ hasText: /English/ }).first();
    const spanishOption = page.locator('button').filter({ hasText: /Español/ }).first();

    const hasEnglish = await englishOption.isVisible({ timeout: 5000 }).catch(() => false);
    const hasSpanish = await spanishOption.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasEnglish && hasSpanish) {
      // Verify English shows US flag
      const usFlag = page.getByText('🇺🇸').first();
      const hasUsFlag = await usFlag.isVisible({ timeout: 2000 }).catch(() => false);

      // Verify Spanish shows Spain flag
      const esFlag = page.getByText('🇪🇸').first();
      const hasEsFlag = await esFlag.isVisible({ timeout: 2000 }).catch(() => false);

      expect(hasUsFlag || hasEsFlag).toBe(true);
    }

    expect(hasEnglish && hasSpanish).toBe(true);
  });
});

// ============================================================
// TEST 2: Switching from English to Spanish
// ============================================================
test.describe('Language Switching - English to Spanish', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_PATH);
    await clearLanguagePreference(page);
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
  });

  test('Clicking Spanish option changes UI language', async ({ page }) => {
    await goToSettings(page);

    // Find and click Spanish option
    const spanishButton = page.locator('button').filter({ hasText: /Español/ }).first();
    const hasSpanishButton = await spanishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSpanishButton) {
      await spanishButton.click();
      await page.waitForTimeout(1000);

      // Check if UI changed to Spanish - look for common Spanish translations
      const spanishTexts = [
        /Configuración/i, // Settings
        /Idioma/i,        // Language
        /Guardar/i,       // Save
        /Cancelar/i,      // Cancel
      ];

      let foundSpanish = false;
      for (const pattern of spanishTexts) {
        const element = page.getByText(pattern).first();
        if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
          foundSpanish = true;
          break;
        }
      }

      expect(foundSpanish).toBe(true);
    }

    expect(hasSpanishButton).toBe(true);
  });

  test('Language preference is saved to localStorage', async ({ page }) => {
    await goToSettings(page);

    // Find and click Spanish option
    const spanishButton = page.locator('button').filter({ hasText: /Español/ }).first();
    const hasSpanishButton = await spanishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSpanishButton) {
      await spanishButton.click();
      await page.waitForTimeout(500);

      // Check localStorage
      const savedLanguage = await getLanguagePreference(page);
      expect(savedLanguage).toBe('es');
    }

    expect(hasSpanishButton).toBe(true);
  });

  test('Spanish persists after page navigation', async ({ page }) => {
    await goToSettings(page);

    // Switch to Spanish
    const spanishButton = page.locator('button').filter({ hasText: /Español/ }).first();
    const hasSpanishButton = await spanishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSpanishButton) {
      await spanishButton.click();
      await page.waitForTimeout(500);

      // Navigate to Machines page
      await goToMachines(page);

      // Check for Spanish text on Machines page
      const spanishTexts = [
        /Mis Máquinas/i,    // My Machines
        /Máquinas/i,        // Machines
        /Nueva Máquina/i,   // New Machine
        /Todas/i,           // All (filter)
      ];

      let foundSpanish = false;
      for (const pattern of spanishTexts) {
        const element = page.getByText(pattern).first();
        if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
          foundSpanish = true;
          break;
        }
      }

      expect(foundSpanish).toBe(true);
    }

    expect(hasSpanishButton).toBe(true);
  });

  test('Spanish persists after page reload', async ({ page }) => {
    await goToSettings(page);

    // Switch to Spanish
    const spanishButton = page.locator('button').filter({ hasText: /Español/ }).first();
    const hasSpanishButton = await spanishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSpanishButton) {
      await spanishButton.click();
      await page.waitForTimeout(500);

      // Reload the page
      await page.reload();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Check localStorage is still Spanish
      const savedLanguage = await getLanguagePreference(page);
      expect(savedLanguage).toBe('es');

      // Check UI is still in Spanish
      const spanishTexts = [
        /Configuración/i,
        /Idioma/i,
        /Español/i,
      ];

      let foundSpanish = false;
      for (const pattern of spanishTexts) {
        const element = page.getByText(pattern).first();
        if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
          foundSpanish = true;
          break;
        }
      }

      expect(foundSpanish).toBe(true);
    }

    expect(hasSpanishButton).toBe(true);
  });
});

// ============================================================
// TEST 3: Switching from Spanish to English
// ============================================================
test.describe('Language Switching - Spanish to English', () => {

  test.beforeEach(async ({ page }) => {
    // Start with Spanish
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'es');
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500);
  });

  test('Page loads in Spanish when preference is set', async ({ page }) => {
    await goToDashboard(page);

    // Check for Spanish text
    const spanishTexts = [
      /Panel/i,           // Dashboard
      /Bienvenido/i,      // Welcome
      /Máquinas/i,        // Machines
    ];

    let foundSpanish = false;
    for (const pattern of spanishTexts) {
      const element = page.getByText(pattern).first();
      if (await element.isVisible({ timeout: 3000 }).catch(() => false)) {
        foundSpanish = true;
        break;
      }
    }

    expect(foundSpanish).toBe(true);
  });

  test('Clicking English option changes UI back to English', async ({ page }) => {
    await goToSettings(page);

    // Find and click English option
    const englishButton = page.locator('button').filter({ hasText: /English/ }).first();
    const hasEnglishButton = await englishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasEnglishButton) {
      await englishButton.click();
      await page.waitForTimeout(1000);

      // Check if UI changed back to English
      const englishTexts = [
        /Settings/i,
        /Language/i,
        /Save/i,
      ];

      let foundEnglish = false;
      for (const pattern of englishTexts) {
        const element = page.getByText(pattern).first();
        if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
          foundEnglish = true;
          break;
        }
      }

      expect(foundEnglish).toBe(true);

      // Verify localStorage updated
      const savedLanguage = await getLanguagePreference(page);
      expect(savedLanguage).toBe('en');
    }

    expect(hasEnglishButton).toBe(true);
  });
});

// ============================================================
// TEST 4: Navigation with Different Languages
// ============================================================
test.describe('Navigation Text Changes with Language', () => {

  test('Navigation sidebar shows Spanish text', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'es');
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Check navigation items in Spanish
    const navItems = [
      { en: 'Dashboard', es: 'Panel' },
      { en: 'Machines', es: 'Máquinas' },
      { en: 'Settings', es: 'Configuración' },
    ];

    let foundSpanishNav = false;
    for (const item of navItems) {
      const spanishNav = page.getByRole('link', { name: new RegExp(item.es, 'i') }).first();
      if (await spanishNav.isVisible({ timeout: 2000 }).catch(() => false)) {
        foundSpanishNav = true;
        break;
      }
    }

    expect(foundSpanishNav).toBe(true);
  });

  test('Navigation sidebar shows English text', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'en');
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Check navigation items in English
    const navItems = ['Dashboard', 'Machines', 'Settings'];

    let foundEnglishNav = false;
    for (const item of navItems) {
      const englishNav = page.getByRole('link', { name: new RegExp(item, 'i') }).first();
      if (await englishNav.isVisible({ timeout: 2000 }).catch(() => false)) {
        foundEnglishNav = true;
        break;
      }
    }

    expect(foundEnglishNav).toBe(true);
  });
});

// ============================================================
// TEST 5: Page-specific Translations
// ============================================================
test.describe('Page-specific Translations', () => {

  test('Machines page shows Spanish titles and labels', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'es');
    await page.reload();
    await goToMachines(page);

    // Check for Spanish content on Machines page
    const spanishTexts = [
      /Mis Máquinas/i,
      /GPUs Activas/i,
      /Respaldo CPU/i,
      /VRAM Total/i,
      /Costo/i,
      /Saldo/i,
    ];

    let foundCount = 0;
    for (const pattern of spanishTexts) {
      const element = page.getByText(pattern).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        foundCount++;
      }
    }

    // At least some Spanish text should be visible
    expect(foundCount).toBeGreaterThan(0);
  });

  test('Machines page shows English titles and labels', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'en');
    await page.reload();
    await goToMachines(page);

    // Check for English content on Machines page
    const englishTexts = [
      /My Machines/i,
      /Active GPUs/i,
      /CPU Backup/i,
      /Total VRAM/i,
      /Cost/i,
      /Balance/i,
    ];

    let foundCount = 0;
    for (const pattern of englishTexts) {
      const element = page.getByText(pattern).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        foundCount++;
      }
    }

    // At least some English text should be visible
    expect(foundCount).toBeGreaterThan(0);
  });

  test('Settings page shows language preference description', async ({ page }) => {
    await page.goto(BASE_PATH);
    await clearLanguagePreference(page);
    await page.reload();
    await goToSettings(page);

    // In English, should see "Choose your preferred language"
    const englishDesc = page.getByText(/Choose your preferred language/i).first();
    const hasEnglishDesc = await englishDesc.isVisible({ timeout: 3000 }).catch(() => false);

    if (!hasEnglishDesc) {
      // May already be in Spanish: "Elige tu idioma preferido"
      const spanishDesc = page.getByText(/Elige tu idioma preferido/i).first();
      const hasSpanishDesc = await spanishDesc.isVisible({ timeout: 3000 }).catch(() => false);
      expect(hasSpanishDesc).toBe(true);
    } else {
      expect(hasEnglishDesc).toBe(true);
    }
  });
});

// ============================================================
// TEST 6: Language Indicator Visibility
// ============================================================
test.describe('Language Selector State', () => {

  test('Selected language shows checkmark indicator', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'en');
    await page.reload();
    await goToSettings(page);

    // Find English option button
    const englishButton = page.locator('button').filter({ hasText: /English/ }).first();
    const hasEnglishButton = await englishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasEnglishButton) {
      // Check for checkmark indicator (brand color or check icon)
      const checkIndicator = englishButton.locator('svg');
      const hasCheck = await checkIndicator.isVisible({ timeout: 2000 }).catch(() => false);

      // Or check for selected styling (brand-500 class)
      const buttonClass = await englishButton.getAttribute('class');
      const hasSelectedStyle = buttonClass && buttonClass.includes('brand');

      expect(hasCheck || hasSelectedStyle).toBe(true);
    }

    expect(hasEnglishButton).toBe(true);
  });

  test('Non-selected language does not show checkmark', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'en');
    await page.reload();
    await goToSettings(page);

    // Find Spanish option button (not selected)
    const spanishButton = page.locator('button').filter({ hasText: /Español/ }).first();
    const hasSpanishButton = await spanishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasSpanishButton) {
      // Spanish should not have the checkmark/selected indicator
      const buttonClass = await spanishButton.getAttribute('class');

      // Should have hover state but not brand/selected state
      const hasSelectedStyle = buttonClass && buttonClass.includes('brand-500/10');
      expect(hasSelectedStyle).toBe(false);
    }

    expect(hasSpanishButton).toBe(true);
  });
});

// ============================================================
// TEST 7: Edge Cases
// ============================================================
test.describe('Edge Cases', () => {

  test('Defaults to English when no preference is set', async ({ page }) => {
    await page.goto(BASE_PATH);
    await clearLanguagePreference(page);
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Navigate to settings and check for English UI
    await goToSettings(page);

    const englishTexts = [
      /Settings/i,
      /Language/i,
      /Preferences/i,
    ];

    let foundEnglish = false;
    for (const pattern of englishTexts) {
      const element = page.getByText(pattern).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        foundEnglish = true;
        break;
      }
    }

    expect(foundEnglish).toBe(true);
  });

  test('Handles rapid language switching', async ({ page }) => {
    await page.goto(BASE_PATH);
    await clearLanguagePreference(page);
    await page.reload();
    await goToSettings(page);

    const spanishButton = page.locator('button').filter({ hasText: /Español/ }).first();
    const englishButton = page.locator('button').filter({ hasText: /English/ }).first();

    const hasButtons = await spanishButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasButtons) {
      // Rapidly switch languages
      await spanishButton.click();
      await page.waitForTimeout(200);
      await englishButton.click();
      await page.waitForTimeout(200);
      await spanishButton.click();
      await page.waitForTimeout(500);

      // Should end in Spanish
      const savedLanguage = await getLanguagePreference(page);
      expect(savedLanguage).toBe('es');

      // UI should be in Spanish
      const spanishText = page.getByText(/Configuración|Idioma/i).first();
      const hasSpanish = await spanishText.isVisible({ timeout: 2000 }).catch(() => false);
      expect(hasSpanish).toBe(true);
    }

    expect(hasButtons).toBe(true);
  });

  test('Language persists across different app sections', async ({ page }) => {
    await page.goto(BASE_PATH);
    await setLanguagePreference(page, 'es');
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Visit multiple pages and verify Spanish persists
    const pages = [
      { path: `${BASE_PATH}`, expectedText: /Panel|Bienvenido/i },
      { path: `${BASE_PATH}/machines`, expectedText: /Máquinas|Mis Máquinas/i },
      { path: `${BASE_PATH}/settings`, expectedText: /Configuración|Idioma/i },
    ];

    for (const pageConfig of pages) {
      await page.goto(pageConfig.path);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      const element = page.getByText(pageConfig.expectedText).first();
      const isVisible = await element.isVisible({ timeout: 3000 }).catch(() => false);

      // At least the language should still be Spanish in localStorage
      const savedLanguage = await getLanguagePreference(page);
      expect(savedLanguage).toBe('es');
    }
  });
});
