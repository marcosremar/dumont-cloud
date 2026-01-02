const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);

  try { await page.click("text=Pular", { timeout: 3000 }); } catch(e) {}
  await page.click("button", { hasText: "Guiado" });
  await page.waitForTimeout(1000);

  await page.click('button[data-testid="region-eua"]');
  await page.waitForTimeout(500);
  await page.click("button", { hasText: "Próximo" });
  await page.waitForTimeout(1500);

  const debug = await page.evaluate(() => {
    const isDemo = localStorage.getItem("demo_mode") === "true";
    return {
      demoMode: localStorage.getItem("demo_mode"),
      isDemoModeResult: isDemo,
      currentStepCheck: document.body.innerText.includes("2/4"),
      wizardHTML: document.getElementById("wizard-form-section")?.innerHTML.substring(0, 2000) || "NO SECTION"
    };
  });

  console.log("DEBUG:", JSON.stringify(debug, null, 2));

  await browser.close();
})();
