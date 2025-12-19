import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import mermaid from 'mermaid';

// Import Dumont UI components
import Layout from '../components/Layout';
import { Card, Button, Badge, Spinner } from '../components/tailadmin-ui';

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
});

// Configure mermaid
mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

const Documentation = () => {
  const { docId } = useParams();
  const navigate = useNavigate();
  const [menu, setMenu] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeDoc, setActiveDoc] = useState(null);

  // Load menu on component mount
  useEffect(() => {
    loadMenu();
  }, []);

  // Load content when docId changes
  useEffect(() => {
    if (docId) {
      loadDoc(`${docId}.md`);
    } else if (menu.length > 0) {
      // Load first doc if no docId specified
      const firstDoc = findFirstDoc(menu);
      if (firstDoc) {
        navigate(`/docs/${firstDoc.replace('.md', '')}`, { replace: true });
      }
    }
  }, [docId, menu, navigate]);

  // Render mermaid diagrams after content loads
  useEffect(() => {
    if (content) {
      setTimeout(() => {
        mermaid.run();
      }, 100);
    }
  }, [content]);

  const loadMenu = async () => {
    try {
      const response = await fetch('/api/docs/menu');
      if (response.ok) {
        const data = await response.json();
        setMenu(data.menu);
      } else {
        console.error('Failed to load menu');
      }
    } catch (error) {
      console.error('Error loading menu:', error);
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
        setContent('<h1>Documento não encontrado</h1>');
      }
    } catch (error) {
      console.error('Error loading document:', error);
      setContent(`<div class="text-red-500 p-4">Erro ao carregar documento: ${id}</div>`);
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
      .replace(/^\d+_/, '')  // Remove leading numbers like "01_"
      .replace(/_/g, ' ')     // Replace underscores with spaces
      .trim();
  };

  const getSectionIcon = (name) => {
    const icons = {
      'Getting Started': '🚀',
      'User Guide': '📖',
      'Features': '⚡',
      'API': '🔌',
      'Engineering': '🛠️',
      'Operations': '⚙️',
      'Business': '💼',
      'Research': '🔬',
      'Sprints': '🏃',
      'Analise Mercado': '📊'
    };
    const cleanedName = cleanName(name);
    return icons[cleanedName] || '📁';
  };

  const renderMenuItem = (item) => {
    if (item.type === 'file') {
      const docPath = item.id.replace('.md', '');
      const isActive = activeDoc === item.id;

      return (
        <Button
          key={item.id}
          variant={isActive ? "primary" : "ghost"}
          size="sm"
          className="w-full justify-start mb-1"
          onClick={() => navigate(`/docs/${docPath}`)}
        >
          <span className="text-emerald-500 mr-2">•</span>
          {cleanName(item.name)}
        </Button>
      );
    } else if (item.type === 'dir') {
      return (
        <div key={item.name} className="mb-6">
          <div className="flex items-center gap-2 mb-3 px-2">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {getSectionIcon(item.name)} {cleanName(item.name)}
            </span>
          </div>
          <div className="ml-2">
            {item.children.map(renderMenuItem)}
          </div>
        </div>
      );
    }
    return null;
  };

  const copyCurrentUrl = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
  };

  return (
    <Layout>
      <div className="flex h-screen bg-gray-50">
        {/* Mobile sidebar toggle */}
        <div className="md:hidden fixed top-4 left-4 z-50">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </Button>
        </div>

        {/* Sidebar */}
        <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 transform transition-transform duration-200 ease-in-out md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                <h1 className="text-lg font-bold text-gray-900 tracking-tight">Dumont Cloud</h1>
              </div>
              <p className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Live Docs</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto p-4">
              {menu.map(renderMenuItem)}
            </nav>

            {/* Back to app button */}
            <div className="p-4 border-t border-gray-200">
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => navigate('/')}
              >
                ← Voltar para App
              </Button>
            </div>
          </div>
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-25 z-30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 md:ml-64">
          <div className="max-w-4xl mx-auto px-6 py-8 md:px-12 md:py-16">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <Spinner />
                <span className="ml-2 text-gray-500">Carregando documentação...</span>
              </div>
            ) : (
              <Card className="p-8">
                <div
                  className="prose prose-gray max-w-none"
                  dangerouslySetInnerHTML={{ __html: content }}
                />
              </Card>
            )}

            {/* Copy URL button */}
            {activeDoc && (
              <div className="fixed bottom-4 right-4">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={copyCurrentUrl}
                  className="shadow-lg"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copiar URL
                </Button>
              </div>
            )}

            {/* Footer */}
            <footer className="mt-20 pt-8 border-t border-gray-200 text-center text-xs text-gray-400">
              <p>Live Documentation System • Dumont Cloud &copy; 2025</p>
            </footer>
          </div>
        </main>
      </div>
    </Layout>
  );
};

export default Documentation;
