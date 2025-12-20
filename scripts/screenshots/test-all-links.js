const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173'
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots/link-test')

const results = {
  tested: [],
  broken: [],
  working: []
}

async function testAllLinks() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true })
  }

  console.log('=' .repeat(60))
  console.log('  TESTE DE TODOS OS LINKS - Playwright')
  console.log('=' .repeat(60))

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } })

  // Páginas para testar os links internos
  const pagesToTest = [
    { name: 'Metrics Hub', path: '/demo-app/metrics-hub' },
    { name: 'GPU Metrics', path: '/demo-app/metrics' },
    { name: 'Dashboard', path: '/demo-app' },
  ]

  for (const pageInfo of pagesToTest) {
    console.log(`\n${'═'.repeat(50)}`)
    console.log(`  Testando links em: ${pageInfo.name}`)
    console.log(`  URL: ${BASE_URL}${pageInfo.path}`)
    console.log('═'.repeat(50))

    const page = await context.newPage()

    try {
      await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle', timeout: 30000 })
      await page.waitForTimeout(2000)

      // Screenshot inicial
      await page.screenshot({
        path: path.join(OUTPUT_DIR, `${pageInfo.name.toLowerCase().replace(/\s+/g, '-')}-inicial.png`),
        fullPage: true
      })

      // Encontrar todos os links e botões clicáveis
      const clickableElements = await page.$$('a[href], button, [role="button"], [onclick]')
      console.log(`\n  Encontrados ${clickableElements.length} elementos clicáveis`)

      // Coletar informações dos links
      const links = []
      for (const el of clickableElements) {
        try {
          const href = await el.getAttribute('href')
          const text = await el.textContent()
          const tagName = await el.evaluate(e => e.tagName.toLowerCase())
          const isVisible = await el.isVisible()

          if (href && href.startsWith('/') && !href.includes('#') && isVisible) {
            links.push({
              href,
              text: text?.trim().substring(0, 50) || '[sem texto]',
              tagName,
              element: el
            })
          }
        } catch (e) {
          // Ignorar elementos que não podem ser lidos
        }
      }

      // Remover duplicatas
      const uniqueLinks = links.filter((link, index, self) =>
        index === self.findIndex(l => l.href === link.href)
      )

      console.log(`  Links internos únicos: ${uniqueLinks.length}`)

      // Testar cada link
      for (const link of uniqueLinks) {
        console.log(`\n  → Testando: ${link.text}`)
        console.log(`    Href: ${link.href}`)

        const testResult = {
          page: pageInfo.name,
          linkText: link.text,
          href: link.href,
          success: false,
          finalUrl: null,
          error: null
        }

        try {
          // Navegar diretamente para o href
          const response = await page.goto(`${BASE_URL}${link.href}`, {
            waitUntil: 'networkidle',
            timeout: 15000
          })

          await page.waitForTimeout(1500)

          const finalUrl = page.url()
          testResult.finalUrl = finalUrl.replace(BASE_URL, '')

          // Verificar se chegou no destino correto
          if (finalUrl.includes(link.href) || testResult.finalUrl === link.href) {
            testResult.success = true
            console.log(`    ✅ OK - Navegou para: ${testResult.finalUrl}`)
            results.working.push(testResult)
          } else {
            testResult.success = false
            testResult.error = `Redirecionou para ${testResult.finalUrl}`
            console.log(`    ❌ ERRO - Redirecionou para: ${testResult.finalUrl}`)
            results.broken.push(testResult)

            // Screenshot do erro
            await page.screenshot({
              path: path.join(OUTPUT_DIR, `broken-${link.href.replace(/\//g, '_')}.png`),
              fullPage: true
            })
          }

          // Verificar se há erros na página
          const pageContent = await page.textContent('body')
          if (pageContent.includes('404') || pageContent.includes('não encontrada') || pageContent.includes('Error')) {
            testResult.success = false
            testResult.error = 'Página com erro ou 404'
            console.log(`    ⚠️  Página pode ter erro`)
          }

        } catch (err) {
          testResult.error = err.message
          console.log(`    ❌ ERRO: ${err.message.substring(0, 100)}`)
          results.broken.push(testResult)
        }

        results.tested.push(testResult)

        // Voltar para a página original
        await page.goto(`${BASE_URL}${pageInfo.path}`, { waitUntil: 'networkidle', timeout: 15000 })
        await page.waitForTimeout(500)
      }

    } catch (err) {
      console.log(`  ❌ Erro ao testar página: ${err.message}`)
    }

    await page.close()
  }

  await browser.close()

  // Relatório final
  printReport()
}

function printReport() {
  console.log('\n' + '═'.repeat(60))
  console.log('  RELATÓRIO FINAL DE LINKS')
  console.log('═'.repeat(60))

  console.log(`
  Total testados: ${results.tested.length}
  ✅ Funcionando: ${results.working.length}
  ❌ Quebrados: ${results.broken.length}
  `)

  if (results.broken.length > 0) {
    console.log('\n  🔴 LINKS QUEBRADOS:')
    console.log('  ' + '─'.repeat(45))
    results.broken.forEach(r => {
      console.log(`\n  ❌ "${r.linkText}"`)
      console.log(`     Página: ${r.page}`)
      console.log(`     Href: ${r.href}`)
      console.log(`     Destino real: ${r.finalUrl || 'N/A'}`)
      console.log(`     Erro: ${r.error || 'Redirecionamento inesperado'}`)
    })
  }

  if (results.working.length > 0) {
    console.log('\n  🟢 LINKS FUNCIONANDO:')
    console.log('  ' + '─'.repeat(45))
    results.working.forEach(r => {
      console.log(`  ✅ ${r.linkText} → ${r.href}`)
    })
  }

  // Salvar relatório
  const reportPath = path.join(OUTPUT_DIR, 'link-report.json')
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: {
      total: results.tested.length,
      working: results.working.length,
      broken: results.broken.length
    },
    broken: results.broken,
    working: results.working
  }, null, 2))

  console.log(`\n  Relatório salvo em: ${reportPath}`)
  console.log('═'.repeat(60))
}

testAllLinks().catch(console.error)
