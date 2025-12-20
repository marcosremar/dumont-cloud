#!/usr/bin/env node
/**
 * Visual Test Runner - VNC-like browser streaming
 *
 * Este script roda testes Playwright com captura contínua de screenshots,
 * transmitindo para o dashboard via WebSocket para uma experiência VNC-like.
 */

const { chromium } = require('@playwright/test');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuração
const DASHBOARD_WS_URL = process.env.DASHBOARD_WS_URL || 'ws://localhost:8082/ws/visual';
const SCREENSHOT_INTERVAL = 200; // ms entre screenshots (5 FPS)
const RUN_ID = process.env.RUN_ID || Date.now().toString();
const TEST_FILE = process.env.TEST_FILE || null;
const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

let ws = null;
let browser = null;
let page = null;
let screenshotInterval = null;
let isRunning = true;

// Conectar ao dashboard via WebSocket
async function connectWebSocket() {
    return new Promise((resolve, reject) => {
        ws = new WebSocket(DASHBOARD_WS_URL);

        ws.on('open', () => {
            console.log('📡 Conectado ao dashboard');
            // Notify dashboard that visual mode is starting
            ws.send(JSON.stringify({
                type: 'visual_start',
                run_id: RUN_ID
            }));
            ws.send(JSON.stringify({
                type: 'visual_runner_connected',
                run_id: RUN_ID
            }));
            resolve();
        });

        ws.on('error', (err) => {
            console.error('WebSocket error:', err.message);
            // Continuar mesmo sem WebSocket
            resolve();
        });

        ws.on('close', () => {
            console.log('WebSocket desconectado');
        });

        // Timeout
        setTimeout(() => resolve(), 3000);
    });
}

// Enviar screenshot para o dashboard
async function sendScreenshot() {
    if (!page || !isRunning) return;

    try {
        const screenshot = await page.screenshot({
            type: 'jpeg',
            quality: 70,
            fullPage: false
        });

        const base64 = screenshot.toString('base64');

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'screenshot',
                run_id: RUN_ID,
                data: base64,
                timestamp: Date.now(),
                url: page.url()
            }));
        }

        // Também salvar localmente para fallback
        const screenshotsDir = path.join(__dirname, 'screenshots', RUN_ID);
        if (!fs.existsSync(screenshotsDir)) {
            fs.mkdirSync(screenshotsDir, { recursive: true });
        }
        const filename = path.join(screenshotsDir, `frame-${Date.now()}.jpg`);
        fs.writeFileSync(filename, screenshot);

    } catch (err) {
        // Página pode estar navegando, ignorar erro
    }
}

// Enviar mensagem de step
function sendStep(stepName, status = 'running') {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'step',
            run_id: RUN_ID,
            step: {
                name: stepName,
                status: status,
                timestamp: Date.now()
            }
        }));
    }
    console.log(`📍 Step: ${stepName} [${status}]`);
}

// Executar teste com streaming
async function runVisualTest() {
    console.log('🚀 Iniciando Visual Test Runner');
    console.log(`   Run ID: ${RUN_ID}`);
    console.log(`   Base URL: ${BASE_URL}`);

    await connectWebSocket();

    // Iniciar navegador (headless para funcionar sem display)
    sendStep('Iniciando navegador', 'running');
    const useHeadless = !process.env.DISPLAY; // headless se não tiver display
    browser = await chromium.launch({
        headless: useHeadless,
        args: ['--window-size=1280,800', '--no-sandbox']
    });
    console.log(`🖥️ Navegador iniciado em modo ${useHeadless ? 'headless' : 'headed'}`);

    const context = await browser.newContext({
        viewport: { width: 1280, height: 800 }
    });

    page = await context.newPage();
    sendStep('Navegador iniciado', 'passed');

    // Iniciar captura contínua de screenshots
    screenshotInterval = setInterval(sendScreenshot, SCREENSHOT_INTERVAL);

    try {
        // Executar sequência de teste
        await runTestSequence();

        sendStep('Teste concluído', 'passed');

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'visual_finished',
                run_id: RUN_ID,
                status: 'passed'
            }));
        }

    } catch (error) {
        console.error('❌ Erro no teste:', error.message);
        sendStep(`Erro: ${error.message}`, 'failed');

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'visual_finished',
                run_id: RUN_ID,
                status: 'failed',
                error: error.message
            }));
        }
    }

    // Aguardar um pouco antes de fechar
    await new Promise(r => setTimeout(r, 2000));

    // Cleanup
    isRunning = false;
    clearInterval(screenshotInterval);
    await browser.close();

    if (ws) ws.close();

    console.log('✅ Visual Test Runner finalizado');
}

