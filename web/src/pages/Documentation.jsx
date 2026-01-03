import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { marked } from 'marked';
import mermaid from 'mermaid';
import { BookOpen, ChevronRight, Copy, Check, ArrowLeft, Menu, X } from 'lucide-react';

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
});

// Configure mermaid
mermaid.initialize({ startOnLoad: false, theme: 'dark' });

// Premium documentation styles
const documentationStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

  .doc-page {
    --doc-bg: #08090a;
    --doc-surface: #0d0f10;
    --doc-surface-elevated: #12151a;
    --doc-border: rgba(255, 255, 255, 0.06);
    --doc-border-subtle: rgba(255, 255, 255, 0.03);
    --doc-text: #e8eaed;
    --doc-text-secondary: #9ca3af;
    --doc-text-muted: #6b7280;
    --doc-accent: #22c55e;
    --doc-accent-soft: rgba(34, 197, 94, 0.12);
    --doc-accent-glow: rgba(34, 197, 94, 0.25);
    font-family: 'DM Sans', system-ui, sans-serif;
  }

  .doc-serif {
    font-family: 'Instrument Serif', Georgia, serif;
  }

  .doc-mono {
    font-family: 'JetBrains Mono', monospace;
  }

  /* Sidebar animations */
  .sidebar-item {
    position: relative;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .sidebar-item::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 2px;
    height: 0;
    background: var(--doc-accent);
    border-radius: 1px;
    transition: height 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .sidebar-item:hover::before,
  .sidebar-item.active::before {
    height: 60%;
  }

  .sidebar-item.active {
    color: var(--doc-accent);
    background: var(--doc-accent-soft);
  }

  /* Content styles */
  .doc-content {
    line-height: 1.8;
    color: var(--doc-text-secondary);
  }

  .doc-content h1 {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 3rem;
    font-weight: 400;
    letter-spacing: -0.03em;
    line-height: 1.1;
    color: var(--doc-text);
    margin: 0 0 1.5rem 0;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--doc-border);
  }

  .doc-content h2 {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 1.875rem;
    font-weight: 400;
    letter-spacing: -0.02em;
    color: var(--doc-text);
    margin: 3rem 0 1.25rem 0;
    position: relative;
    padding-left: 1rem;
  }

  .doc-content h2::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.25em;
    width: 3px;
    height: 1em;
    background: linear-gradient(180deg, var(--doc-accent) 0%, transparent 100%);
    border-radius: 2px;
  }

  .doc-content h3 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--doc-text);
    margin: 2rem 0 1rem 0;
  }

  .doc-content h4 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--doc-text-muted);
    margin: 1.5rem 0 0.75rem 0;
  }

  .doc-content p {
    margin: 1.25rem 0;
    font-size: 1rem;
  }

  .doc-content strong {
    color: var(--doc-text);
    font-weight: 600;
  }

  .doc-content a {
    color: var(--doc-accent);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.2s;
  }

  .doc-content a:hover {
    border-bottom-color: var(--doc-accent);
  }

  .doc-content ul, .doc-content ol {
    margin: 1.25rem 0;
    padding-left: 0;
    list-style: none;
  }

  .doc-content ul li, .doc-content ol li {
    position: relative;
    padding-left: 1.75rem;
    margin: 0.75rem 0;
  }

  .doc-content ul li::before {
    content: '';
    position: absolute;
    left: 0.25rem;
    top: 0.65em;
    width: 6px;
    height: 6px;
    background: var(--doc-accent);
    border-radius: 50%;
    opacity: 0.7;
  }

  .doc-content ol {
    counter-reset: list-counter;
  }

  .doc-content ol li::before {
    counter-increment: list-counter;
    content: counter(list-counter);
    position: absolute;
    left: 0;
    top: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--doc-accent);
    background: var(--doc-accent-soft);
    width: 1.25rem;
    height: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
  }

  .doc-content code:not(pre code) {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875em;
    background: var(--doc-surface-elevated);
    color: var(--doc-accent);
    padding: 0.2em 0.5em;
    border-radius: 6px;
    border: 1px solid var(--doc-border);
  }

  .doc-content pre {
    background: var(--doc-surface);
    border: 1px solid var(--doc-border);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    overflow-x: auto;
    position: relative;
  }

  .doc-content pre::before {
    content: '';
    position: absolute;
    top: 1rem;
    left: 1rem;
    display: flex;
    gap: 6px;
  }

  .doc-content pre code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
    line-height: 1.7;
    color: var(--doc-text-secondary);
    background: none;
    padding: 0;
    border: none;
  }

  .doc-content blockquote {
    position: relative;
    margin: 2rem 0;
    padding: 1.5rem 1.5rem 1.5rem 2rem;
    background: linear-gradient(135deg, var(--doc-accent-soft) 0%, transparent 100%);
    border-left: 3px solid var(--doc-accent);
    border-radius: 0 12px 12px 0;
    font-style: italic;
  }

  .doc-content blockquote p {
    margin: 0;
    color: var(--doc-text);
  }

  .doc-content table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 2rem 0;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--doc-border);
  }

  .doc-content thead {
    background: var(--doc-surface-elevated);
  }

  .doc-content th {
    padding: 1rem 1.25rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--doc-text-muted);
    border-bottom: 1px solid var(--doc-border);
  }

  .doc-content td {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--doc-border-subtle);
    color: var(--doc-text-secondary);
  }

  .doc-content tr:last-child td {
    border-bottom: none;
  }

  .doc-content tr:hover td {
    background: var(--doc-surface);
  }

  .doc-content hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--doc-border), transparent);
    margin: 3rem 0;
  }

  .doc-content img {
    max-width: 100%;
    border-radius: 12px;
    border: 1px solid var(--doc-border);
  }

  /* Scroll progress indicator */
  .scroll-progress {
    position: fixed;
    top: 0;
    left: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--doc-accent), #10b981);
    z-index: 100;
    transition: width 0.1s;
  }

  /* Fade in animation */
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fade-in {
    animation: fadeInUp 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  }

  /* Loading skeleton */
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }

  .skeleton {
    background: linear-gradient(90deg, var(--doc-surface) 25%, var(--doc-surface-elevated) 50%, var(--doc-surface) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
  }

  /* Copy button */
  .copy-btn {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    padding: 0.5rem;
    background: var(--doc-surface-elevated);
    border: 1px solid var(--doc-border);
    border-radius: 6px;
    color: var(--doc-text-muted);
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;
  }

  .doc-content pre:hover .copy-btn {
    opacity: 1;
  }

  .copy-btn:hover {
    color: var(--doc-accent);
    border-color: var(--doc-accent);
  }
`;

const Documentation = () => {
  const { t } = useTranslation();
  const { docId } = useParams();
  const navigate = useNavigate();
  const [menu, setMenu] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeDoc, setActiveDoc] = useState(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [copied, setCopied] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});

  // Track scroll progress
  useEffect(() => {
    const handleScroll = () => {
      const windowHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = (window.scrollY / windowHeight) * 100;
      setScrollProgress(Math.min(progress, 100));
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Load menu on component mount
  useEffect(() => {
    loadMenu();
  }, []);

  // Load content when docId changes
  useEffect(() => {
    if (docId) {
      loadDoc(`${docId}.md`);
    } else if (menu.length > 0) {
      const firstDoc = findFirstDoc(menu);
      if (firstDoc) {
        loadDoc(firstDoc);
      }
    }
  }, [docId, menu]);

  // Render mermaid diagrams after content loads
  useEffect(() => {
    if (content) {
      setTimeout(() => {
        mermaid.run();
      }, 100);
    }
  }, [content]);

  // Auto-expand section containing active doc
  useEffect(() => {
    if (activeDoc && menu.length > 0) {
      const newExpanded = { ...expandedSections };
      menu.forEach(item => {
        if (item.type === 'dir' && item.children) {
          const hasActiveChild = item.children.some(child => child.id === activeDoc);
          if (hasActiveChild) {
            newExpanded[item.name] = true;
          }
        }
      });
      setExpandedSections(newExpanded);
    }
  }, [activeDoc, menu]);

  const loadMenu = async () => {
    try {
      const response = await fetch('/api/docs/menu');
      if (response.ok) {
        const data = await response.json();
        setMenu(data.menu);
      } else {
        throw new Error('API failed');
      }
    } catch (error) {
      console.warn('Error loading menu, using mock data:', error);
      setMenu([
        {
          name: 'Getting Started',
          type: 'dir',
          children: [
            { name: 'Introduction', type: 'file', id: '01_Introduction.md' },
            { name: 'Quick Start', type: 'file', id: '02_Quick_Start.md' }
          ]
        },
        {
          name: 'Features',
          type: 'dir',
          children: [
            { name: 'GPU Instances', type: 'file', id: '03_GPU_Instances.md' },
            { name: 'AI Wizard', type: 'file', id: '04_AI_Wizard.md' }
          ]
        },
        {
          name: 'API Reference',
          type: 'dir',
          children: [
            { name: 'Authentication', type: 'file', id: '05_Authentication.md' },
            { name: 'Endpoints', type: 'file', id: '06_Endpoints.md' }
          ]
        }
      ]);
    }
  };

  const loadDoc = async (id) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/docs/content/${encodeURI(id)}`);
      if (response.ok) {
        const data = await response.json();
        const htmlContent = marked.parse(data.content);
        setContent(htmlContent);
        setActiveDoc(id);
      } else {
        throw new Error('Doc not found');
      }
    } catch (error) {
      console.warn('Error loading document, using mock content:', error);
      const mockMd = `# ${cleanName(id.replace('.md', ''))}

Welcome to the Dumont Cloud documentation. This guide will help you understand and utilize our platform's powerful features.

## Overview

Dumont Cloud provides enterprise-grade GPU infrastructure for AI/ML workloads. Our platform offers:

- **High-Performance Computing**: Access to the latest NVIDIA GPUs
- **Automatic Failover**: Seamless migration between GPU and CPU instances
- **Cost Optimization**: Pay only for what you use

> "The future of AI infrastructure is here. Dumont Cloud makes it accessible to everyone."

## Getting Started

To begin using Dumont Cloud, follow these steps:

1. Create your account at [dumont.cloud](https://dumont.cloud)
2. Configure your API keys in the dashboard
3. Deploy your first GPU instance
4. Monitor performance in real-time

### Code Example

\`\`\`python
import dumont

# Initialize client
client = dumont.Client(api_key="your-key")

# Create a GPU instance
instance = client.instances.create(
    gpu_type="RTX_4090",
    region="us-east",
    auto_failover=True
)

print(f"Instance {instance.id} is ready!")
\`\`\`

## Architecture

| Component | Description | Status |
|-----------|-------------|--------|
| GPU Pool | NVIDIA RTX 4090, A100 | Active |
| CPU Fallback | Intel Xeon | Standby |
| Storage | NVMe SSD | Active |

---

For more information, visit our [API documentation](/docs/api) or contact support.`;
      setContent(marked.parse(mockMd));
      setActiveDoc(id);
    }
    setLoading(false);
  };

  const findFirstDoc = (items) => {
    for (const item of items) {
      if (item.type === 'file') return item.id;
      if (item.type === 'dir' && item.children) {
        const child = findFirstDoc(item.children);
        if (child) return child;
      }
    }
    return null;
  };

  const cleanName = (name) => {
    return name
      .replace(/^\d+_/, '')
      .replace(/_/g, ' ')
      .replace('.md', '')
      .trim();
  };

  const getSectionIcon = (name) => {
    const icons = {
      'Getting Started': '◈',
      'User Guide': '◇',
      'Features': '◆',
      'API': '⬡',
      'API Reference': '⬡',
      'Engineering': '⬢',
      'Operations': '○',
      'Business': '●',
      'Research': '◎',
      'Sprints': '▸',
      'Analise Mercado': '▹'
    };
    const cleanedName = cleanName(name);
    return icons[cleanedName] || '◈';
  };

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const copyCurrentUrl = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderMenuItem = (item) => {
    if (item.type === 'file') {
      const docPath = item.id.replace('.md', '');
      const isActive = activeDoc === item.id;

      return (
        <button
          key={item.id}
          onClick={() => {
            navigate(`/docs/${docPath}`);
            setSidebarOpen(false);
          }}
          className={`sidebar-item w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
            isActive
              ? 'active text-[var(--doc-accent)] bg-[var(--doc-accent-soft)]'
              : 'text-[var(--doc-text-secondary)] hover:text-[var(--doc-text)] hover:bg-white/[0.03]'
          }`}
        >
          {cleanName(item.name)}
        </button>
      );
    } else if (item.type === 'dir') {
      const isExpanded = expandedSections[item.name] ?? true;

      return (
        <div key={item.name} className="mb-6">
          <button
            onClick={() => toggleSection(item.name)}
            className="flex items-center gap-2 w-full px-2 py-1.5 text-[var(--doc-text-muted)] hover:text-[var(--doc-text-secondary)] transition-colors"
          >
            <ChevronRight
              className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
            />
            <span className="text-[10px] font-semibold uppercase tracking-[0.15em]">
              {getSectionIcon(item.name)} {cleanName(item.name)}
            </span>
          </button>
          <div className={`mt-2 space-y-0.5 overflow-hidden transition-all duration-200 ${
            isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
          }`}>
            {item.children.map(renderMenuItem)}
          </div>
        </div>
      );
    }
    return null;
  };

  const LoadingSkeleton = () => (
    <div className="space-y-6 animate-fade-in">
      <div className="skeleton h-12 w-3/4" />
      <div className="skeleton h-px w-full opacity-20" />
      <div className="space-y-3">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-5/6" />
        <div className="skeleton h-4 w-4/5" />
      </div>
      <div className="skeleton h-32 w-full" />
      <div className="space-y-3">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
    </div>
  );

  return (
    <div className="doc-page min-h-screen bg-[var(--doc-bg)]">
      <style>{documentationStyles}</style>

      {/* Scroll progress */}
      <div className="scroll-progress" style={{ width: `${scrollProgress}%` }} />

      {/* Mobile header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-[var(--doc-surface)]/95 backdrop-blur-xl border-b border-[var(--doc-border)]">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 -ml-2 text-[var(--doc-text-secondary)] hover:text-[var(--doc-text)] transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <span className="doc-serif text-lg text-[var(--doc-text)]">Documentation</span>
          <div className="w-9" />
        </div>
      </header>

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-72 bg-[var(--doc-surface)] border-r border-[var(--doc-border)] transform transition-transform duration-300 ease-out lg:translate-x-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex flex-col h-full">
          {/* Header with back button */}
          <div className="p-4 border-b border-[var(--doc-border)]">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 w-full px-3 py-2.5 rounded-lg text-sm font-medium bg-[var(--doc-accent)]/10 text-[var(--doc-accent)] hover:bg-[var(--doc-accent)]/20 border border-[var(--doc-accent)]/20 transition-all group"
            >
              <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
              {t('documentation.backToApp') || 'Voltar ao App'}
            </button>
          </div>

          {/* Logo */}
          <div className="px-6 py-5 border-b border-[var(--doc-border)]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--doc-accent)] to-emerald-600 flex items-center justify-center shadow-lg shadow-[var(--doc-accent-glow)]">
                <BookOpen className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="doc-serif text-lg text-[var(--doc-text)] tracking-tight">Documentação</h1>
                <p className="text-[9px] font-medium uppercase tracking-[0.2em] text-[var(--doc-text-muted)]">
                  Dumont Cloud
                </p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            {menu.map(renderMenuItem)}
          </nav>

        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="lg:pl-72 min-h-screen">
        <div className="max-w-3xl mx-auto px-6 py-16 lg:px-12 lg:py-20 pt-24 lg:pt-20">
          {loading ? (
            <LoadingSkeleton />
          ) : (
            <article className="animate-fade-in">
              <div
                className="doc-content"
                dangerouslySetInnerHTML={{ __html: content }}
              />
            </article>
          )}

          {/* Copy URL floating button */}
          {activeDoc && (
            <button
              onClick={copyCurrentUrl}
              className={`fixed bottom-6 right-6 flex items-center gap-2 px-4 py-3 rounded-full text-sm font-medium transition-all duration-300 shadow-xl ${
                copied
                  ? 'bg-[var(--doc-accent)] text-white'
                  : 'bg-[var(--doc-surface-elevated)] text-[var(--doc-text-secondary)] hover:text-[var(--doc-text)] border border-[var(--doc-border)] hover:border-[var(--doc-accent)]/30 hover:shadow-[var(--doc-accent-glow)]'
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>{t('documentation.copyLink') || 'Copy Link'}</span>
                </>
              )}
            </button>
          )}

          {/* Footer */}
          <footer className="mt-24 pt-8 border-t border-[var(--doc-border)] text-center">
            <p className="text-xs text-[var(--doc-text-muted)] tracking-wide">
              {t('documentation.footer') || '© 2024 Dumont Cloud. All rights reserved.'}
            </p>
          </footer>
        </div>
      </main>
    </div>
  );
};

export default Documentation;
