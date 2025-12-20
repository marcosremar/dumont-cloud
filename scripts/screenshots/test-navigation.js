const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173'
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots/navigation-test')

// Testes de navegação
const navigationTests = []

async function testNavigation() {
  // Criar diretório
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true })
  }

  console.log('=' .repeat(60))
  console.log('  TESTE DE NAVEGAÇÃO - Playwright')
  console.log('=' .repeat(60))
  console.log(`\n  Base URL: ${BASE_URL}`)
  console.log(`  Output: ${OUTPUT_DIR}\n`)

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  })
  const page = await context.newPage()

  // Capturar erros de console
  const consoleErrors = []
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text())
    }
  })

  try {
    // 1. Ir para o Dashboard inicial
    console.log('\n📍 Navegando para Dashboard inicial...')
    await page.goto(`${BASE_URL}/demo-app`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(2000)

    let currentUrl = page.url()
    console.log(`   URL atual: ${currentUrl}`)
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01-dashboard-inicial.png') })

    // 2. Testar clique no menu Analytics para expandir
    console.log('\n📍 Clicando em Analytics para expandir...')
    const analyticsMenu = await page.$('text=Analytics')
    if (analyticsMenu) {
      await analyticsMenu.click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(OUTPUT_DIR, '02-analytics-expandido.png') })
      console.log('   ✅ Menu Analytics expandido')
    } else {
      console.log('   ❌ Menu Analytics não encontrado')
    }

    // 3. Testar navegação para Economia
    console.log('\n📍 Clicando em Economia...')
    await testMenuClick(page, 'Economia', '/demo-app/savings', '03-economia')

    // 4. Testar navegação para Métricas
    console.log('\n📍 Clicando em Métricas...')
    // Primeiro expandir Analytics novamente se necessário
    const analyticsMenu2 = await page.$('text=Analytics')
    if (analyticsMenu2) {
      await analyticsMenu2.click()
      await page.waitForTimeout(300)
    }
    await testMenuClick(page, 'Métricas', '/demo-app/metrics', '04-metricas')

    // 5. Testar navegação para AI Advisor
    console.log('\n📍 Clicando em AI Advisor...')
    const analyticsMenu3 = await page.$('text=Analytics')
    if (analyticsMenu3) {
      await analyticsMenu3.click()
      await page.waitForTimeout(300)
    }
    await testMenuClick(page, 'AI Advisor', '/demo-app/advisor', '05-advisor')

    // 6. Testar navegação para Dashboard
    console.log('\n📍 Clicando em Dashboard...')
    await testMenuClick(page, 'Dashboard', '/demo-app', '06-dashboard')

    // 7. Testar navegação para Machines
    console.log('\n📍 Clicando em Machines...')
    await testMenuClick(page, 'Machines', '/demo-app/machines', '07-machines')

    // 8. Testar navegação para Fine-Tuning
    console.log('\n📍 Clicando em Fine-Tuning...')
    await testMenuClick(page, 'Fine-Tuning', '/demo-app/finetune', '08-finetune')

    // 9. Testar navegação para Settings
    console.log('\n📍 Clicando em Settings...')
    await testMenuClick(page, 'Settings', '/demo-app/settings', '09-settings')

  } catch (error) {
    console.error('\n💥 Erro durante teste:', error.message)
  }

  await browser.close()

  // Relatório final
  printReport()

  async function testMenuClick(page, menuText, expectedPath, screenshotName) {
    const result = {
      menu: menuText,
      expectedPath,
      actualPath: null,
      success: false,
      error: null
    }

    try {
      // Tentar encontrar o link do menu
      const menuLink = await page.$(`a:has-text("${menuText}"), button:has-text("${menuText}")`)

      if (!menuLink) {
        // Tentar com seletor mais genérico
        const allLinks = await page.$$('a, button')
        for (const link of allLinks) {
          const text = await link.textContent()
          if (text && text.trim().toLowerCase().includes(menuText.toLowerCase())) {
            await link.click()
            await page.waitForTimeout(1500)
            break
          }
        }
      } else {
        await menuLink.click()
        await page.waitForTimeout(1500)
      }

      // Verificar URL
      const currentUrl = page.url()
      result.actualPath = currentUrl.replace(BASE_URL, '')

      // Verificar se navegou corretamente
      if (currentUrl.includes(expectedPath) || result.actualPath === expectedPath) {
        result.success = true
        console.log(`   ✅ Navegou para: ${currentUrl}`)
      } else {
        result.success = false
        result.error = `Esperado ${expectedPath}, mas foi para ${result.actualPath}`
        console.log(`   ❌ ERRO: Esperado ${expectedPath}`)
        console.log(`   ❌ Atual: ${result.actualPath}`)
      }

      await page.screenshot({ path: path.join(OUTPUT_DIR, `${screenshotName}.png`) })

    } catch (err) {
      result.error = err.message
      console.log(`   ❌ Erro: ${err.message}`)
    }

    navigationTests.push(result)
    return result
  }
}

function printReport() {
  console.log('\n' + '='.repeat(60))
  console.log('  RELATÓRIO DE NAVEGAÇÃO')
  console.log('='.repeat(60))

  const passed = navigationTests.filter(t => t.success).length
  const failed = navigationTests.filter(t => !t.success).length

  console.log(`
  ✅ Passou: ${passed}
  ❌ Falhou: ${failed}
  Total: ${navigationTests.length}
  `)

  if (failed > 0) {
    console.log('  FALHAS ENCONTRADAS:')
    console.log('  ' + '─'.repeat(40))
    navigationTests.filter(t => !t.success).forEach(t => {
      console.log(`\n  ❌ ${t.menu}`)
      console.log(`     Esperado: ${t.expectedPath}`)
      console.log(`     Atual: ${t.actualPath}`)
      if (t.error) console.log(`     Erro: ${t.error}`)
    })
  }

  console.log('\n  SUCESSOS:')
  console.log('  ' + '─'.repeat(40))
  navigationTests.filter(t => t.success).forEach(t => {
    console.log(`  ✅ ${t.menu} → ${t.actualPath}`)
  })

  // Salvar relatório JSON
  const reportPath = path.join(OUTPUT_DIR, 'navigation-report.json')
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    passed,
    failed,
    tests: navigationTests
  }, null, 2))

  console.log(`\n  Relatório salvo em: ${reportPath}`)
  console.log('  Screenshots salvos em: ' + OUTPUT_DIR)
  console.log('\n' + '='.repeat(60))
}

testNavigation().catch(console.error)
