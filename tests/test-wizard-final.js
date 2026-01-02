const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 400 });
  const page = await browser.newPage();

  try {
    console.log("=== 1. Login ===");
    await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(4000);

    // Pular onboarding
    try { await page.click("text=Pular", { timeout: 3000 }); } catch(e) {}
    await page.waitForTimeout(500);

    console.log("=== 2. Abrir Wizard Guiado ===");
    await page.click("button", { hasText: "Guiado" });
    await page.waitForTimeout(1000);

    // STEP 1
    console.log("=== STEP 1: Selecionar Região ===");
    await page.click('button[data-testid="region-eua"]');
    await page.waitForTimeout(300);

    const proximoDisabled = await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Próximo"));
      return btn ? btn.disabled : true;
    });

    console.log("Botão Próximo disabled?", proximoDisabled);

    if (!proximoDisabled) {
      console.log("=== Clicar Próximo (Step 1 -> 2) ===");
      await page.click("button", { hasText: "Próximo" });
      await page.waitForTimeout(1500);

      const step2Info = await page.evaluate(() => {
        const text = document.body.innerText;
        return {
          hasHardware: text.includes("Hardware") || text.includes("2/4"),
          hasTier: text.includes("Lento") || text.includes("Medio") || text.includes("Rapido"),
          bodyPreview: text.substring(700, 1300)
        };
      });

      console.log("Step 2:", step2Info);

      if (step2Info.hasHardware) {
        // Procurar botões de tier
        const tierButtons = await page.evaluate(() => {
          const buttons = Array.from(document.querySelectorAll("button"));
          return buttons
            .filter(b => {
              const text = b.textContent;
              return (text.includes("Experimentar") || text.includes("Desenvolver") ||
                      text.includes("Treinar") || text.includes("Produção") || text.includes("Lento")) &&
                     !b.disabled;
            })
            .map(b => ({ text: b.textContent.trim(), class: b.className }));
        });

        console.log("Tier buttons encontrados:", tierButtons.length);

        if (tierButtons.length > 0) {
          console.log("Clicar em:", tierButtons[0].text.substring(0, 20));
          await page.click("button", { hasText: /Experimentar|Lento/i });
          await page.waitForTimeout(500);

          // Clicar Próximo
          await page.click("button", { hasText: "Próximo" });
          await page.waitForTimeout(1500);

          // STEP 3
          console.log("=== STEP 3: Estratégia ===");
          await page.click("button", { hasText: "Próximo" });
          await page.waitForTimeout(1500);

          // STEP 4
          console.log("=== STEP 4: Provisionar ===");
          const provisionBtn = await page.evaluate(() => {
            const btn = Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Provisionar"));
            return btn ? { text: btn.textContent, disabled: btn.disabled } : null;
          });

          console.log("Botão Provisionar:", provisionBtn);

          if (provisionBtn && !provisionBtn.disabled) {
            console.log("=== CLICAR EM PROVISIONAR ===");
            await page.click("button:not([disabled])", { hasText: /Provisionar/i });
            await page.waitForTimeout(5000);

            await page.screenshot({ path: "tests/tests/final-result.png" });

            const result = await page.evaluate(() => {
              const text = document.body.innerText;
              return {
                hasSuccess: text.includes("sucesso") || text.includes("Success"),
                hasCreated: text.includes("criada"),
                textPreview: text.substring(500, 1500)
              };
            });

            console.log("Resultado:", result);

            if (result.hasSuccess || result.hasCreated) {
              console.log("✅✅✅ RESERVA FUNCIONOU! ✅✅✅");
            }
          } else {
            console.log("❌ Botão Provisionar desabilitado");
          }
        }
      }
    }

  } catch (error) {
    console.error("Erro:", error.message);
  } finally {
    await browser.close();
  }
})();
