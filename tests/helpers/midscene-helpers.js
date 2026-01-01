// @ts-check
/**
 * 🤖 MIDSCENE.JS AI-POWERED HELPERS
 *
 * Funções helper para testes automatizados usando Midscene.js AI
 * Integra com OpenAI Vision para reconhecimento inteligente de elementos
 *
 * VANTAGENS:
 * - ✅ Reconhecimento visual de elementos via AI
 * - ✅ Comandos em linguagem natural
 * - ✅ Queries inteligentes sobre estado da página
 * - ✅ Self-healing automático quando layout muda
 *
 * IMPORTANTE: Requer OPENAI_API_KEY configurada (custo por chamada)
 *
 * @see https://midscenejs.com/
 */

/**
 * Configurações padrão para Midscene
 */
const DEFAULT_CONFIG = {
  /** Tempo máximo de espera para operações AI (ms) */
  timeout: 30000,
  /** Número máximo de tentativas em caso de erro */
  maxRetries: 3,
  /** Delay inicial para retry exponencial (ms) */
  initialRetryDelay: 1000,
  /** Multiplicador para retry exponencial */
  retryMultiplier: 2
};

/**
 * Verifica se a API key do OpenAI está configurada
 * Retorna true se disponível, false se não
 *
 * @returns {boolean}
 */
function checkApiKey() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey || apiKey.trim() === '') {
    console.log('⚠️ OPENAI_API_KEY não configurada - testes Midscene serão ignorados');
    return false;
  }
  if (!apiKey.startsWith('sk-')) {
    console.log('⚠️ OPENAI_API_KEY inválida (deve começar com sk-) - testes Midscene serão ignorados');
    return false;
  }
  console.log('✅ OPENAI_API_KEY configurada');
  return true;
}

/**
 * Executa uma função com retry e backoff exponencial
 * Útil para lidar com rate limits da API OpenAI
 *
 * @template T
 * @param {() => Promise<T>} fn - Função async a ser executada
 * @param {object} [options] - Opções de retry
 * @param {number} [options.maxRetries] - Número máximo de tentativas
 * @param {number} [options.initialDelay] - Delay inicial em ms
 * @param {number} [options.multiplier] - Multiplicador do delay
 * @returns {Promise<T>}
 */
async function withRetry(fn, options = {}) {
  const maxRetries = options.maxRetries ?? DEFAULT_CONFIG.maxRetries;
  const initialDelay = options.initialDelay ?? DEFAULT_CONFIG.initialRetryDelay;
  const multiplier = options.multiplier ?? DEFAULT_CONFIG.retryMultiplier;

  let lastError;
  let delay = initialDelay;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const isRateLimit = error.message?.includes('rate limit') ||
                          error.message?.includes('429') ||
                          error.message?.includes('Too Many Requests');

      if (attempt === maxRetries) {
        console.log(`❌ Falha após ${maxRetries} tentativas`);
        throw error;
      }

      if (isRateLimit) {
        console.log(`⚠️ Rate limit detectado - aguardando ${delay}ms antes de tentar novamente (tentativa ${attempt}/${maxRetries})`);
      } else {
        console.log(`⚠️ Erro na tentativa ${attempt}/${maxRetries} - retentando em ${delay}ms`);
      }

      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= multiplier;
    }
  }

  throw lastError;
}

/**
 * Cria uma instância do Midscene AI para uma página Playwright
 * Wrapper com configuração padrão e tratamento de erros
 *
 * @param {import('@playwright/test').Page} page - Página Playwright
 * @param {object} [options] - Opções de configuração
 * @param {number} [options.timeout] - Timeout para operações (ms)
 * @returns {Promise<MidsceneAIWrapper>}
 */
