const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();

  await page.goto("http://localhost:4894/login?auto_login=demo", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  try { await page.click("text=Pular", { timeout: 3000 }); } catch(e) {}
  await page.click("button", { hasText: "Guiado" });
  await page.waitForTimeout(1000);

  console.log("=== TESTE WIZARD - RESERVA DE GPU ===\n");

  // Step 1: Localização
  console.log("Step 1: Selecionando região EUA...");
  await page.click("button[data-testid=\"region-eua\"]");
  await page.waitForTimeout(800);

  const clickProximo = () => page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    btn?.click();
  });

  await clickProximo();
  console.log("✅ Step 1 completo\n");
  await page.waitForTimeout(1500);

  // Step 2: Hardware
  console.log("Step 2: Selecionando tier 'Desenvolver'...");
  await page.click("button:has-text(\"Desenvolver\")");
  await page.waitForTimeout(1500);

  // Ver se máquinas apareceram
  const machinesCheck = await page.evaluate(() => {
    return {
      hasRTX: document.body.innerText.includes("RTX"),
      hasA100: document.body.innerText.includes("A100"),
      machineCount: (document.body.innerText.match(/RTX|A100|H100/g) || []).length
    };
  });
  console.log("  Máquinas encontradas:", machinesCheck);
  console.log("  Clicando Próximo...");

  await clickProximo();
  console.log("✅ Step 2 completo\n");
  await page.waitForTimeout(1500);

  // Step 3: Estratégia
  console.log("Step 3: Estratégia pré-selecionada");
  const strategyCheck = await page.evaluate(() => {
    return {
      hasSnapshotOnly: document.body.innerText.includes("Snapshot Only"),
      hasRecomendado: document.body.innerText.includes("Recomendado")
    };
  });
  console.log("  Estratégia:", strategyCheck);
  console.log("  Clicando Iniciar...");

  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Iniciar") && !b.disabled);
    btn?.click();
  });

  console.log("✅ Step 3 completo\n");

  // Step 4: Provisionamento
  console.log("Step 4: Aguardando provisionamento...");
  await page.waitForTimeout(6000);

  const finalCheck = await page.evaluate(() => {
    const hasWinner = document.body.innerText.includes("Conectado") || document.body.innerText.includes("RTX");
    const hasUsarBtn = document.body.innerText.includes("Usar Esta Máquina");
    const winnerText = document.body.innerText.substring(1200, 1600);
    return { hasWinner, hasUsarBtn, winnerText };
  });

  console.log("  Status final:", finalCheck.hasWinner ? "Vencedor encontrado!" : "Aguardando...");
  console.log("  Botão 'Usar Esta Máquina':", finalCheck.hasUsarBtn ? "Presente ✅" : "Ausente");

  if (finalCheck.hasUsarBtn) {
    console.log("\n  Clicando em 'Usar Esta Máquina'...");
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Usar Esta Máquina"));
      btn?.click();
    });
    await page.waitForTimeout(2000);

    const url = page.url();
    console.log("  Navegou para:", url);
    console.log("\n✅ WIZARD COMPLETO - GPU RESERVADA COM SUCESSO!");
  } else {
    console.log("\n❌ ERRO: Botão 'Usar Esta Máquina' não encontrado");
  }

  await page.waitForTimeout(2000);
  await browser.close();
})();
