const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173'
const OUTPUT_DIR = path.join(__dirname, '../../artifacts/screenshots/analytics')

const analyticsRoutes = [
  { path: '/demo-app/metrics-hub', name: 'metrics-hub' },
  { path: '/demo-app/metrics', name: 'gpu-metrics' },
  { path: '/demo-app/savings', name: 'savings' },
  { path: '/demo-app/advisor', name: 'advisor' },
  { path: '/demo-app/failover-report', name: 'failover-report' },
  { path: '/demo-app/finetune', name: 'finetune' },
]

async function captureAnalytics() {
  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true })
  }

  const browser = await chromium.launch({ headless: true })

  console.log('📸 Capturando screenshots das páginas de Analytics...\n')

  for (const route of analyticsRoutes) {
    const page = await browser.newPage()
    await page.setViewportSize({ width: 1920, height: 1080 })

    const url = `${BASE_URL}${route.path}`
    console.log(`━━━ ${route.name} ━━━`)
    console.log(`   URL: ${url}`)

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 })
      await page.waitForTimeout(2000) // Wait for animations

      // Capture Light Mode (default)
      const lightPath = path.join(OUTPUT_DIR, `${route.name}_light.png`)
      await page.screenshot({ path: lightPath, fullPage: true })
      console.log(`   ✅ Light mode: ${route.name}_light.png`)

      // Toggle to Dark Mode
      await page.evaluate(() => {
        document.documentElement.classList.add('dark')
        document.body.classList.add('dark')
      })
      await page.waitForTimeout(500)

      // Capture Dark Mode
      const darkPath = path.join(OUTPUT_DIR, `${route.name}_dark.png`)
      await page.screenshot({ path: darkPath, fullPage: true })
      console.log(`   ✅ Dark mode: ${route.name}_dark.png`)

    } catch (error) {
      console.log(`   ❌ Erro: ${error.message}`)
    }

    await page.close()
    console.log('')
  }

  await browser.close()

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log(`📁 Screenshots salvos em: ${OUTPUT_DIR}`)
}

captureAnalytics().catch(console.error)
