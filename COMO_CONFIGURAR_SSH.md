# 🔧 Como Configurar SSH para Antigravity, Windsurf e Cursor

## ❌ Problema Atual

Erro ao conectar:
```
Failed to connect to the remote extension host server
Error: Failed to resolve remote authority
SSH server closed unexpectedly. Error code: 255
ssh: Could not resolve hostname dumont-28917659: nodename nor servname provided, or not known
```

**Causa**: O SSH não está configurado. As IDEs (Antigravity, Windsurf, Cursor) não conseguem encontrar a configuração SSH da máquina.

---

## ✅ Solução Completa (Passo a Passo)

### Passo 1: Baixar o Script de Setup

1. Acesse: http://54.37.225.188:8766/machines
2. Encontre sua máquina
3. Role até a seção "Configuração SSH Necessária"
4. Clique em **"💾 Baixar Script de Setup"**

Isso vai baixar: `setup-ssh-dumont-XXXXXXXX.sh`

### Passo 2: Executar o Script no Terminal (Mac)

Abra o Terminal e execute:

```bash
cd ~/Downloads
bash setup-ssh-dumont-*.sh
```

Você verá:
```
🚀 Configurando SSH para dumont-28917659...
Adicionando configuração SSH...
✅ Configuração SSH adicionada!

📥 Agora você precisa baixar a chave SSH do vast.ai:
```

**O que esse script faz:**
- Cria `~/.ssh/config` se não existir
- Adiciona a configuração SSH da sua máquina
- Define o host, porta, usuário e chave SSH

### Passo 3: Baixar a Chave SSH do Vast.ai

1. Acesse: https://cloud.vast.ai/account/
2. Role até a seção **"SSH Keys"**
3. Clique em **"Show Private Key"**
4. Copie TODA a chave (de `-----BEGIN` até `-----END`)

### Passo 4: Salvar a Chave SSH no Mac

No terminal, execute:

```bash
nano ~/.ssh/vast_rsa
```

1. Cole a chave SSH que você copiou
2. Pressione `Ctrl + O` para salvar
3. Pressione `Enter` para confirmar
4. Pressione `Ctrl + X` para sair

Defina as permissões corretas:

```bash
chmod 600 ~/.ssh/vast_rsa
```

### Passo 5: Testar a Conexão SSH

Execute o teste:

```bash
ssh dumont-28917659
```

(Substitua pelo ID da sua máquina)

**Se funcionar:**
- Você verá o prompt do servidor remoto
- Digite `exit` para sair

**Se NÃO funcionar:**
- Verifique se copiou a chave completa
- Verifique as permissões: `ls -la ~/.ssh/vast_rsa`
- Verifique a configuração: `cat ~/.ssh/config | grep dumont`

### Passo 6: Usar as IDEs

Agora você pode clicar nos botões:
- ✅ **Antigravity** - vai funcionar!
- ✅ **Windsurf** - vai funcionar!
- ✅ **Cursor** - vai funcionar!

---

## 🔍 Debug Avançado

### Verificar se a configuração SSH está correta

```bash
cat ~/.ssh/config | grep -A 7 dumont-28917659
```

Deve mostrar algo como:
```
Host dumont-28917659
  HostName 123.45.67.89
  Port 41234
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  IdentityFile ~/.ssh/vast_rsa
```

### Verificar se a chave existe

```bash
ls -la ~/.ssh/vast_rsa
```

Deve mostrar:
```
-rw-------  1 marcos  staff  1679 Dec 16 22:00 /Users/marcos/.ssh/vast_rsa
```

As permissões **DEVEM** ser `-rw-------` (600)

### Teste SSH detalhado (verbose)

```bash
ssh -vvv dumont-28917659 2>&1 | head -50
```

Isso mostra logs detalhados da conexão. Procure por:
- ✅ `debug1: Reading configuration data /Users/marcos/.ssh/config` - OK
- ✅ `debug1: Connecting to <IP> port <PORT>` - OK
- ❌ `Could not resolve hostname` - SSH config não está funcionando
- ❌ `Permission denied` - Chave SSH incorreta

---

## 🚀 Alternativa Sem SSH: VS Code Online

Se você não quer configurar SSH, use o **VS Code Online**:

1. Acesse: http://54.37.225.188:8766/machines
2. Clique no botão **"VS Code Online"**
3. Abre direto no navegador, sem precisar de SSH!

**Vantagens:**
- ✅ Não precisa configurar SSH
- ✅ Funciona direto no navegador
- ✅ Mesmo VS Code, todas as extensões

**Desvantagens:**
- ❌ Precisa estar com navegador aberto
- ❌ Não integra com sistema de arquivos local

---

## 📋 Checklist Final

- [ ] Baixei o script de setup
- [ ] Executei `bash setup-ssh-dumont-*.sh`
- [ ] Baixei a chave SSH do vast.ai
- [ ] Salvei em `~/.ssh/vast_rsa` com `chmod 600`
- [ ] Testei: `ssh dumont-XXXXXXXX` e conectou
- [ ] Cliquei em OK no dialog do site para marcar como configurado
- [ ] Testei abrir Antigravity/Windsurf/Cursor - funcionou!

---

## ❓ Perguntas Frequentes

**P: O script baixou mas não apareceu dialog no site**
R: Clique novamente em "Baixar Script de Setup", aguarde 1 segundo

**P: A chave SSH está correta mas ainda não conecta**
R: Verifique se a máquina está rodando em: http://54.37.225.188:8766/machines

**P: Aparece "Permission denied (publickey)"**
R: A chave SSH está incorreta. Baixe novamente do vast.ai e substitua

**P: Aparece "Connection timed out"**
R: A máquina pode estar parada ou a porta está bloqueada

**P: Prefiro usar VS Code no navegador**
R: Clique em "VS Code Online" - não precisa SSH!

---

## 🎯 Resumo Ultra-Rápido

```bash
# 1. Baixar script de setup (no site)
# 2. Executar
bash ~/Downloads/setup-ssh-dumont-*.sh

# 3. Copiar chave do vast.ai e salvar
nano ~/.ssh/vast_rsa
chmod 600 ~/.ssh/vast_rsa

# 4. Testar
ssh dumont-XXXXXXXX

# 5. Usar as IDEs! 🎉
```

---

**Feito! Agora Antigravity, Windsurf e Cursor vão funcionar perfeitamente!** ✨
