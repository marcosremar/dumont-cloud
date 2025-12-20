const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173'
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots/audit')

// Todas as páginas de relatórios/analytics para auditar
const REPORT_PAGES = [
  // Analytics
  { path: '/demo-app/metrics-hub', name: 'Metrics Hub', category: 'Analytics' },
  { path: '/demo-app/metrics', name: 'GPU Metrics', category: 'Analytics' },
  { path: '/demo-app/savings', name: 'Savings Dashboard', category: 'Analytics' },
  { path: '/demo-app/advisor', name: 'GPU Advisor', category: 'Analytics' },

  // Reports
  { path: '/demo-app/failover-report', name: 'Failover Report', category: 'Reports' },
  { path: '/demo-app/finetune', name: 'Fine-Tuning', category: 'Reports' },

  // Main pages
  { path: '/demo-app', name: 'Dashboard', category: 'Main' },
  { path: '/demo-app/machines', name: 'Machines', category: 'Main' },
  { path: '/demo-app/settings', name: 'Settings', category: 'Main' },
]

// Resultados da auditoria
const auditResults = []

async function auditPage(browser, route) {
  const result = {
    name: route.name,
    path: route.path,
    category: route.category,
    status: 'unknown',
    issues: [],
    warnings: [],
    screenshot: null,
    loadTime: 0,
    consoleErrors: [],
    hasContent: false,
    redirected: false,
    finalUrl: null,
  }

  const page = await browser.newPage()
  await page.setViewportSize({ width: 1920, height: 1080 })

  // Capturar erros do console
  page.on('console', msg => {
    if (msg.type() === 'error') {
      result.consoleErrors.push(msg.text())
    }
  })

  // Capturar erros de página
  page.on('pageerror', error => {
    result.consoleErrors.push(error.message)
  })

  const startTime = Date.now()

  try {
    const url = `${BASE_URL}${route.path}`
    console.log(`\n  Navegando para: ${url}`)

    const response = await page.goto(url, {
      waitUntil: 'networkidle',
      timeout: 30000
    })

    result.loadTime = Date.now() - startTime
    result.finalUrl = page.url()

    // Verificar se houve redirecionamento
    if (!result.finalUrl.includes(route.path)) {
      result.redirected = true
      result.issues.push(`Redirecionou para: ${result.finalUrl}`)
    }

    // Verificar status HTTP
    if (response && response.status() >= 400) {
      result.issues.push(`HTTP Status: ${response.status()}`)
    }

    // Aguardar um pouco para conteúdo dinâmico
    await page.waitForTimeout(2000)

    // Verificar elementos de erro comuns
    const errorSelectors = [
      '[data-testid="error"]',
      '.error-message',
      '.error-state',
      'text=Erro',
      'text=Error',
      'text=404',
      'text=não encontrado',
      'text=not found',
    ]

    for (const selector of errorSelectors) {
      try {
        const errorElement = await page.$(selector)
        if (errorElement) {
          const text = await errorElement.textContent()
          if (text && text.length < 200) {
            result.warnings.push(`Possível erro encontrado: "${text.trim().substring(0, 100)}"`)
          }
        }
      } catch (e) {
        // Ignorar erros de seletor
      }
    }

    // Verificar se há conteúdo significativo
    const bodyText = await page.textContent('body')
    result.hasContent = bodyText && bodyText.length > 500

    if (!result.hasContent) {
      result.warnings.push('Página parece ter pouco conteúdo')
    }

    // Verificar elementos vazios/loading travados
    const loadingElements = await page.$$('.loading, .spinner, [data-loading="true"]')
    if (loadingElements.length > 0) {
      result.warnings.push(`${loadingElements.length} elemento(s) de loading ainda visíveis`)
    }

    // Verificar se tem sidebar (padrão TailAdmin)
    const hasSidebar = await page.$('aside, [class*="sidebar"], [class*="Sidebar"]')
    if (!hasSidebar && route.category !== 'Auth') {
      result.warnings.push('Sem sidebar TailAdmin detectado')
    }

    // Verificar cards/conteúdo principal
    const hasCards = await page.$$('[class*="card"], [class*="Card"], .ta-card')
    if (hasCards.length === 0 && route.category !== 'Auth') {
      result.warnings.push('Nenhum card detectado na página')
    }

    // Tirar screenshot
    const screenshotPath = path.join(OUTPUT_DIR, `${route.name.toLowerCase().replace(/\s+/g, '-')}.png`)
    await page.screenshot({ path: screenshotPath, fullPage: true })
    result.screenshot = screenshotPath

    // Determinar status final
    if (result.issues.length > 0) {
      result.status = 'broken'
    } else if (result.warnings.length > 0) {
      result.status = 'warning'
    } else {
      result.status = 'ok'
    }

    // Verificar se página está em branco ou só com loading
    const mainContent = await page.$('main, [role="main"], .main-content, #root > div > div')
    if (mainContent) {
      const mainText = await mainContent.textContent()
      if (!mainText || mainText.trim().length < 50) {
        result.status = 'broken'
        result.issues.push('Conteúdo principal vazio ou muito curto')
      }
    }

  } catch (error) {
    result.status = 'error'
    result.issues.push(`Erro ao carregar: ${error.message}`)
    result.loadTime = Date.now() - startTime
  }

  await page.close()
  return result
}

