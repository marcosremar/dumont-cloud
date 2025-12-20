#!/usr/bin/env node
/**
 * DumontCloud - Automated Screenshot Capture Script
 * 
 * Features:
 * - Runs in background (nohup support)
 * - Auto-recovery on failures
 * - Progress tracking with JSON state file
 * - Supports demo mode (no auth needed)
 * - Full-page and viewport screenshots
 * - Organized output with timestamps
 * 
 * Usage:
 *   node capture-all-screens.js              # Normal run
 *   node capture-all-screens.js --resume     # Resume from last failure
 *   node capture-all-screens.js --demo       # Use demo routes only
 *   node capture-all-screens.js --clean      # Start fresh, ignore state
 * 
 * Background execution:
 *   nohup node capture-all-screens.js > screenshots.log 2>&1 &
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    baseUrl: 'http://localhost:5173',
    outputDir: path.join(__dirname, '../../artifacts/screenshots'),
    stateFile: path.join(__dirname, 'screenshot-state.json'),
    logFile: path.join(__dirname, '../../artifacts/screenshots/capture.log'),
    viewport: { width: 1920, height: 1080 },
    timeout: 30000,
    waitAfterLoad: 2000,
    retryAttempts: 3,
    retryDelay: 2000,
};

// All routes to capture
const ROUTES = [
    // Public routes
    { path: '/', name: 'landing-page', description: 'Landing Page / Home', authRequired: false },
    { path: '/login', name: 'login-page', description: 'Login Page', authRequired: false },

    // Demo routes (no auth needed - using demo mode)
    { path: '/demo-app', name: 'dashboard', description: 'Dashboard Principal' },
    { path: '/demo-app/machines', name: 'machines', description: 'Gerenciamento de Máquinas' },
    { path: '/demo-app/advisor', name: 'advisor', description: 'GPU Advisor' },
    { path: '/demo-app/metrics-hub', name: 'metrics-hub', description: 'Metrics Hub' },
    { path: '/demo-app/metrics', name: 'gpu-metrics', description: 'GPU Metrics' },
    { path: '/demo-app/savings', name: 'savings', description: 'Economia / Savings' },
    { path: '/demo-app/settings', name: 'settings', description: 'Configurações' },
    { path: '/demo-app/failover-report', name: 'failover-report', description: 'Relatório de Failover' },
    { path: '/demo-app/finetune', name: 'finetune', description: 'Fine-Tuning' },
    { path: '/demo-docs', name: 'documentation', description: 'Documentação' },
];

// State management for recovery
class StateManager {
    constructor() {
        this.state = {
            started: null,
            lastUpdated: null,
            completed: [],
            failed: [],
            pending: [],
            inProgress: null,
            totalRoutes: ROUTES.length,
        };
        this.load();
    }

    load() {
        try {
            if (fs.existsSync(CONFIG.stateFile)) {
                this.state = JSON.parse(fs.readFileSync(CONFIG.stateFile, 'utf8'));
                console.log(`📂 Estado carregado: ${this.state.completed.length}/${this.state.totalRoutes} completas`);
            }
        } catch (e) {
            console.error('⚠️  Erro ao carregar estado:', e.message);
        }
    }

    save() {
        this.state.lastUpdated = new Date().toISOString();
        fs.writeFileSync(CONFIG.stateFile, JSON.stringify(this.state, null, 2));
    }

    start() {
        this.state.started = new Date().toISOString();
        this.state.pending = ROUTES.map(r => r.name);
        this.state.completed = [];
        this.state.failed = [];
        this.save();
    }

    markInProgress(routeName) {
        this.state.inProgress = routeName;
        this.save();
    }

    markCompleted(routeName) {
        this.state.completed.push(routeName);
        this.state.pending = this.state.pending.filter(r => r !== routeName);
        this.state.inProgress = null;
        this.save();
    }

    markFailed(routeName, error) {
        this.state.failed.push({ route: routeName, error: error.message, time: new Date().toISOString() });
        this.state.pending = this.state.pending.filter(r => r !== routeName);
        this.state.inProgress = null;
        this.save();
    }

    getIncomplete() {
        return ROUTES.filter(r =>
            !this.state.completed.includes(r.name) &&
            !this.state.failed.some(f => f.route === r.name)
        );
    }
}

// Logger
class Logger {
    constructor() {
        this.ensureLogDir();
    }

    ensureLogDir() {
        const dir = path.dirname(CONFIG.logFile);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    }

    write(message) {
        const timestamp = new Date().toISOString();
        const logLine = `[${timestamp}] ${message}\n`;
        console.log(message);
        fs.appendFileSync(CONFIG.logFile, logLine);
    }

    info(msg) { this.write(`ℹ️  ${msg}`); }
    success(msg) { this.write(`✅ ${msg}`); }
    error(msg) { this.write(`❌ ${msg}`); }
    warning(msg) { this.write(`⚠️  ${msg}`); }
}

// Screenshot capture
async function captureScreenshot(page, route, logger) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${route.name}_${timestamp}.png`;
    const filepath = path.join(CONFIG.outputDir, filename);

    // Full page screenshot
    const fullPageFilename = `${route.name}_fullpage_${timestamp}.png`;
    const fullPageFilepath = path.join(CONFIG.outputDir, fullPageFilename);

    logger.info(`📸 Navegando para: ${CONFIG.baseUrl}${route.path}`);

    await page.goto(`${CONFIG.baseUrl}${route.path}`, {
        waitUntil: 'networkidle',
        timeout: CONFIG.timeout
    });

    // Wait for content to render
    await page.waitForTimeout(CONFIG.waitAfterLoad);

    // Viewport screenshot
    await page.screenshot({
        path: filepath,
        fullPage: false
    });
    logger.success(`Screenshot viewport: ${filename}`);

    // Full page screenshot
    await page.screenshot({
        path: fullPageFilepath,
        fullPage: true
    });
    logger.success(`Screenshot full page: ${fullPageFilename}`);

    return { viewport: filepath, fullPage: fullPageFilepath };
}

async function captureWithRetry(page, route, logger, stateManager) {
    for (let attempt = 1; attempt <= CONFIG.retryAttempts; attempt++) {
        try {
            stateManager.markInProgress(route.name);
            const result = await captureScreenshot(page, route, logger);
            stateManager.markCompleted(route.name);
            return result;
        } catch (error) {
            logger.warning(`Tentativa ${attempt}/${CONFIG.retryAttempts} falhou para ${route.name}: ${error.message}`);

            if (attempt === CONFIG.retryAttempts) {
                stateManager.markFailed(route.name, error);
                throw error;
            }

            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
        }
    }
}

async function main() {
    const args = process.argv.slice(2);
    const isResume = args.includes('--resume');
    const isClean = args.includes('--clean');
    const isDemoOnly = args.includes('--demo');

    const logger = new Logger();
    const stateManager = new StateManager();

    logger.info('🚀 Iniciando captura de screenshots do DumontCloud');
    logger.info(`   Base URL: ${CONFIG.baseUrl}`);
    logger.info(`   Output: ${CONFIG.outputDir}`);

    // Ensure output directory exists
    if (!fs.existsSync(CONFIG.outputDir)) {
        fs.mkdirSync(CONFIG.outputDir, { recursive: true });
    }

    // Clean start or resume
    if (isClean || !isResume) {
        stateManager.start();
        logger.info('📝 Iniciando nova sessão de captura');
    } else {
        logger.info('📝 Retomando sessão anterior');
    }

    let browser;
    try {
        browser = await chromium.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        const context = await browser.newContext({
            viewport: CONFIG.viewport,
            deviceScaleFactor: 1,
        });

        const page = await context.newPage();

        // Get routes to process
        const routesToProcess = isResume ? stateManager.getIncomplete() : ROUTES;

        logger.info(`📋 Rotas a processar: ${routesToProcess.length}`);

        const results = {
            success: [],
            failed: []
        };

        for (const route of routesToProcess) {
            try {
                logger.info(`\n━━━ Processando: ${route.description} ━━━`);
                const screenshots = await captureWithRetry(page, route, logger, stateManager);
                results.success.push({
                    route: route.name,
                    description: route.description,
                    screenshots
                });
            } catch (error) {
                logger.error(`Falha ao capturar ${route.name}: ${error.message}`);
                results.failed.push({
                    route: route.name,
                    error: error.message
                });
            }
        }

        // Generate summary report
        const summaryFile = path.join(CONFIG.outputDir, 'summary.json');
        const summary = {
            timestamp: new Date().toISOString(),
            baseUrl: CONFIG.baseUrl,
            totalRoutes: ROUTES.length,
            success: results.success.length,
            failed: results.failed.length,
            results: results
        };
        fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2));

        logger.info('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        logger.info('📊 RESUMO DA CAPTURA');
        logger.success(`   Sucesso: ${results.success.length}/${ROUTES.length}`);
        if (results.failed.length > 0) {
            logger.error(`   Falhas: ${results.failed.length}`);
            results.failed.forEach(f => logger.error(`   - ${f.route}: ${f.error}`));
        }
        logger.info(`📁 Screenshots salvos em: ${CONFIG.outputDir}`);
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

        await browser.close();

    } catch (error) {
        logger.error(`Erro fatal: ${error.message}`);
        if (browser) await browser.close();
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n⚠️  Interrompido pelo usuário. Estado salvo para recuperação.');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n⚠️  Terminado. Estado salvo para recuperação.');
    process.exit(0);
});

main().catch(console.error);
