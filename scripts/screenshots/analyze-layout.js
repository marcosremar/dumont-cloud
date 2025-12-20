#!/usr/bin/env node
/**
 * DumontCloud - Layout Analysis & Improvement Suggestions
 * 
 * Analisa screenshots e código fonte para identificar:
 * - Inconsistências de design
 * - Problemas de espaçamento
 * - Cores não padronizadas
 * - Componentes fora do padrão
 * 
 * Usage:
 *   node analyze-layout.js
 *   node analyze-layout.js --detailed
 *   node analyze-layout.js --output report.md
 */

const fs = require('fs');
const path = require('path');

// Design System Reference (Modern Dark SaaS)
const DESIGN_SYSTEM = {
    colors: {
        background: {
            primary: ['#0a0d0a', '#0d120d', '#111511'],
            secondary: ['#151a15', '#1a1f1a'],
            card: ['#1a1f1a', '#1e231e', 'rgba(30, 35, 30, 0.8)'],
        },
        accent: {
            primary: ['#4ade80', '#22c55e', '#16a34a'],
            secondary: ['#86efac', '#a7f3d0'],
            gradient: ['linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'],
        },
        text: {
            primary: ['#f5f5f5', '#e5e5e5', '#ffffff'],
            secondary: ['#a1a1aa', '#9ca3af', '#71717a'],
            muted: ['#6b7280', '#64748b'],
        },
        borders: ['#2a2f2a', '#333833', 'rgba(74, 222, 128, 0.2)'],
    },
    spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        xxl: '48px',
    },
    borderRadius: {
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        full: '9999px',
    },
    fonts: {
        primary: ['Inter', 'SF Pro Display', 'system-ui'],
        sizes: {
            xs: '12px',
            sm: '14px',
            base: '16px',
            lg: '18px',
            xl: '20px',
            '2xl': '24px',
            '3xl': '30px',
        }
    }
};

// Analysis rules
const ANALYSIS_RULES = [
    {
        id: 'color-consistency',
        name: 'Consistência de Cores',
        check: (content) => {
            const issues = [];
            const nonStandardColors = content.match(/#[0-9a-fA-F]{6}(?![0-9a-fA-F])/g) || [];

            // Flatten all hex colors from design system recursively
            const flattenColors = (obj) => {
                let colors = [];
                for (const val of Object.values(obj)) {
                    if (Array.isArray(val)) {
                        val.forEach(v => {
                            if (typeof v === 'string' && v.startsWith('#')) {
                                colors.push(v.toLowerCase());
                            }
                        });
                    } else if (typeof val === 'object' && val !== null) {
                        colors = colors.concat(flattenColors(val));
                    } else if (typeof val === 'string' && val.startsWith('#')) {
                        colors.push(val.toLowerCase());
                    }
                }
                return colors;
            };

            const allowedColors = flattenColors(DESIGN_SYSTEM.colors);

            nonStandardColors.forEach(color => {
                if (!allowedColors.includes(color.toLowerCase())) {
                    issues.push(`Cor não padronizada: ${color}`);
                }
            });

            return [...new Set(issues)].slice(0, 5);
        }
    },
    {
        id: 'spacing-consistency',
        name: 'Consistência de Espaçamento',
        check: (content) => {
            const issues = [];
            // Check for hardcoded pixel values that are not in the spacing scale
            const pixelValues = content.match(/:\s*(\d+)px/g) || [];
            const allowedSpacing = [4, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64];

            pixelValues.forEach(match => {
                const value = parseInt(match.replace(/[^\d]/g, ''));
                if (value > 0 && value < 100 && !allowedSpacing.includes(value)) {
                    issues.push(`Espaçamento fora do padrão: ${value}px (considere ${findClosest(value, allowedSpacing)}px)`);
                }
            });

            return [...new Set(issues)].slice(0, 5); // Limit to 5 unique issues
        }
    },
    {
        id: 'border-radius',
        name: 'Border Radius Consistente',
        check: (content) => {
            const issues = [];
            const radiusValues = content.match(/border-radius:\s*(\d+)px/g) || [];
            const allowed = [4, 8, 12, 16, 9999];

            radiusValues.forEach(match => {
                const value = parseInt(match.replace(/[^\d]/g, ''));
                if (!allowed.includes(value)) {
                    issues.push(`Border radius não padronizado: ${value}px`);
                }
            });

            return [...new Set(issues)].slice(0, 3);
        }
    },
    {
        id: 'card-styling',
        name: 'Estilização de Cards',
        check: (content) => {
            const issues = [];

            // Check for cards without proper glass morphism
            if (content.includes('Card') && !content.includes('backdrop-filter') && !content.includes('glassmorphism')) {
                if (content.includes('background:') && !content.includes('rgba')) {
                    issues.push('Cards podem se beneficiar de glassmorphism (backdrop-filter: blur)');
                }
            }

            return issues;
        }
    },
    {
        id: 'animation-usage',
        name: 'Uso de Animações',
        check: (content) => {
            const issues = [];

            // Check if page has interactive elements without transitions
            if (content.includes('onClick') || content.includes('hover')) {
                if (!content.includes('transition') && !content.includes('animate')) {
                    issues.push('Elementos interativos podem se beneficiar de transições suaves');
                }
            }

            return issues;
        }
    },
    {
        id: 'responsive-design',
        name: 'Design Responsivo',
        check: (content) => {
            const issues = [];

            if (!content.includes('@media') && !content.includes('useMediaQuery') && !content.includes('sm:') && !content.includes('md:')) {
                issues.push('Considere adicionar breakpoints responsivos');
            }

            // Check for fixed widths
            const fixedWidths = content.match(/width:\s*\d{3,4}px/g) || [];
            if (fixedWidths.length > 2) {
                issues.push(`${fixedWidths.length} larguras fixas grandes encontradas - considere usar max-width ou porcentagens`);
            }

            return issues;
        }
    },
    {
        id: 'accessibility',
        name: 'Acessibilidade',
        check: (content) => {
            const issues = [];

            if (content.includes('<img') && !content.includes('alt=')) {
                issues.push('Imagens sem atributo alt encontradas');
            }

            if (content.includes('onClick') && !content.includes('role=') && !content.includes('button')) {
                issues.push('Elementos clicáveis podem precisar de role="button" para acessibilidade');
            }

            return issues;
        }
    }
];

function findClosest(value, arr) {
    return arr.reduce((prev, curr) =>
        Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
    );
}

async function analyzeFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const fileName = path.basename(filePath);

    const results = {
        file: fileName,
        path: filePath,
        issues: [],
        suggestions: []
    };

    ANALYSIS_RULES.forEach(rule => {
        const issues = rule.check(content);
        if (issues.length > 0) {
            results.issues.push({
                rule: rule.name,
                id: rule.id,
                problems: issues
            });
        }
    });

    return results;
}

