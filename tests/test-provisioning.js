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

  await page.click("button[data-testid=\"region-eua\"]");
  await page.waitForTimeout(500);

  // Helper function to click Próximo
  const clickProximo = () => page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo") && !b.disabled);
    btn?.click();
  });

  await clickProximo();
  await page.waitForTimeout(1500);

  await page.click("button:has-text(\"Desenvolver\")");
  await page.waitForTimeout(1500);

  await clickProximo();
  await page.waitForTimeout(1500);

  // Check what strategy is selected by default
  const step3Details = await page.evaluate(() => {
    const wizardSection = document.getElementById("wizard-form-section");
    if (!wizardSection) return { error: "no wizard section" };

    const buttons = Array.from(wizardSection.querySelectorAll("button")).map(b => ({
      text: b.textContent.trim().substring(0, 50),
      hasBrandClass: b.className.includes("bg-brand-500") || b.className.includes("border-brand-500")
    }));

    return {
      selectedButtons: buttons.filter(b => b.hasBrandClass),
      hasRecomendado: document.body.innerText.includes("Recomendado"),
      allButtons: buttons.map(b => b.text)
    };
  });
  console.log("Step 3 default selection:", step3Details);

  // Click Iniciar
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Iniciar") && !b.disabled);
    if (btn) btn.click();
  });

  // Wait for provisioning
  console.log("Waiting for provisioning...");
  await page.waitForTimeout(5000);

  const step4Details = await page.evaluate(() => {
    const wizardSection = document.getElementById("wizard-form-section");
    if (!wizardSection) return { error: "no wizard section" };

    return {
      bodyText: document.body.innerText.substring(1200, 2000),
      hasCandidate: document.body.innerText.includes("Candidato") || document.body.innerText.includes("vencedor") || document.body.innerText.includes("winner"),
      hasUsar: document.body.innerText.includes("Usar Esta Máquina"),
      hasBuscarOutras: document.body.innerText.includes("Buscar Outras"),
      buttons: Array.from(wizardSection.querySelectorAll("button")).map(b => b.textContent.trim().substring(0, 40))
    };
  });
  console.log("Step 4 after 5s:", step4Details);

  // Wait a bit more
  await page.waitForTimeout(5000);

  const step4Final = await page.evaluate(() => {
    return {
      hasUsar: document.body.innerText.includes("Usar Esta Máquina"),
      hasCancelar: document.body.innerText.includes("Cancelar") && !document.body.innerText.includes("Buscar Outras"),
      hasBuscarOutras: document.body.innerText.includes("Buscar Outras"),
      buttonsText: Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).filter(t => t.length > 5)
    };
  });
  console.log("Step 4 final:", step4Final);

  await browser.close();
})();
