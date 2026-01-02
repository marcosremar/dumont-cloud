const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 300 });
  const page = await browser.newPage();

  try {
    await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "networkidle" });
    await page.waitForTimeout(3000);

    await page.click("button", { hasText: "Guiado" });
    await page.waitForTimeout(1500);

    // Clicar EUA
    await page.click("button", { hasText: "EUA" });
    await page.waitForTimeout(500);

    // Clicar Próximo
    await page.click("button", { hasText: "Próximo" });
    await page.waitForTimeout(2000);

    // Debug Step 2
    const debug = await page.evaluate(() => {
      const bodyText = document.body.innerText;
      const wizardSection = document.getElementById("wizard-form-section");
      return {
        hasWizardSection: wizardSection !== null,
        wizardHTML: wizardSection ? wizardSection.innerHTML.substring(0, 2000) : "No wizard section",
        hasHardwareText: bodyText.includes("Hardware"),
        hasTier: bodyText.includes("Tier") || bodyText.includes("tier"),
        hasButtons: document.querySelectorAll("button").length,
        stepIndicator: bodyText.includes("2/4")
      };
    });

    console.log("Debug Step 2:", JSON.stringify(debug, null, 2));
    await page.screenshot({ path: "tests/tests/step2-debug.png", fullPage: true });

  } catch (error) {
    console.error("Error:", error.message);
  } finally {
    await browser.close();
  }
})();
