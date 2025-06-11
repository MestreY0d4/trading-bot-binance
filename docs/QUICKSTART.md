# 🚀 Guia Rápido - Primeiros Passos

Este guia te leva do zero ao bot funcionando em 15 minutos.

## ✅ Checklist Pré-Início

- [ ] Python 3.9+ instalado
- [ ] Conta Binance Testnet criada
- [ ] API Keys obtidas
- [ ] 15 minutos livres

## 📦 Passo 1: Instalar o Bot (5 min)

```bash
# 1. Baixar o código
git clone https://github.com/seu-usuario/trading-bot-binance.git
cd trading-bot-binance

# 2. Criar ambiente virtual
python -m venv venv

# 3. Ativar ambiente
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instalar dependências
pip install -r requirements.txt
```

## 🔑 Passo 2: Configurar API Keys (2 min)

### Opção A: Editar arquivo (mais fácil)

1. Abra `config/settings.yaml`
2. Encontre a seção `binance:`
3. Substitua:
```yaml
binance:
  testnet_api_key: "COLE_SUA_API_KEY_AQUI"
  testnet_api_secret: "COLE_SEU_API_SECRET_AQUI"
```

### Opção B: Variáveis de ambiente (mais seguro)

```bash
# Windows
set BINANCE_TESTNET_API_KEY=sua_key_aqui
set BINANCE_TESTNET_API_SECRET=seu_secret_aqui

# Linux/Mac
export BINANCE_TESTNET_API_KEY=sua_key_aqui
export BINANCE_TESTNET_API_SECRET=seu_secret_aqui
```

## 🏃 Passo 3: Primeira Execução (8 min)

### 1. Iniciar o bot

```bash
python main.py
```

### 2. O que vai acontecer:

```
=== INICIANDO BOT DE TRADING V5.1 ===
Modo: TESTNET
📊 Baixando dados históricos...
Baixando BTCUSDT... [████████████] 100%
Baixando ETHUSDT... [████████████] 100%
Baixando SOLUSDT... [████████████] 100%
✅ Bot inicializado com sucesso!
```

### 3. Dashboard aparece:

```
╔═══════════════════════════════════════════════════╗
║ BOT TRADING V5.1 [Testnet] [●] Conectado         ║
╠═══════════════════════════════════════════════════╣
║ Capital: 200 USDT | P&L Hoje: +0.0% (+0 USD)     ║
║                                                   ║
║ [▶️ INICIAR] [⏸️ PAUSAR] [⏹️ PARAR] [📊 RELATÓRIO] ║
║                                                   ║
║ Status: Aguardando comando...                     ║
╚═══════════════════════════════════════════════════╝
```

### 4. Pressione 'P' para iniciar trading

O bot começará a procurar oportunidades!

## 🎯 O Que Observar

### Primeiros 30 minutos:
- Bot analisando mercado
- Pode não haver trades imediatos (normal!)
- Observe o status mudar para "Aguardando sinal..."

### Quando acontece um trade:
```
║ Posições Abertas: 1/2                             ║
║ • BTC: Comprado 42,150 | P&L: +0.8%              ║
```

### Sinais de que está funcionando:
- ✅ Status: "Conectado"
- ✅ Preços atualizando
- ✅ "Aguardando sinal..." aparece
- ✅ Sem erros vermelhos

## 🛑 Como Parar com Segurança

1. Pressione **'S'** no dashboard
2. Bot fecha posições abertas (se houver)
3. Salva dados e encerra

**NÃO use Ctrl+C** - pode deixar posições abertas!

## 📊 Analisando Resultados

### Após algumas horas/dias:

1. Pressione **'R'** para ver relatório:
```
╔══════════════════════════════════════════════╗
║           RELATÓRIO DIÁRIO                   ║
╠══════════════════════════════════════════════╣
║ Total de Trades: 12                          ║
║ Win Rate: 58.3%                              ║
║ P&L Líquido: +4.2 USDT                      ║
╚══════════════════════════════════════════════╝
```

2. Verifique logs em `logs/bot_20240110.log`

3. Analise trades no banco: `data/trading_bot.db`

## 🎓 Próximos Passos

### Dia 1-3: Observação
- Deixe rodar no testnet
- Observe padrões
- Entenda quando entra/sai

### Dia 4-5: Ajustes
Se win rate < 55%, ajuste em `settings.yaml`:
```yaml
strategy:
  rsi_oversold: 30    # Tente 28 ou 35
  rsi_overbought: 70  # Tente 65 ou 72
```

### Semana 2: Produção
1. Mude para modo real:
```yaml
mode: "real"
```

2. Configure API keys reais

3. Comece com 50 USDT apenas!

## ❓ FAQ Rápido

**P: Bot não faz nenhum trade?**
R: Normal! Espera condições ideais. Pode levar horas.

**P: Muitas perdas consecutivas?**
R: Circuit breaker vai parar. Revise estratégia.

**P: Erro de conexão?**
R: Verifique internet e API keys.

**P: Como sei se está funcionando?**
R: Dashboard atualiza a cada segundo = OK

**P: Posso fechar o terminal?**
R: Não! Use VPS para rodar 24/7.

## 🚨 Comandos de Emergência

```bash
# Ver logs em tempo real
tail -f logs/bot_20240110.log

# Backup do banco de dados
cp data/trading_bot.db data/backup_$(date +%Y%m%d).db

# Resetar tudo (CUIDADO!)
rm -rf data/ logs/
```

## 💡 Dicas de Ouro

1. **Paciência**: Melhor perder oportunidade que perder dinheiro
2. **Logs**: Leia os logs diariamente
3. **Testnet**: Mínimo 1 semana antes de real
4. **Capital**: Comece pequeno, aumente gradualmente
5. **Emoção**: Se estiver nervoso, pause o bot

---

🎉 **Parabéns!** Seu bot está rodando!

Lembre-se: Trading é maratona, não corrida de 100m. 🏃‍♂️