async function runAudit() {
  // Criar diretório de saída
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true })
  }

  console.log('=' .repeat(60))
  console.log('  AUDITORIA DE PÁGINAS DE RELATÓRIOS')
  console.log('=' .repeat(60))
  console.log(`\n  Base URL: ${BASE_URL}`)
  console.log(`  Total de páginas: ${REPORT_PAGES.length}`)
  console.log(`  Output: ${OUTPUT_DIR}\n`)

  const browser = await chromium.launch({ headless: true })

  for (const route of REPORT_PAGES) {
    console.log(`\n${'─'.repeat(50)}`)
    console.log(`  ${route.category} > ${route.name}`)

    const result = await auditPage(browser, route)
    auditResults.push(result)

    // Mostrar resultado imediato
    const statusIcon = {
      'ok': '✅',
      'warning': '⚠️',
      'broken': '❌',
      'error': '💥',
      'unknown': '❓'
    }[result.status]

    console.log(`  Status: ${statusIcon} ${result.status.toUpperCase()}`)
    console.log(`  Tempo de carga: ${result.loadTime}ms`)

    if (result.issues.length > 0) {
      console.log(`  Issues:`)
      result.issues.forEach(i => console.log(`    - ${i}`))
    }
    if (result.warnings.length > 0) {
      console.log(`  Warnings:`)
      result.warnings.forEach(w => console.log(`    - ${w}`))
    }
    if (result.consoleErrors.length > 0) {
      console.log(`  Console Errors: ${result.consoleErrors.length}`)
    }
  }

  await browser.close()

  // Gerar relatório final
  generateReport()
}

function generateReport() {
  console.log('\n' + '='.repeat(60))
  console.log('  RESUMO DA AUDITORIA')
  console.log('='.repeat(60))

  const stats = {
    ok: auditResults.filter(r => r.status === 'ok').length,
    warning: auditResults.filter(r => r.status === 'warning').length,
    broken: auditResults.filter(r => r.status === 'broken').length,
    error: auditResults.filter(r => r.status === 'error').length,
  }

  console.log(`
  ✅ OK:       ${stats.ok}
  ⚠️  Warnings: ${stats.warning}
  ❌ Broken:   ${stats.broken}
  💥 Error:    ${stats.error}
  `)

  // Listar páginas com problemas
  const problematic = auditResults.filter(r => r.status !== 'ok')

  if (problematic.length > 0) {
    console.log('\n  PÁGINAS COM PROBLEMAS:')
    console.log('  ' + '─'.repeat(40))

    problematic.forEach(r => {
      const icon = r.status === 'broken' ? '❌' : r.status === 'error' ? '💥' : '⚠️'
      console.log(`\n  ${icon} ${r.name} (${r.path})`)
      r.issues.forEach(i => console.log(`     Issue: ${i}`))
      r.warnings.forEach(w => console.log(`     Warning: ${w}`))
    })
  }

  // Páginas OK
  const okPages = auditResults.filter(r => r.status === 'ok')
  if (okPages.length > 0) {
    console.log('\n  PÁGINAS OK:')
    console.log('  ' + '─'.repeat(40))
    okPages.forEach(r => {
      console.log(`  ✅ ${r.name} (${r.loadTime}ms)`)
    })
  }

  // Salvar relatório JSON
  const reportPath = path.join(OUTPUT_DIR, 'audit-report.json')
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    stats,
    results: auditResults
  }, null, 2))

  console.log(`\n  Relatório salvo em: ${reportPath}`)
  console.log('  Screenshots salvos em: ' + OUTPUT_DIR)
  console.log('\n' + '='.repeat(60))

  // Recomendações
  console.log('\n  RECOMENDAÇÕES:')
  console.log('  ' + '─'.repeat(40))

  const redirected = auditResults.filter(r => r.redirected)
  if (redirected.length > 0) {
    console.log(`\n  🔄 ${redirected.length} página(s) redirecionando:`)
    redirected.forEach(r => console.log(`     - ${r.name}: ${r.path} -> ${r.finalUrl}`))
  }

  const noSidebar = auditResults.filter(r =>
    r.warnings.some(w => w.includes('sidebar'))
  )
  if (noSidebar.length > 0) {
    console.log(`\n  📐 ${noSidebar.length} página(s) sem sidebar TailAdmin:`)
    noSidebar.forEach(r => console.log(`     - ${r.name}`))
  }

  const slowPages = auditResults.filter(r => r.loadTime > 5000)
  if (slowPages.length > 0) {
    console.log(`\n  🐢 ${slowPages.length} página(s) lentas (>5s):`)
    slowPages.forEach(r => console.log(`     - ${r.name}: ${r.loadTime}ms`))
  }

  console.log('\n')
}

// Executar
runAudit().catch(console.error)
