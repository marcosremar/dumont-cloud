const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();

  try {
    // Login
    console.log("1. Login...");
    await page.goto("http://localhost:4892/login?auto_login=demo", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(4000);

    // Verificar se está no /app
    console.log("URL:", page.url());

    // Verificar botões
    const buttons = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll("button"));
      return btns
        .filter(b => b.offsetParent !== null)
        .map(b => b.textContent.trim())
        .slice(0, 10);
    });

    console.log("Botões visíveis:", buttons);

    if (buttons.includes("Guiado")) {
      console.log("2. Clicar em Guiado...");
      await page.click("text=Guiado");
      await page.waitForTimeout(2000);

      // Screenshot
      await page.screenshot({ path: "tests/tests/after-guiado.png" });

      // Verificar Step 1
      const step1 = await page.evaluate(() => {
        return {
          hasRegion: document.body.innerText.includes("Região"),
          hasEUA: document.body.innerText.includes("EUA"),
          text: document.body.innerText.substring(400, 800)
        };
      });

      console.log("Step 1:", step1.hasRegion ? "OK" : "NOK");

      if (step1.hasEUA) {
        console.log("3. Selecionar EUA...");
        await page.click("text=EUA");
        await page.waitForTimeout(500);

        console.log("4. Clicar Próximo...");
        await page.click("text=Próximo");
        await page.waitForTimeout(2000);

        await page.screenshot({ path: "tests/tests/step2-after.png" });

        const step2 = await page.evaluate(() => {
          const text = document.body.innerText;
          return {
            hasHardware: text.includes("Hardware"),
            has2of4: text.includes("2/4"),
            hasButtons: document.querySelectorAll("button").length > 0,
            text: text.substring(600, 1200)
          };
        });

        console.log("Step 2:", step2);

        if (step2.hasHardware && step2.has2of4) {
          console.log("✅ Step 2 carregou!");
        } else {
          console.log("❌ Step 2 não carregou corretamente");
        }
      }
    } else {
      console.log("❌ Botão Guiado não encontrado");
    }

  } catch (error) {
    console.error("Erro:", error.message);
  } finally {
    await browser.close();
  }
})();
