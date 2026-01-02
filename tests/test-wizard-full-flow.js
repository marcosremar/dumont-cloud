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
  console.log("=== STEP 1 - SELECTING REGION ===");
  await page.click("button[data-testid=\"region-eua\"]");
  await page.waitForTimeout(500);

  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    btn?.click();
  });
  await page.waitForTimeout(1500);

  // Step 2: Select a tier
  console.log("=== STEP 2 - SELECTING TIER ===");
  const step2Check = await page.evaluate(() => {
    return {
      hasOQue: document.body.innerText.includes("O que"),
      hasDesenvolver: document.body.innerText.includes("Desenvolver")
    };
  });
  console.log("Step 2 check:", step2Check);

  // Select "Desenvolver" (Medio tier)
  await page.click("button:has-text(\"Desenvolver\")");
  await page.waitForTimeout(500);

  // Wait for machines to load
  await page.waitForTimeout(1500);

  // Check if machines loaded
  const machinesCheck = await page.evaluate(() => {
    return {
      hasRecomendadas: document.body.innerText.includes("recomendadas") || document.body.innerText.includes("GPU"),
      anyMachineCards: document.body.innerText.includes("RTX") || document.body.innerText.includes("A100")
    };
  });
  console.log("Machines loaded:", machinesCheck);

  // Click Próximo to go to Step 3
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    if (btn) {
      console.log("Clicking Próximo button");
      btn.click();
    } else {
      console.log("Próximo button not found or disabled!");
    }
  });
  await page.waitForTimeout(1500);

  // Step 3: Check content
  console.log("=== STEP 3 - STRATEGY ===");
  const step3Content = await page.evaluate(() => {
    return {
      hasStrategy: document.body.innerText.includes("Estratégia") || document.body.innerText.includes("Strategy"),
      hasFailover: document.body.innerText.includes("Failover"),
      hasRace: document.body.innerText.includes("Race") || document.body.innerText.includes("Corrida"),
      hasColdstart: document.body.innerText.includes("Coldstart"),
      allButtons: Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim().substring(0, 40)).filter(t => t.length > 0)
    };
  });
  console.log("Step 3 content:", step3Content);

  // Select a strategy (look for Race or Coldstart)
  const strategySelected = await page.evaluate(() => {
    const allButtons = Array.from(document.querySelectorAll("button"));
    const raceBtn = allButtons.find(b => b.textContent.includes("Race") || b.textContent.includes("Corrida"));
    const coldstartBtn = allButtons.find(b => b.textContent.includes("Coldstart"));

    if (raceBtn && !raceBtn.disabled) {
      raceBtn.click();
      return "Race";
    } else if (coldstartBtn && !coldstartBtn.disabled) {
      coldstartBtn.click();
      return "Coldstart";
    }
    return "none";
  });
  console.log("Strategy selected:", strategySelected);

  await page.waitForTimeout(500);

  // Click Iniciar to start provisioning
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Iniciar") && !b.disabled);
    if (btn) {
      console.log("Clicking Iniciar button");
      btn.click();
    } else {
      console.log("Iniciar button not found or disabled!");
    }
  });
  await page.waitForTimeout(2000);

  // Step 4: Provisioning
  console.log("=== STEP 4 - PROVISIONING ===");
  const step4Content = await page.evaluate(() => {
    return {
      bodyText: document.body.innerText.substring(1500, 2000),
      hasRound: document.body.innerText.includes("Round") || document.body.innerText.includes("Rodada"),
      hasConectando: document.body.innerText.includes("Conectando"),
      allButtons: Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim().substring(0, 30)).filter(t => t.length > 0)
    };
  });
  console.log("Step 4 content:", step4Content);

  console.log("\n=== TEST COMPLETE ===");
  await browser.close();
})();
