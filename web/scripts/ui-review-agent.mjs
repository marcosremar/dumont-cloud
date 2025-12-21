/**
 * UI Review Agent - Automated UI/UX Analysis
 *
 * Uses Playwright for screenshots + Vertex AI (Gemini Pro) for design analysis
 * Uses GCP Service Account for authentication
 *
 * Usage: node scripts/ui-review-agent.mjs
 */

import { chromium } from 'playwright';
import { VertexAI } from '@google-cloud/vertexai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
export const CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://localhost:5173',
  minScore: 8,
  maxIterations: 5,
  screenshotDir: path.join(__dirname, 'screenshots', 'ui-review'),

  // GCP/Vertex AI Config
  projectId: 'avian-computer-477918-j9',
  location: 'us-central1',
  model: 'gemini-2.0-flash-001',
  credentialsPath: '/home/marcos/dumontcloud/credentials/gcs-service-account.json',
};

// All pages to review
export const PAGES_TO_REVIEW = [
  { path: '/', name: 'Landing Page', auth: false },
  { path: '/login', name: 'Login', auth: false },
  { path: '/app', name: 'Dashboard', auth: true },
  { path: '/app/machines', name: 'Machines', auth: true },
  { path: '/app/metrics', name: 'GPU Metrics', auth: true, tabs: ['spot', 'market', 'llm', 'training'] },
  { path: '/app/metrics-hub', name: 'Metrics Hub', auth: true },
  { path: '/app/savings', name: 'Savings', auth: true },
  { path: '/app/advisor', name: 'AI Advisor', auth: true },
  { path: '/app/settings', name: 'Settings', auth: true },
  { path: '/app/finetune', name: 'Fine Tuning', auth: true },
  { path: '/app/failover-report', name: 'Failover Report', auth: true },
  { path: '/docs', name: 'Documentation', auth: false },
];

// Senior Designer Prompt for Gemini
const DESIGNER_PROMPT = `Você é um Designer Sênior de UI/UX especializado em dashboards e aplicações SaaS B2B.

Analise esta captura de tela de interface e forneça uma avaliação detalhada considerando:

## Critérios de Avaliação (peso igual):

1. **Hierarquia Visual** (0-10)
   - Títulos e subtítulos claros
   - Espaçamento e agrupamento lógico
   - Peso visual adequado dos elementos

2. **Consistência** (0-10)
   - Cores consistentes com o tema (emerald/dark theme)
   - Tipografia uniforme
   - Componentes padronizados

3. **Usabilidade** (0-10)
   - Ações claras e acessíveis
   - Feedback visual adequado
   - Navegação intuitiva

4. **Responsividade** (0-10)
   - Layout adaptável
   - Elementos não quebrados
   - Espaçamento adequado

5. **Estética Geral** (0-10)
   - Visual moderno e profissional
   - Sem elementos desalinhados
   - Cores harmoniosas

## Formato de Resposta (JSON):

{
  "page_name": "Nome da página",
  "scores": {
    "hierarquia_visual": X,
    "consistencia": X,
    "usabilidade": X,
    "responsividade": X,
    "estetica": X
  },
  "score_total": X.X,
  "problemas_criticos": [
    {
      "elemento": "descrição do elemento",
      "problema": "descrição do problema",
      "sugestao": "como corrigir",
      "arquivo_provavel": "caminho provável do arquivo"
    }
  ],
  "melhorias_recomendadas": [
    "melhoria 1",
    "melhoria 2"
  ],
  "pontos_positivos": [
    "ponto positivo 1"
  ],
  "aprovado": true/false
}

IMPORTANTE:
- Score total é a média dos 5 critérios
- "aprovado" = true se score_total >= 8
- Seja específico sobre qual elemento/componente tem problema
- Indique o arquivo provável (ex: src/components/spot/SpotMonitor.jsx)
- Foque em problemas que afetam a experiência do usuário`;

export class UIReviewAgent {
  constructor() {
    this.browser = null;
    this.page = null;
    this.vertexAI = null;
    this.model = null;
    this.results = [];
  }

  async init() {
    // Set credentials environment variable
    process.env.GOOGLE_APPLICATION_CREDENTIALS = CONFIG.credentialsPath;

    // Initialize Vertex AI
    this.vertexAI = new VertexAI({
      project: CONFIG.projectId,
      location: CONFIG.location,
    });

    this.model = this.vertexAI.getGenerativeModel({
      model: CONFIG.model,
    });

    // Initialize Playwright
    this.browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    this.page = await this.browser.newPage();
    await this.page.setViewportSize({ width: 1920, height: 1080 });

    // Create screenshot directory
    if (!fs.existsSync(CONFIG.screenshotDir)) {
      fs.mkdirSync(CONFIG.screenshotDir, { recursive: true });
    }

    console.log('🎨 UI Review Agent initialized');
    console.log(`   Model: Vertex AI ${CONFIG.model}`);
    console.log(`   Project: ${CONFIG.projectId}`);
    console.log(`   Target: ${CONFIG.baseUrl}`);
  }

  async takeScreenshot(pagePath, name) {
    const url = `${CONFIG.baseUrl}${pagePath}`;
    const filename = `${name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.png`;
    const filepath = path.join(CONFIG.screenshotDir, filename);

    try {
      await this.page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await this.page.waitForTimeout(2000); // Wait for animations
      await this.page.screenshot({ path: filepath, fullPage: true });

      console.log(`   📸 Screenshot: ${filename}`);
      return filepath;
    } catch (error) {
      console.error(`   ❌ Failed to capture ${name}: ${error.message}`);
      return null;
    }
  }

