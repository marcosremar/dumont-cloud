const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  page.on("console", msg => console.log("LOG:", msg.text()));
  page.on("pageerror", err => console.error("PAGE ERROR:", err.message));

  await page.goto("http://localhost:4894/login?auto_login=demo", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  try { await page.click("text=Pular", { timeout: 3000 }); } catch(e) {}
  await page.click("button", { hasText: "Guiado" });
  await page.waitForTimeout(2000);

  console.log("Step 1 - clicking EUA");
  await page.click("button[data-testid=\"region-eua\"]");
  await page.waitForTimeout(1000);

  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    btn?.click();
  });
  await page.waitForTimeout(2000);

  console.log("Step 2 - selecting Desenvolver");
  await page.click("button:has-text(\"Desenvolver\")");
  await page.waitForTimeout(2000);

  console.log("Step 2 - clicking Próximo");
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    btn?.click();
  });
  await page.waitForTimeout(2000);

  console.log("Step 3 - clicking Iniciar");
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Iniciar") && !b.disabled);
    btn?.click();
  });

  console.log("Waiting for provisioning...");
  await page.waitForTimeout(6000);

  const check = await page.evaluate(() => {
    return {
      hasUsar: document.body.innerText.includes("Usar Esta Máquina"),
      buttons: Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).filter(t => t.length > 5)
    };
  });
  console.log("Check:", check);

  if (check.hasUsar) {
    console.log("Clicking Usar Esta Máquina");
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Usar Esta Máquina"));
      btn?.click();
    });
    await page.waitForTimeout(2000);

    const final = await page.evaluate(() => {
      return {
        url: window.location.href,
        bodyText: document.body.innerText.substring(1400, 1800)
      };
    });
    console.log("Final:", final);
  }

  console.log("DONE");
  await browser.close();
})();
