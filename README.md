# Bot de Trading Binance V5.1

Bot automatizado de day trading para Binance com foco em simplicidade e eficácia.

## 🚀 Características

- **Trading automatizado** com estratégia RSI + Bollinger Bands + EMA
- **WebSocket** para execução em tempo real com latência mínima
- **Gestão de risco** com stop loss/take profit automáticos
- **Backtest integrado** para validação antes de operar
- **Dashboard minimalista** no terminal
- **Otimização semanal** automática de parâmetros
- **Circuit breakers** para proteção do capital

## 📋 Requisitos

- Python 3.9 ou superior
- Conta na Binance (Testnet para testes)
- 200 USDT de capital inicial (recomendado)
- Sistema operacional: Windows, Linux ou macOS

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/trading-bot-binance.git
cd trading-bot-binance
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as API Keys

#### Opção 1: Editar o arquivo de configuração

Edite o arquivo `config/settings.yaml`:

```yaml
binance:
  testnet_api_key: "SUA_API_KEY_TESTNET"
  testnet_api_secret: "SEU_API_SECRET_TESTNET"
```

#### Opção 2: Usar variáveis de ambiente (recomendado)

```bash
# Windows
set BINANCE_TESTNET_API_KEY=sua_key_aqui
set BINANCE_TESTNET_API_SECRET=seu_secret_aqui

# Linux/Mac
export BINANCE_TESTNET_API_KEY=sua_key_aqui
export BINANCE_TESTNET_API_SECRET=seu_secret_aqui
```

## 🏃 Como Usar

### 1. Primeira execução (Testnet)

```bash
python main.py
```

O bot irá:
1. Baixar dados históricos (2-3 minutos)
2. Executar backtest inicial
3. Abrir o dashboard
4. Aguardar comando para iniciar trading

### 2. Controles do Dashboard

- **P** - Pausar/Retomar trading
- **S** - Parar bot
- **R** - Ver relatório diário
- **F5** - Atualizar dashboard

### 3. Fluxo de Trabalho Recomendado

#### Semana 1: Validação no Testnet
- Deixe o bot rodar 3-5 dias no testnet
- Monitore win rate e performance
- Ajuste parâmetros se necessário

#### Semana 2: Início em Produção
- Mude para modo real com 50 USDT (25%)
- Configure no `settings.yaml`:
```yaml
mode: "real"
```

#### Semana 3+: Escala Gradual
- Se lucrativo, aumente para 100 USDT
- Máximo recomendado: 150 USDT (75% do capital)

## ⚙️ Configuração

### Principais Parâmetros

```yaml
# Estratégia
strategy:
  rsi_oversold: 32        # Compra quando RSI < 32
  rsi_overbought: 68      # Venda quando RSI > 68
  timeframe: "5m"         # Timeframe dos candles

# Gestão de Risco
risk:
  position_size_pct: 15   # 15% do capital por trade
  stop_loss_pct: 1.5      # Stop loss em -1.5%
  take_profit_pct: 2.5    # Take profit em +2.5%
  max_positions: 2        # Máximo 2 posições simultâneas
```

### Horários de Trading

O bot evita horários de baixa liquidez:
- **Evita**: 00:00-02:00 e 12:00-13:00 UTC
- **Melhor**: 14:00-20:00 UTC (overlap Europa/USA)

## 📊 Estratégia

### Condições de Entrada (COMPRA)

Todas as condições devem ser verdadeiras:
1. RSI < 32 (sobrevenda)
2. Preço < Banda Inferior de Bollinger
3. Preço > EMA 20 (tendência de alta)
4. Volume > 50% da média
5. Largura das Bandas > 0.8%

### Gestão de Posição

- **Stop Loss**: -1.5% fixo
- **Take Profit**: +2.5% fixo
- **Position Size**: 15% do capital (30 USDT com 200 USDT)
- **Cooldown**: 5 minutos entre trades no mesmo par

## 🛡️ Proteções (Circuit Breakers)

O bot para automaticamente se:
- 3 perdas consecutivas
- Perda diária > 15 USDT (7.5%)
- Spread > 0.3%
- Falha de conexão com API

## 📈 Metas Realistas

- **Diária**: 1.5% (3 USDT)
- **Semanal**: 8% (16 USDT)
- **Mensal**: 25% (50 USDT)

**Importante**: Estas são metas, não garantias. Trading envolve riscos.

## 🔍 Monitoramento

### Dashboard em Tempo Real

```
╔═══════════════════════════════════════════════════╗
║ BOT TRADING V5.1 [Testnet] [●] Conectado         ║
╠═══════════════════════════════════════════════════╣
║ Capital: 200 USDT | P&L Hoje: +2.8% (+5.6 USD)   ║
║                                                   ║
║ [▶️ INICIAR] [⏸️ PAUSAR] [⏹️ PARAR] [📊 RELATÓRIO] ║
║                                                   ║
║ Posições Abertas: 1/2                             ║
║ • BTC: Long 42,150 | P&L: +1.2%                  ║
╚═══════════════════════════════════════════════════╝
```

### Logs

Os logs são salvos em:
- `logs/bot_YYYYMMDD.log` - Log diário
- `data/trading_bot.db` - Banco de dados SQLite

## 🔧 Troubleshooting

### Erro: "API key não configurada"
- Verifique se configurou as API keys corretamente
- Para testnet: https://testnet.binance.vision/

### Erro: "Insufficient balance"
- Verifique saldo na conta
- Reduza `position_size_pct` se necessário

### Bot não encontra sinais
- Normal em mercados laterais
- Aguarde condições favoráveis
- Não force trades

## ⚠️ Avisos Importantes

1. **Comece no TESTNET** - Sempre teste antes de usar dinheiro real
2. **Capital de risco** - Só use dinheiro que pode perder
3. **Monitore sempre** - Não deixe o bot sem supervisão
4. **Mercado volátil** - Criptomoedas são altamente voláteis
5. **Sem garantias** - Lucros passados não garantem lucros futuros

## 📝 Estrutura do Projeto

```
trading_bot/
├── core/                  # Lógica principal
├── infrastructure/        # APIs e indicadores
├── config/               # Configurações
├── database/             # Persistência
├── interface/            # Dashboard
├── backtest/             # Validação
├── logs/                 # Arquivos de log
├── data/                 # Banco de dados
├── main.py               # Ponto de entrada
└── requirements.txt      # Dependências
```

## 🤝 Suporte

Para dúvidas ou problemas:
1. Verifique os logs em `logs/`
2. Consulte a documentação
3. Abra uma issue no GitHub

## 📜 Licença

Este projeto é fornecido "como está", sem garantias. Use por sua conta e risco.

---

**Lembre-se**: Trading é arriscado. Nunca invista mais do que pode perder. 🚨