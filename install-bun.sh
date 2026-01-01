#!/bin/bash

# Script para instalar o Bun

set -e

echo "🚀 Instalando Bun..."
echo ""

if command -v bun &> /dev/null; then
    echo "✓ Bun já está instalado: $(bun --version)"
    echo ""
    read -p "Deseja atualizar para a última versão? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

curl -fsSL https://bun.sh/install | bash

echo ""
echo "✓ Bun instalado com sucesso!"
echo ""
echo "Para usar o Bun agora, execute:"
echo "  source ~/.bashrc  (ou ~/.zshrc se usar zsh)"
echo ""
echo "Ou feche e abra um novo terminal."