async function createMidsceneAI(page, options = {}) {
  // Verificar se API key está configurada
  if (!checkApiKey()) {
    throw new Error('OPENAI_API_KEY não configurada - configure a variável de ambiente');
  }

  const timeout = options.timeout ?? DEFAULT_CONFIG.timeout;

  // Importar Midscene dinamicamente (lazy loading)
  let PlaywrightAiFixture;
  try {
    const midscene = require('@midscene/web/playwright');
    // Midscene pode exportar de diferentes formas dependendo da versão
    PlaywrightAiFixture = midscene.PlaywrightAiFixture ||
                          midscene.PlaywrightAI ||
                          midscene.default?.PlaywrightAiFixture;

    if (!PlaywrightAiFixture) {
      // Tentar usar exports direto
      PlaywrightAiFixture = midscene;
    }
  } catch (importError) {
    console.log('❌ Erro ao importar @midscene/web/playwright:', importError.message);
    throw new Error(`Falha ao carregar Midscene: ${importError.message}. Execute 'npm install' no diretório tests/`);
  }

  console.log('🔄 Inicializando Midscene AI...');

  // Criar wrapper com métodos facilitados
  const wrapper = new MidsceneAIWrapper(page, PlaywrightAiFixture, { timeout });

  console.log('✅ Midscene AI inicializado');
  return wrapper;
}

/**
 * Wrapper para facilitar uso do Midscene com tratamento de erros
 */
class MidsceneAIWrapper {
  /**
   * @param {import('@playwright/test').Page} page
   * @param {any} MidsceneClass
   * @param {object} options
   */
  constructor(page, MidsceneClass, options) {
    this.page = page;
    this.MidsceneClass = MidsceneClass;
    this.timeout = options.timeout;
    this._ai = null;
  }

  /**
   * Obtém a instância AI (lazy initialization)
   * @returns {Promise<any>}
   */
  async _getAI() {
    if (!this._ai) {
      // Tentar diferentes formas de instanciar baseado na API do Midscene
      if (typeof this.MidsceneClass === 'function') {
        if (this.MidsceneClass.prototype && this.MidsceneClass.prototype.constructor) {
          // É uma classe
          this._ai = new this.MidsceneClass(this.page);
        } else {
          // É uma função factory
          this._ai = this.MidsceneClass(this.page);
        }
      } else if (this.MidsceneClass.createPlaywrightAI) {
        this._ai = this.MidsceneClass.createPlaywrightAI(this.page);
      } else if (this.MidsceneClass.PlaywrightAiFixture) {
        this._ai = new this.MidsceneClass.PlaywrightAiFixture(this.page);
      } else {
        throw new Error('Não foi possível inicializar Midscene - API não reconhecida');
      }
    }
    return this._ai;
  }

  /**
   * Executa uma ação via AI usando linguagem natural
   * Exemplos:
   * - ai.action('click on the Login button')
   * - ai.action('type "email@test.com" in the email field')
   * - ai.action('scroll down to see more content')
   *
   * @param {string} instruction - Instrução em linguagem natural
   * @returns {Promise<void>}
   */
  async action(instruction) {
    const ai = await this._getAI();
    console.log(`🔄 AI Action: "${instruction}"`);

    return withRetry(async () => {
      if (typeof ai.aiAction === 'function') {
        await ai.aiAction(instruction);
      } else if (typeof ai.action === 'function') {
        await ai.action(instruction);
      } else if (typeof ai.ai === 'function') {
        await ai.ai(instruction);
      } else {
        throw new Error('Método de action não encontrado na API Midscene');
      }
      console.log(`✅ AI Action concluída: "${instruction}"`);
    });
  }

  /**
   * Faz uma query sobre a página usando AI
   * Retorna informação extraída da página
   * Exemplos:
   * - ai.query('What is the current page title?')
   * - ai.query('Is the user logged in?')
   * - ai.query('How many items are in the cart?')
   *
   * @param {string} question - Pergunta sobre a página
   * @returns {Promise<any>}
   */
  async query(question) {
    const ai = await this._getAI();
    console.log(`🔄 AI Query: "${question}"`);

    return withRetry(async () => {
      let result;
      if (typeof ai.aiQuery === 'function') {
        result = await ai.aiQuery(question);
      } else if (typeof ai.query === 'function') {
        result = await ai.query(question);
      } else if (typeof ai.ask === 'function') {
        result = await ai.ask(question);
      } else {
        throw new Error('Método de query não encontrado na API Midscene');
      }
      console.log(`✅ AI Query resultado: ${JSON.stringify(result)}`);
      return result;
    });
  }

