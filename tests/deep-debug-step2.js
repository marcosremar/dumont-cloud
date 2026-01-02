const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  page.on("console", msg => {
    const text = msg.text();
    if (text.includes("error") || text.includes("Error") || text.includes("warn")) {
      console.log("CONSOLE:", text);
    }
  });

  await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  try { await page.click("text=Pular", { timeout: 3000 }); } catch(e) {}
  await page.click("button", { hasText: "Guiado" });
  await page.waitForTimeout(1000);

  await page.click('button[data-testid="region-eua"]');
  await page.waitForTimeout(500);
  await page.click("button", { hasText: "Próximo" });
  await page.waitForTimeout(2000);

  const deepDebug = await page.evaluate(() => {
    const wizardSection = document.getElementById("wizard-form-section");
    if (!wizardSection) return { error: "no wizard section" };

    const allDivs = Array.from(wizardSection.querySelectorAll("div"));
    const contentDivs = allDivs.filter(d => {
      const text = d.textContent;
      return text.includes("Hardware") || text.includes("O que") || text.includes("GPU");
    }).map(d => ({
      className: d.className,
      textContent: d.textContent.substring(0, 100),
      isVisible: d.offsetParent !== null,
      display: window.getComputedStyle(d).display
    }));

    return {
      contentDivsFound: contentDivs.length,
      firstFew: contentDivs.slice(0, 5),
      wizardHTML: wizardSection.innerHTML.substring(2000, 4000)
    };
  });

  console.log("Deep Debug:", JSON.stringify(deepDebug, null, 2));

  await browser.close();
})();
