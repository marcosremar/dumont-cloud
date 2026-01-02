import { test, expect } from '@playwright/test';

test('Wizard visual verification', async ({ page }) => {
  // Navigate to login page
  await page.goto('http://localhost:4893/login');
  await page.waitForLoadState('networkidle');

  // Check if dev bar is visible and use it to login
  const devBarCredentials = page.locator('code:has-text("marcosremar@gmail.com")');
  const hasDevBar = await devBarCredentials.isVisible().catch(() => false);

  if (hasDevBar) {
    console.log('✓ Dev bar found, clicking credentials to auto-fill');
    await devBarCredentials.click();
    await page.waitForTimeout(500);
  }

  // Get the email and password fields
  const emailField = page.locator('input[type="email"], input[placeholder*="email" i]').first();
  const passwordField = page.locator('input[type="password"]').first();

  // Check current values
  const emailValue = await emailField.inputValue().catch(() => '');
  const passwordValue = await passwordField.inputValue().catch(() => '');
  console.log('Email:', emailValue);
  console.log('Password filled:', passwordValue.length > 0);

  // If not filled, fill them manually
  if (!emailValue) {
    await emailField.fill('marcosremar@gmail.com');
  }
  if (!passwordValue) {
    await passwordField.fill('dumont123');
  }

  // Click login button
  const loginButton = page.locator('button:has-text("Entrar"), button:has-text("Login")').first();
  await page.waitForTimeout(500);

  const isEnabled = await loginButton.isEnabled().catch(() => false);
  console.log('Login button enabled:', isEnabled);

  if (isEnabled) {
    await loginButton.click();
  } else {
    // Try clicking the button anyway
    console.log('Button disabled, trying to click anyway');
    await loginButton.click({ force: true });
  }

  // Wait for redirect to /app
  await page.waitForURL('**/app**', { timeout: 10000 });
  console.log('✓ Redirected to app');

  // Wait for page to load
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Check for wizard modal/dialog
  const wizardModal = page.locator('text="Nova Instância GPU"').first();
  const wizardVisible = await wizardModal.isVisible().catch(() => false);
  console.log(`✓ Wizard modal visible: ${wizardVisible}`);

  // Verify stepper steps
  const steps = [
    { num: '1/4', label: 'Região' },
    { num: '2/4', label: 'Hardware' },
    { num: '3/4', label: 'Estratégia' },
    { num: '4/4', label: 'Provisionar' }
  ];

  for (const step of steps) {
    const stepElement = page.locator(`text="${step.num}"`);
    const visible = await stepElement.isVisible().catch(() => false);
    console.log(`✓ Step ${step.num} (${step.label}): ${visible}`);
  }

  // Check for map
  const mapContainer = page.locator('canvas, svg').first();
  const mapVisible = await mapContainer.isVisible().catch(() => false);
  console.log(`✓ Map visible: ${mapVisible}`);

  // Take screenshot before interaction
  await page.screenshot({
    path: '/Users/marcos/CascadeProjects/dumontcloud/tests/test-results/wizard-step1-before.png',
    fullPage: true
  });

  // Try to select a region
  const regionButtons = ['EUA', 'Europa', 'Ásia'];
  for (const region of regionButtons) {
    const btn = page.locator(`button:has-text("${region}")`);
    const visible = await btn.isVisible().catch(() => false);
    if (visible) {
      console.log(`✓ Found region button: ${region}`);
      await btn.click();
      await page.waitForTimeout(500);
      console.log(`✓ Clicked region: ${region}`);
      break;
    }
  }

  // Take screenshot after region selection
  await page.screenshot({
    path: '/Users/marcos/CascadeProjects/dumontcloud/tests/test-results/wizard-step1-after-region.png',
    fullPage: true
  });

  // Try clicking on map
  if (mapVisible) {
    console.log('Attempting to click on map...');
    await mapContainer.click({ position: { x: 200, y: 150 } });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/test-results/wizard-step1-after-map-click.png',
      fullPage: true
    });
  }

  // Try to proceed to next step
  const nextButton = page.locator('button:has-text("Próximo"), button:has-text("Avançar")');
  const nextVisible = await nextButton.isVisible().catch(() => false);
  console.log(`✓ Next button visible: ${nextVisible}`);

  if (nextVisible) {
    await nextButton.click();
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: '/Users/marcos/CascadeProjects/dumontcloud/tests/test-results/wizard-step2.png',
      fullPage: true
    });
    console.log('✓ Moved to step 2');
  }

  // Final full page screenshot
  await page.screenshot({
    path: '/Users/marcos/CascadeProjects/dumontcloud/tests/test-results/wizard-dashboard.png',
    fullPage: true
  });
  console.log('✓ Screenshots saved');
});