  /**
   * Faz uma asserção via AI
   * Verifica se uma condição é verdadeira na página
   * Exemplos:
   * - ai.assert('The login form should be visible')
   * - ai.assert('There should be at least one machine listed')
   *
   * @param {string} assertion - Asserção a verificar
   * @returns {Promise<void>}
   */
  async assert(assertion) {
    const ai = await this._getAI();
    console.log(`🔄 AI Assert: "${assertion}"`);

    return withRetry(async () => {
      if (typeof ai.aiAssert === 'function') {
        await ai.aiAssert(assertion);
      } else if (typeof ai.assert === 'function') {
        await ai.assert(assertion);
      } else if (typeof ai.verify === 'function') {
        await ai.verify(assertion);
      } else {
        // Fallback: usar query e verificar resultado
        const result = await this.query(`Is this true: ${assertion}? Answer with true or false.`);
        if (result !== true && result !== 'true' && !String(result).toLowerCase().includes('true')) {
          throw new Error(`Assertion failed: ${assertion}`);
        }
      }
      console.log(`✅ AI Assert passou: "${assertion}"`);
    });
  }

  /**
   * Aguarda até que uma condição seja verdadeira
   * Usa AI para verificar estado da página
   *
   * @param {string} condition - Condição a aguardar
   * @param {object} [options] - Opções
   * @param {number} [options.timeout] - Timeout em ms (default: 30000)
   * @param {number} [options.pollInterval] - Intervalo entre verificações (default: 1000)
   * @returns {Promise<void>}
   */
  async waitFor(condition, options = {}) {
    const timeout = options.timeout ?? this.timeout;
    const pollInterval = options.pollInterval ?? 1000;
    const startTime = Date.now();

    console.log(`🔄 AI WaitFor: "${condition}"`);

    while (Date.now() - startTime < timeout) {
      try {
        const result = await this.query(`Is this true: ${condition}? Answer with just true or false.`);
        if (result === true || result === 'true' || String(result).toLowerCase().includes('true')) {
          console.log(`✅ AI WaitFor concluído: "${condition}"`);
          return;
        }
      } catch {
        // Ignorar erros durante polling
      }
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Timeout aguardando: ${condition}`);
  }

  /**
   * Captura screenshot com anotações AI (se suportado)
   *
   * @param {string} [name] - Nome do screenshot
   * @returns {Promise<Buffer|void>}
   */
  async screenshot(name) {
    console.log(`📸 Screenshot: ${name || 'unnamed'}`);
    return this.page.screenshot({ path: name ? `${name}.png` : undefined });
  }
}

/**
 * Wrapper para usar em testes - pula automaticamente se API key não estiver configurada
 * Uso: const { ai, skip } = await setupMidsceneTest(page);
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{ai: MidsceneAIWrapper | null, skip: boolean, skipReason: string | null}>}
 */
async function setupMidsceneTest(page) {
  if (!checkApiKey()) {
    return {
      ai: null,
      skip: true,
      skipReason: 'OPENAI_API_KEY não configurada'
    };
  }

  try {
    const ai = await createMidsceneAI(page);
    return { ai, skip: false, skipReason: null };
  } catch (error) {
    console.log(`⚠️ Erro ao inicializar Midscene: ${error.message}`);
    return {
      ai: null,
      skip: true,
      skipReason: `Erro ao inicializar Midscene: ${error.message}`
    };
  }
}

/**
 * Estima custo aproximado de uma operação Midscene
 * Baseado em pricing médio do OpenAI GPT-4 Vision
 *
 * @param {'action' | 'query' | 'assert'} operationType
 * @returns {string}
 */
function estimateCost(operationType) {
  // Estimativa aproximada baseada em tokens médios por operação
  const costs = {
    action: '$0.01-0.03', // Screenshot + prompt + resposta
    query: '$0.01-0.02',  // Screenshot + pergunta + resposta curta
    assert: '$0.01-0.02'  // Similar ao query
  };
  return costs[operationType] || '$0.01-0.03';
}

/**
 * Log de custo estimado para awareness
 *
 * @param {string} operation - Nome da operação
 */
function logCostWarning(operation) {
  console.log(`💰 Custo estimado para ${operation}: ${estimateCost(operation)} por chamada`);
}

module.exports = {
  // Funções principais
  createMidsceneAI,
  setupMidsceneTest,
  checkApiKey,
  withRetry,

  // Utilitários
  estimateCost,
  logCostWarning,

  // Configurações
  DEFAULT_CONFIG,

  // Classe (para extensão avançada)
  MidsceneAIWrapper
};
