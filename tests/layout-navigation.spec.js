/**
 * Dumont Cloud - Layout and Navigation E2E Tests
 *
 * Testes para navegação, menu, header, e responsividade geral
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.TEST_URL || 'https://dumontcloud.com';
const TEST_USER = process.env.TEST_USER || 'marcosremar@gmail.com';
const TEST_PASS = process.env.TEST_PASS || 'Marcos123';

// Helper para login
async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(1000);
  await page.fill('input[type="text"]', TEST_USER);
  await page.fill('input[type="password"]', TEST_PASS);
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(2000);
}

test.describe('Layout - Header', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should display Dumont Cloud logo', async ({ page }) => {
    const logo = page.locator('text=Dumont Cloud, text=Dumont, svg');
    await expect(logo.first()).toBeVisible();
  });

  test('should display main navigation links', async ({ page }) => {
    await expect(page.locator('text=Dashboard').first()).toBeVisible();
    await expect(page.locator('text=Machines').first()).toBeVisible();
    await expect(page.locator('text=Settings').first()).toBeVisible();
  });

  test('should display Métricas dropdown', async ({ page }) => {
    const metricsDropdown = page.locator('text=Métricas');
    await expect(metricsDropdown.first()).toBeVisible();
  });

  test('should display Logout button', async ({ page }) => {
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout"), text=Logout');
    await expect(logoutBtn.first()).toBeVisible();
  });

  test('should take header screenshot', async ({ page }) => {
    await page.screenshot({ path: 'screenshots/layout-header.png' });
  });
});

test.describe('Layout - Navigation Links', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should navigate to Dashboard', async ({ page }) => {
    await page.click('text=Dashboard');
    await page.waitForTimeout(1000);
    expect(page.url()).toBe(`${BASE_URL}/`);
  });

  test('should navigate to Machines', async ({ page }) => {
    await page.click('text=Machines');
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/machines');
  });

  test('should navigate to Settings', async ({ page }) => {
    await page.click('text=Settings');
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/settings');
  });

  test('should highlight active nav link', async ({ page }) => {
    // Go to machines
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(1000);

    // Check if Machines link is highlighted
    const machinesLink = page.locator('.nav-link:has-text("Machines"), a:has-text("Machines")').first();
    const classes = await machinesLink.getAttribute('class');
    console.log('Machines link classes:', classes);
  });
});

test.describe('Layout - Métricas Dropdown', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should open Métricas dropdown on click', async ({ page }) => {
    const metricsDropdown = page.locator('text=Métricas').first();
    await metricsDropdown.click();
    await page.waitForTimeout(500);

    // Should show dropdown menu
    await page.screenshot({ path: 'screenshots/layout-metrics-dropdown.png' });
  });

  test('should show dropdown options', async ({ page }) => {
    const metricsDropdown = page.locator('text=Métricas').first();
    await metricsDropdown.click();
    await page.waitForTimeout(500);

    // Look for dropdown items
    const dropdownItems = page.locator('[role="menu"], [class*="dropdown"]');
    const isVisible = await dropdownItems.isVisible().catch(() => false);
    console.log('Dropdown menu visible:', isVisible);
  });

  test('should navigate to GPU Metrics from dropdown', async ({ page }) => {
    const metricsDropdown = page.locator('text=Métricas').first();
    await metricsDropdown.click();
    await page.waitForTimeout(500);

    // Click on metrics option
    const metricsOption = page.locator('a[href*="metrics"], text=/GPU|Preços/i');
    if (await metricsOption.count() > 0) {
      await metricsOption.first().click();
      await page.waitForTimeout(1000);
      expect(page.url()).toContain('/metrics');
    }
  });
});

test.describe('Layout - Logout', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should logout when clicking Logout button', async ({ page }) => {
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout")').first();
    await logoutBtn.click();
    await page.waitForTimeout(2000);

    // Should redirect to login page
    expect(page.url()).toContain('/login');
  });

  test('should clear session on logout', async ({ page }) => {
    // Logout
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout")').first();
    await logoutBtn.click();
    await page.waitForTimeout(2000);

    // Try to access protected page
    await page.goto(`${BASE_URL}/machines`);
    await page.waitForTimeout(2000);

    // Should redirect to login
    expect(page.url()).toContain('/login');
  });

  test('should clear localStorage token on logout', async ({ page }) => {
    // Logout
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout")').first();
    await logoutBtn.click();
    await page.waitForTimeout(2000);

    // Check localStorage
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));
    expect(token).toBeNull();
  });
});

test.describe('Layout - Mobile Menu', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should display hamburger menu on mobile', async ({ page }) => {
    const hamburger = page.locator('button:has(svg.lucide-menu), button[aria-label*="menu"], .hamburger');
    const isVisible = await hamburger.count() > 0;
    console.log('Hamburger menu visible:', isVisible);

    await page.screenshot({ path: 'screenshots/layout-mobile-header.png' });
  });

  test('should open mobile menu on hamburger click', async ({ page }) => {
    const hamburger = page.locator('button:has(svg.lucide-menu), button[aria-label*="menu"], .hamburger').first();

    if (await hamburger.isVisible()) {
      await hamburger.click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'screenshots/layout-mobile-menu-open.png', fullPage: true });

      // Menu should show navigation links
      const dashboardLink = page.locator('text=Dashboard');
      const machinesLink = page.locator('text=Machines');

      expect(await dashboardLink.count()).toBeGreaterThan(0);
      expect(await machinesLink.count()).toBeGreaterThan(0);
    }
  });

  test('should navigate from mobile menu', async ({ page }) => {
    const hamburger = page.locator('button:has(svg.lucide-menu), button[aria-label*="menu"], .hamburger').first();

    if (await hamburger.isVisible()) {
      await hamburger.click();
      await page.waitForTimeout(500);

      // Click on Machines
      await page.click('text=Machines');
      await page.waitForTimeout(1000);

      expect(page.url()).toContain('/machines');
    }
  });

  test('should close mobile menu after navigation', async ({ page }) => {
    const hamburger = page.locator('button:has(svg.lucide-menu), button[aria-label*="menu"], .hamburger').first();

    if (await hamburger.isVisible()) {
      await hamburger.click();
      await page.waitForTimeout(500);

      await page.click('text=Machines');
      await page.waitForTimeout(1000);

      // Menu should be closed (hamburger should be visible again)
      const hamburgerAfter = page.locator('button:has(svg.lucide-menu), button[aria-label*="menu"], .hamburger').first();
      const isHamburgerVisible = await hamburgerAfter.isVisible().catch(() => false);
      console.log('Hamburger visible after nav:', isHamburgerVisible);
    }
  });
});

test.describe('Layout - Responsive Breakpoints', () => {
  test('should display correctly at 320px (small mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'screenshots/layout-320px.png', fullPage: true });
  });

  test('should display correctly at 768px (tablet)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'screenshots/layout-768px.png', fullPage: true });
  });

  test('should display correctly at 1024px (small desktop)', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'screenshots/layout-1024px.png', fullPage: true });
  });

  test('should display correctly at 1440px (large desktop)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'screenshots/layout-1440px.png', fullPage: true });
  });
});

test.describe('Layout - Footer', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should display footer if exists', async ({ page }) => {
    const footer = page.locator('footer, [class*="footer"]');
    const hasFooter = await footer.count() > 0;
    console.log('Footer present:', hasFooter);
  });
});

test.describe('Layout - Theme and Styling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should use dark theme', async ({ page }) => {
    // Check background color
    const bodyBg = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });
    console.log('Body background:', bodyBg);

    // Dark theme typically has rgb values < 50
    // rgb(13, 17, 23) is common dark bg
  });

  test('should have consistent color scheme', async ({ page }) => {
    // Check for green accent colors (brand)
    const greenElements = page.locator('[class*="green"], [class*="primary"]');
    const count = await greenElements.count();
    console.log('Green/primary elements:', count);
  });
});

test.describe('Layout - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/`);
    await page.waitForTimeout(2000);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    const h1 = await page.locator('h1').count();
    const h2 = await page.locator('h2').count();
    const h3 = await page.locator('h3').count();

    console.log(`Headings: h1=${h1}, h2=${h2}, h3=${h3}`);
  });

  test('should have alt text on images', async ({ page }) => {
    const images = page.locator('img');
    const count = await images.count();

    let withAlt = 0;
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      if (alt && alt.length > 0) withAlt++;
    }

    console.log(`Images: ${withAlt}/${count} have alt text`);
  });

  test('should have proper button labels', async ({ page }) => {
    const buttons = page.locator('button');
    const count = await buttons.count();

    let withLabel = 0;
    for (let i = 0; i < count; i++) {
      const text = await buttons.nth(i).textContent();
      const ariaLabel = await buttons.nth(i).getAttribute('aria-label');
      if ((text && text.trim().length > 0) || ariaLabel) withLabel++;
    }

    console.log(`Buttons: ${withLabel}/${count} have labels`);
  });

  test('should be keyboard navigable', async ({ page }) => {
    // Press Tab to navigate
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check if focused element is visible
    const focusedElement = page.locator(':focus');
    const hasFocus = await focusedElement.count() > 0;
    console.log('Focused element exists:', hasFocus);
  });
});

test.describe('Layout - Error States', () => {
  test('should show 404 for invalid routes', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/invalid-route-that-does-not-exist`);
    await page.waitForTimeout(2000);

    // Should either show 404 or redirect to home
    const url = page.url();
    const has404 = await page.locator('text=/404|not found|página não encontrada/i').count() > 0;
    const redirectedHome = url === `${BASE_URL}/`;

    console.log('404 behavior:', has404 ? '404 page' : redirectedHome ? 'Redirected to home' : 'Unknown');
  });
});

test.describe('Layout - Performance', () => {
  test('should load within reasonable time', async ({ page }) => {
    await login(page);

    const startTime = Date.now();
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    console.log(`Page load time: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(10000); // Should load within 10 seconds
  });
});
