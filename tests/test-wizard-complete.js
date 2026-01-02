const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();

  try {
    console.log("=== 1. Login ===");
    await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(5000);

    console.log("URL:", page.url());

    // Fechar onboarding se estiver aberto
    const hasOnboarding = await page.evaluate(() => {
      return document.body.innerText.includes("Pular") || document.body.innerText.includes("Bem-vindo");
    });

    if (hasOnboarding) {
      console.log("=== 2. Fechar Onboarding ===");
      try {
        await page.click("text=Pular", { timeout: 5000 });
        await page.waitForTimeout(1000);
      } catch (e) {
        console.log("Onboarding já fechado ou não encontrado");
      }
    }

    console.log("=== 3. Clicar em Guiado ===");
    await page.click("button", { hasText: "Guiado" });
    await page.waitForTimeout(1500);

    await page.screenshot({ path: "tests/tests/wizard-after-guiado.png" });

    // STEP 1 - Selecionar Região
    console.log("=== STEP 1: Selecionar Região ===");
    const step1Info = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        hasRegion: text.includes("Região"),
        hasEUA: text.includes("EUA"),
        hasProximo: text.includes("Próximo")
      };
    });
    console.log("Step 1:", step1Info);

    await page.click("button", { hasText: "EUA" });
    await page.waitForTimeout(500);
    await page.click("button", { hasText: "Próximo" });
    await page.waitForTimeout(1500);

    // STEP 2 - Hardware
    console.log("=== STEP 2: Hardware ===");
    const step2Info = await page.evaluate(() => {
      const text = document.body.innerText;
      const buttons = Array.from(document.querySelectorAll("button"));
      return {
        hasHardware: text.includes("Hardware") || text.includes("2/4"),
        tierButtons: buttons.filter(b => b.textContent.includes("Lento") || b.textContent.includes("Medio") || b.textContent.includes("Rapido") || b.textContent.includes("Ultra")).map(b => b.textContent.trim())
      };
    });
    console.log("Step 2:", step2Info);
    await page.screenshot({ path: "tests/tests/wizard-step2-debug2.png" });

    if (step2Info.tierButtons.length > 0) {
      console.log("Clicar tier:", step2Info.tierButtons[0]);
      await page.click("button", { hasText: new RegExp(step2Info.tierButtons[0].split(" ")[0]) });
      await page.waitForTimeout(500);
      await page.click("button", { hasText: "Próximo" });
      await page.waitForTimeout(1500);

      // STEP 3 - Estratégia
      console.log("=== STEP 3: Estratégia ===");
      await page.click("button", { hasText: "Próximo" });
      await page.waitForTimeout(1500);

      // STEP 4 - Provisionar
      console.log("=== STEP 4: Provisionar ===");
      const step4Info = await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll("button"));
        const provisionBtn = buttons.find(b => b.textContent.includes("Provisionar"));
        return {
          hasProvisionar: provisionBtn ? true : false,
          enabled: provisionBtn ? !provisionBtn.disabled : false
        };
      });
      console.log("Step 4:", step4Info);

      if (step4Info.enabled) {
        console.log("=== 5. CLICAR EM PROVISIONAR ===");
        await page.click("button:not([disabled])", { hasText: /Provisionar/i });
        await page.waitForTimeout(5000);

        await page.screenshot({ path: "tests/tests/wizard-after-provision.png" });

        const result = await page.evaluate(() => {
          const text = document.body.innerText;
          return {
            hasSuccess: text.includes("sucesso") || text.includes("Success"),
            hasCreated: text.includes("criada") || text.includes("created"),
            textPreview: text.substring(500, 1500)
          };
        });

        console.log("Resultado:", result);

        if (result.hasSuccess || result.hasCreated) {
          console.log("✅✅✅ RESERVA FUNCIONOU! ✅✅✅");
        } else {
          console.log("⚠️ Provisionamento em andamento");
        }
      } else {
        console.log("❌ Botão desabilitado");
      }
    } else {
      console.log("❌ Nenhum tier encontrado");
    }

  } catch (error) {
    console.error("Erro:", error.message);
  } finally {
    await browser.close();
  }
})();
