# FAQ - Perguntas Frequentes

## Geral

### O que e GPU Spot?
GPUs Spot sao instancias com desconto de ate 90%, mas podem ser interrompidas a qualquer momento. O Dumont Cloud adiciona failover automatico para garantir que voce nunca perca dados.

### Quanto custa?
Precos variam por GPU. Uma RTX 4090 custa ~$0.40/hora vs $3.00/hora na AWS. Veja a tabela completa em Pricing.

### Preciso de conhecimento tecnico?
Nao! O AI Wizard recomenda a melhor GPU baseado na sua descricao do projeto. Para usuarios avancados, oferecemos controle total via API.

---

## Billing

### Quais formas de pagamento?
- Cartao de credito (Visa, Mastercard, Amex)
- PIX (apenas Brasil)
- Boleto bancario (apenas Brasil)
- Wire transfer (empresas)

### Como funciona a cobranca?
Cobranca por segundo de uso. Voce adiciona creditos e eles sao consumidos conforme o uso. Sem surpresas.

### Tem reembolso?
Creditos nao utilizados podem ser reembolsados em ate 30 dias apos a compra.

---

## Tecnico

### O que acontece se minha GPU for interrompida?
O sistema automaticamente:
1. Detecta a interrupcao
2. Migra para GPU do Warm Pool ou CPU Standby
3. Restaura seus dados do ultimo snapshot
4. Notifica voce por email/webhook

### Quanto tempo leva o failover?
- Warm Pool: ~30-60 segundos
- CPU Standby: ~2-5 minutos

### Posso usar Docker?
Sim! Todas as maquinas suportam Docker. Imagens customizadas tambem sao suportadas.

### Suporta multi-GPU?
Sim! Oferecemos configuracoes de 1 a 8 GPUs por maquina, dependendo da disponibilidade.

---

## Seguranca

### Meus dados estao seguros?
- Criptografia em transito (TLS 1.3)
- Criptografia em repouso (AES-256)
- Snapshots em storage isolado
- Acesso via SSH key apenas

### Tem certificacoes?
Estamos em processo de certificacao SOC 2 Type II. Ja oferecemos:
- GDPR compliance
- HIPAA BAA (plano Enterprise)
- DPA disponivel

---

## Suporte

### Como contato o suporte?
- Chat ao vivo no dashboard
- Email: suporte@dumontcloud.com
- Discord: discord.gg/dumontcloud

### Qual o tempo de resposta?
- Plano Free: 24h
- Plano Pro: 4h
- Plano Enterprise: 1h (24/7)
