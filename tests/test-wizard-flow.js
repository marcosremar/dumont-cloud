const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 400 });
  const page = await browser.newPage();

  try {
    console.log("=== 1. Login ===");
    await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "networkidle" });
    await page.waitForTimeout(3000);

    console.log("=== 2. Abrir Wizard (Guiado) ===");
    await page.click("button", { hasText: "Guiado" });
    await page.waitForTimeout(2000);

    // STEP 1 - Selecionar Região
    console.log("=== STEP 1: Selecionar Região ===");
    const step1Before = await page.evaluate(() => {
      const bodyText = document.body.innerText;
      return {
        hasEUA: bodyText.includes("EUA"),
        hasEuropa: bodyText.includes("Europa")
      };
    });
    console.log("Step 1 options:", step1Before);

    // Clicar em EUA para selecionar
    await page.click("button", { hasText: "EUA" });
    await page.waitForTimeout(500);

    // Clicar Próximo
    await page.click("button", { hasText: "Próximo" });
    await page.waitForTimeout(2000);

    // STEP 2 - Selecionar Hardware/GPU
    console.log("=== STEP 2: Selecionar Hardware ===");
    const step2Info = await page.evaluate(() => {
      const bodyText = document.body.innerText;
      const buttons = Array.from(document.querySelectorAll("button"));
      return {
        hasHardware: bodyText.includes("Hardware") || bodyText.includes("2/4"),
        hasRTX: bodyText.includes("RTX"),
        hasH100: bodyText.includes("H100"),
        hasA100: bodyText.includes("A100"),
        tierButtons: buttons.filter(b => {
          const text = b.textContent;
          return text && (text.includes("RTX") || text.includes("H100") || text.includes("A100") || text.includes("Tier"));
        }).map(b => b.textContent.trim()),
        bodyPreview: bodyText.substring(500, 2000)
      };
    });

    console.log("Step 2 info:", JSON.stringify(step2Info, null, 2));
    await page.screenshot({ path: "tests/tests/wizard-step2-debug.png", fullPage: true });

    if (step2Info.tierButtons.length > 0) {
      console.log("Found tier buttons:", step2Info.tierButtons);

      // Clicar no primeiro tier disponível
      const firstTier = step2Info.tierButtons[0];
      console.log("Clicking tier:", firstTier);
      await page.click("button", { hasText: new RegExp(firstTier.split(" ")[0]) });
      await page.waitForTimeout(500);

      // Clicar Próximo
      await page.click("button", { hasText: "Próximo" });
      await page.waitForTimeout(1500);

      // STEP 3 - Estratégia
      console.log("=== STEP 3: Estratégia ===");
      const step3Info = await page.evaluate(() => {
        const bodyText = document.body.innerText;
        return {
          hasStrategy: bodyText.includes("Estratégia") || bodyText.includes("3/4"),
          hasFailover: bodyText.includes("Failover")
        };
      });

      console.log("Step 3 info:", step3Info);
      await page.screenshot({ path: "tests/tests/wizard-step3-debug.png", fullPage: true });

      // Clicar Próximo
      await page.click("button", { hasText: "Próximo" });
      await page.waitForTimeout(1500);

      // STEP 4 - Provisionar
      console.log("=== STEP 4: Provisionar ===");
      const step4Info = await page.evaluate(() => {
        const bodyText = document.body.innerText;
        const buttons = Array.from(document.querySelectorAll("button"));
        const provisionBtn = buttons.find(b => b.textContent.includes("Provisionar"));
        return {
          hasProvisionar: bodyText.includes("Provisionar") || bodyText.includes("4/4"),
          provisionButtonEnabled: provisionBtn ? !provisionBtn.disabled : false,
          buttons: buttons.slice(0, 20).map(b => ({
            text: b.textContent.trim(),
            disabled: b.disabled
          }))
        };
      });

      console.log("Step 4 info:", JSON.stringify(step4Info, null, 2));
      await page.screenshot({ path: "tests/tests/wizard-step4-debug.png", fullPage: true });

      if (step4Info.provisionButtonEnabled) {
        console.log("=== 6. CLICAR EM PROVISIONAR ===");
        await page.click("button:not([disabled])", { hasText: /Provisionar/i });
        await page.waitForTimeout(5000);

        const result = await page.evaluate(() => {
          const bodyText = document.body.innerText;
          return {
            hasSuccess: bodyText.includes("sucesso") || bodyText.includes("Success"),
            hasCreated: bodyText.includes("criada") || bodyText.includes("created"),
            hasMachine: bodyText.includes("máquina") || bodyText.includes("GPU"),
            hasWinner: bodyText.includes("vencedor") || bodyText.includes("winner"),
            bodyPreview: bodyText.substring(500, 2000)
          };
        });

        console.log("Resultado Final:", JSON.stringify(result, null, 2));
        await page.screenshot({ path: "tests/tests/wizard-result-final.png", fullPage: true });

        if (result.hasSuccess || result.hasCreated || result.hasWinner) {
          console.log("✅✅✅ RESERVA FUNCIONOU! ✅✅✅");
        } else {
          console.log("⚠️ Provisionamento iniciado");
        }
      } else {
        console.log("❌ Botão Provisionar está DISABLED");
        console.log("Verifique as validações:");
        console.log("- selectedLocation:", await page.evaluate(() => window.selectedLocation));
        console.log("- selectedTier:", await page.evaluate(() => window.selectedTier));
      }
    } else {
      console.log("❌ Nenhum botão de tier encontrado no Step 2");
    }

  } catch (error) {
    console.error("Test error:", error.message);
    console.error(error.stack);
  } finally {
    await browser.close();
  }
})();