async function analyzeAllPages() {
    const pagesDir = path.join(__dirname, '../../web/src/pages');
    const componentsDir = path.join(__dirname, '../../web/src/components');
    const stylesDir = path.join(__dirname, '../../web/src/styles');

    console.log('🔍 DumontCloud Layout Analyzer');
    console.log('━'.repeat(50) + '\n');

    const allResults = [];

    // Analyze pages
    console.log('📄 Analisando páginas...\n');
    const pageFiles = fs.readdirSync(pagesDir)
        .filter(f => f.endsWith('.jsx') && !f.startsWith('._'));

    for (const file of pageFiles) {
        const filePath = path.join(pagesDir, file);
        const result = await analyzeFile(filePath);
        allResults.push(result);

        if (result.issues.length > 0) {
            console.log(`\n📁 ${file}`);
            result.issues.forEach(issue => {
                console.log(`   ⚠️  ${issue.rule}:`);
                issue.problems.forEach(p => console.log(`      • ${p}`));
            });
        } else {
            console.log(`   ✅ ${file} - OK`);
        }
    }

    // Generate improvement suggestions
    console.log('\n' + '━'.repeat(50));
    console.log('💡 SUGESTÕES DE MELHORIA DO LAYOUT\n');

    const suggestions = generateImprovementSuggestions(allResults);
    suggestions.forEach((s, i) => {
        console.log(`${i + 1}. ${s.title}`);
        console.log(`   ${s.description}`);
        if (s.example) {
            console.log(`   Exemplo: ${s.example}`);
        }
        console.log('');
    });

    // Save report
    const reportPath = path.join(__dirname, '../../artifacts/screenshots/layout-analysis.json');
    fs.writeFileSync(reportPath, JSON.stringify({
        timestamp: new Date().toISOString(),
        designSystem: DESIGN_SYSTEM,
        results: allResults,
        suggestions
    }, null, 2));

    console.log('━'.repeat(50));
    console.log(`📊 Relatório salvo em: ${reportPath}`);

    return allResults;
}

function generateImprovementSuggestions(results) {
    const suggestions = [];

    // Collect all unique issues
    const allIssues = results.flatMap(r => r.issues.map(i => i.id));
    const issueCounts = allIssues.reduce((acc, id) => {
        acc[id] = (acc[id] || 0) + 1;
        return acc;
    }, {});

    // Generate suggestions based on common issues
    if (issueCounts['color-consistency'] > 2) {
        suggestions.push({
            title: '🎨 Padronizar Paleta de Cores',
            description: 'Múltiplas páginas usam cores fora do design system. Crie variáveis CSS centralizadas.',
            example: '--color-accent: #4ade80; --color-bg-card: #1a1f1a;'
        });
    }

    if (issueCounts['spacing-consistency'] > 2) {
        suggestions.push({
            title: '📐 Sistema de Espaçamento',
            description: 'Adote uma escala de espaçamento consistente (4, 8, 16, 24, 32, 48px).',
            example: 'Use gap-4 (16px) em vez de valores arbitrários como 15px ou 17px'
        });
    }

    if (issueCounts['animation-usage'] > 1) {
        suggestions.push({
            title: '✨ Adicionar Micro-animações',
            description: 'Melhore a experiência com transições suaves em elementos interativos.',
            example: 'transition: all 0.2s ease-in-out;'
        });
    }

    if (issueCounts['card-styling'] > 0) {
        suggestions.push({
            title: '🪟 Implementar Glassmorphism',
            description: 'Cards podem ter um visual mais moderno com efeito de vidro fosco.',
            example: 'backdrop-filter: blur(12px); background: rgba(26, 31, 26, 0.8);'
        });
    }

    if (issueCounts['responsive-design'] > 1) {
        suggestions.push({
            title: '📱 Melhorar Responsividade',
            description: 'Algumas páginas precisam de breakpoints para mobile/tablet.',
            example: '@media (max-width: 768px) { ... }'
        });
    }

    // Always suggest these improvements
    suggestions.push({
        title: '🌙 Dark Mode Consistente',
        description: 'Garantir que todas as telas usem o tema escuro uniformemente com contraste adequado.',
        example: 'Texto principal: #f5f5f5, Secundário: #a1a1aa'
    });

    suggestions.push({
        title: '🔤 Tipografia Hierárquica',
        description: 'Usar tamanhos de fonte consistentes para criar hierarquia visual clara.',
        example: 'H1: 30px, H2: 24px, H3: 20px, Body: 16px, Small: 14px'
    });

    return suggestions;
}

// Run analysis
analyzeAllPages().catch(console.error);