  async analyzeWithGemini(screenshotPath, pageName) {
    try {
      console.log(`   🤖 Analyzing with Gemini...`);
      const imageData = fs.readFileSync(screenshotPath);
      const base64Image = imageData.toString('base64');

      const request = {
        contents: [{
          role: 'user',
          parts: [
            { text: `${DESIGNER_PROMPT}\n\nPágina sendo analisada: ${pageName}` },
            {
              inlineData: {
                mimeType: 'image/png',
                data: base64Image
              }
            }
          ]
        }]
      };

      const result = await this.model.generateContent(request);
      const response = await result.response;
      const text = response.candidates[0].content.parts[0].text;

      // Parse JSON from response
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }

      throw new Error('Could not parse Gemini response as JSON');
    } catch (error) {
      console.error(`   ❌ Gemini analysis failed: ${error.message}`);
      return null;
    }
  }

  async reviewPage(pageConfig) {
    const { path: pagePath, name, auth, tabs } = pageConfig;

    console.log(`\n${'─'.repeat(50)}`);
    console.log(`📄 ${name}`);
    console.log('─'.repeat(50));

    // Use demo path for auth pages
    const actualPath = auth ? pagePath.replace('/app', '/demo-app') : pagePath;

    const results = [];

    if (tabs && tabs.length > 0) {
      // Review each tab
      for (const tab of tabs) {
        const tabPath = `${actualPath}?tab=${tab}`;
        const tabName = `${name} - ${tab}`;

        const screenshot = await this.takeScreenshot(tabPath, tabName);
        if (screenshot) {
          const analysis = await this.analyzeWithGemini(screenshot, tabName);
          if (analysis) {
            results.push({ page: tabName, path: tabPath, analysis });
            this.printAnalysis(analysis);
          }
        }
      }
    } else {
      const screenshot = await this.takeScreenshot(actualPath, name);
      if (screenshot) {
        const analysis = await this.analyzeWithGemini(screenshot, name);
        if (analysis) {
          results.push({ page: name, path: actualPath, analysis });
          this.printAnalysis(analysis);
        }
      }
    }

    return results;
  }

  printAnalysis(analysis) {
    const score = analysis.score_total || 0;
    const status = analysis.aprovado ? '✅ APROVADO' : '❌ REPROVADO';
    const scoreBar = '█'.repeat(Math.floor(score)) + '░'.repeat(10 - Math.floor(score));

    console.log(`\n   Score: ${scoreBar} ${score.toFixed(1)}/10 ${status}`);

    if (analysis.scores) {
      console.log('\n   Detalhes:');
      Object.entries(analysis.scores).forEach(([key, value]) => {
        const icon = value >= 8 ? '✓' : value >= 6 ? '○' : '✗';
        console.log(`     ${icon} ${key}: ${value}/10`);
      });
    }

    if (analysis.problemas_criticos?.length > 0) {
      console.log('\n   🚨 Problemas:');
      analysis.problemas_criticos.slice(0, 3).forEach((p, i) => {
        console.log(`     ${i + 1}. ${p.elemento}: ${p.problema}`);
      });
    }
  }

  generateReport() {
    const reportPath = path.join(CONFIG.screenshotDir, `report-${Date.now()}.json`);

    const report = {
      timestamp: new Date().toISOString(),
      config: CONFIG,
      results: this.results,
      summary: {
        total_pages: this.results.length,
        approved: this.results.filter(r => r.analysis?.aprovado).length,
        failed: this.results.filter(r => !r.analysis?.aprovado).length,
        average_score: this.results.length > 0
          ? this.results.reduce((sum, r) => sum + (r.analysis?.score_total || 0), 0) / this.results.length
          : 0,
        all_problems: this.results.flatMap(r => r.analysis?.problemas_criticos || [])
      }
    };

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n📊 Report saved: ${reportPath}`);

    return report;
  }

  async run() {
    console.log('\n' + '═'.repeat(60));
    console.log('  🎨 UI REVIEW AGENT - Senior Designer Analysis');
    console.log('═'.repeat(60));

    try {
      await this.init();

      for (const pageConfig of PAGES_TO_REVIEW) {
        const pageResults = await this.reviewPage(pageConfig);
        this.results.push(...pageResults);
      }

      const report = this.generateReport();

      // Print summary
      console.log('\n' + '═'.repeat(60));
      console.log('  📊 SUMMARY');
      console.log('═'.repeat(60));
      console.log(`  Total Pages Reviewed: ${report.summary.total_pages}`);
      console.log(`  ✅ Approved (>= 8):    ${report.summary.approved}`);
      console.log(`  ❌ Need Improvement:   ${report.summary.failed}`);
      console.log(`  📈 Average Score:      ${report.summary.average_score.toFixed(1)}/10`);

      if (report.summary.all_problems.length > 0) {
        console.log(`\n  🔧 Total Problems Found: ${report.summary.all_problems.length}`);
      }

      // Return pages that need work
      const failedPages = this.results.filter(r => !r.analysis?.aprovado);
      return { report, failedPages };

    } catch (error) {
      console.error('Agent error:', error);
      throw error;
    } finally {
      if (this.browser) {
        await this.browser.close();
      }
    }
  }
}

// Run if called directly
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];

if (isMain) {
  const agent = new UIReviewAgent();
  agent.run()
    .then(({ report, failedPages }) => {
      if (failedPages.length > 0) {
        console.log('\n⚠️  Some pages need improvement. Run fixes and re-analyze.');
        process.exit(1);
      } else {
        console.log('\n✅ All pages approved!');
        process.exit(0);
      }
    })
    .catch(err => {
      console.error('Fatal error:', err);
      process.exit(1);
    });
}
