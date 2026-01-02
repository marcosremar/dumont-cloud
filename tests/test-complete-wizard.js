const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  page.on("console", msg => console.log("LOG:", msg.text()));

  await page.goto("http://localhost:4894/login?auto_login=demo", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  try { await page.click("text=Pular", { timeout: 3000 }); } catch(e) {}
  await page.click("button", { hasText: "Guiado" });
  await page.waitForTimeout(1000);

  // Step 1: Select EUA
  console.log("=== STEP 1: SELECTING REGION ===");
  await page.click("button[data-testid=\"region-eua\"]");
  await page.waitForTimeout(500);

  const clickProximo = () => page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    btn?.click();
  });

  await clickProximo();
  await page.waitForTimeout(1500);

  // Step 2: Select a tier
  console.log("=== STEP 2: SELECTING HARDWARE ===");
  await page.click("button:has-text(\"Desenvolver\")");
  await page.waitForTimeout(1500);

  await clickProximo();
  await page.waitForTimeout(1500);

  // Step 3: Strategy is pre-selected
  console.log("=== STEP 3: STRATEGY PRE-SELECTED ===");

  // Click Iniciar to start provisioning
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Iniciar") && !b.disabled);
    if (btn) btn.click();
  });

  // Wait for provisioning simulation to complete
  console.log("=== WAITING FOR PROVISIONING ===");
  await page.waitForTimeout(6000);

  // Check if winner was selected
  const step4Winner = await page.evaluate(() => {
    return {
      hasUsar: document.body.innerText.includes("Usar Esta Máquina"),
      hasBuscarOutras: document.body.innerText.includes("Buscar Outras"),
      hasConectado: document.body.innerText.includes("Conectado"),
      wizardContent: document.body.innerText.substring(1200, 1800)
    };
  });
  console.log("Step 4 with winner:", step4Winner);

  // Click "Usar Esta Máquina" to complete
  console.log("=== CLICKING USAR ESTA MÁQUINA ===");
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Usar Esta Máquina") && !b.disabled);
    if (btn) {
      console.log("Clicking Usar Esta Máquina");
      btn.click();
    } else {
      console.log("Usar Esta Máquina button not found!");
    }
  });

  await page.waitForTimeout(2000);

  // Check final state
  const finalState = await page.evaluate(() => {
    return {
      bodyText: document.body.innerText.substring(1400, 2000),
      hasSuccess: document.body.innerText.includes("sucesso") || document.body.innerText.includes("Success") || document.body.innerText.includes("Conectado"),
      hasMachines: document.body.innerText.includes("Máquinas") || document.body.innerText.includes("Machines"),
      url: window.location.href
    };
  });
  console.log("Final state:", finalState);

  console.log("\n=== WIZARD FLOW COMPLETE! ===");
  await browser.close();
})();