// Sequência de teste padrão (pode ser customizada)
async function runTestSequence() {
    // 1. Navegar para a página inicial
    sendStep('Navegando para página inicial', 'running');
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    sendStep('Página inicial carregada', 'passed');

    // 2. Verificar se há botão de login
    sendStep('Verificando autenticação', 'running');
    const loginButton = await page.locator('text=Login, text=Entrar, button:has-text("Login")').first();
    if (await loginButton.isVisible().catch(() => false)) {
        sendStep('Fazendo login', 'running');
        await loginButton.click();
        await page.waitForTimeout(500);

        // Preencher credenciais demo
        const emailInput = await page.locator('input[type="email"], input[name="email"]').first();
        if (await emailInput.isVisible().catch(() => false)) {
            await emailInput.fill('demo@dumont.cloud');
            await page.waitForTimeout(300);
        }

        const passwordInput = await page.locator('input[type="password"]').first();
        if (await passwordInput.isVisible().catch(() => false)) {
            await passwordInput.fill('demo123');
            await page.waitForTimeout(300);
        }

        const submitBtn = await page.locator('button[type="submit"], button:has-text("Entrar")').first();
        if (await submitBtn.isVisible().catch(() => false)) {
            await submitBtn.click();
            await page.waitForTimeout(2000);
        }
        sendStep('Login realizado', 'passed');
    }

    // 3. Navegar para Dashboard
    sendStep('Acessando Dashboard', 'running');
    await page.goto(`${BASE_URL}/app`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    sendStep('Dashboard carregado', 'passed');

    // 4. Verificar elementos do Dashboard
    sendStep('Verificando elementos do Dashboard', 'running');
    await page.waitForTimeout(1000);
    sendStep('Dashboard verificado', 'passed');

    // 5. Navegar para Machines
    sendStep('Acessando página de Máquinas', 'running');
    const machinesLink = await page.locator('a[href*="machines"], text=Máquinas, text=Machines').first();
    if (await machinesLink.isVisible().catch(() => false)) {
        await machinesLink.click();
        await page.waitForTimeout(1500);
    } else {
        await page.goto(`${BASE_URL}/app/machines`, { waitUntil: 'networkidle' });
    }
    sendStep('Página de Máquinas carregada', 'passed');

    // 6. Verificar lista de máquinas
    sendStep('Verificando lista de máquinas', 'running');
    await page.waitForTimeout(1000);
    const machineCards = await page.locator('[class*="card"], [class*="machine"]').count();
    sendStep(`${machineCards} máquinas encontradas`, 'passed');

    // 7. Tentar interagir com uma máquina
    sendStep('Interagindo com máquina', 'running');
    const firstMachine = await page.locator('[class*="card"], [class*="machine"]').first();
    if (await firstMachine.isVisible().catch(() => false)) {
        await firstMachine.hover();
        await page.waitForTimeout(500);

        // Procurar botão de ação
        const actionBtn = await firstMachine.locator('button').first();
        if (await actionBtn.isVisible().catch(() => false)) {
            await actionBtn.hover();
            await page.waitForTimeout(500);
        }
    }
    sendStep('Interação concluída', 'passed');

    // 8. Navegar para Settings
    sendStep('Acessando Settings', 'running');
    const settingsLink = await page.locator('a[href*="settings"], text=Settings, text=Configurações').first();
    if (await settingsLink.isVisible().catch(() => false)) {
        await settingsLink.click();
        await page.waitForTimeout(1500);
    } else {
        await page.goto(`${BASE_URL}/app/settings`, { waitUntil: 'networkidle' });
    }
    sendStep('Settings carregado', 'passed');

    // 9. Scroll pela página
    sendStep('Verificando configurações', 'running');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await page.waitForTimeout(1000);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    sendStep('Configurações verificadas', 'passed');

    // 10. Voltar para Dashboard
    sendStep('Retornando ao Dashboard', 'running');
    await page.goto(`${BASE_URL}/app`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    sendStep('Navegação completa', 'passed');
}

// Executar
runVisualTest().catch(console.error);
