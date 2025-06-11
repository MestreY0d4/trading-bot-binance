# 🔑 Guia de Configuração - API Binance

Este guia mostra como obter suas API keys para usar o bot.

## 📌 Testnet (Recomendado para Começar)

### 1. Acesse o Binance Testnet

Vá para: https://testnet.binance.vision/

### 2. Crie uma conta

- Clique em "Register"
- Use um email válido
- Crie uma senha forte

### 3. Faça login e vá para API Management

- Após login, clique no ícone do usuário
- Selecione "API Management"

### 4. Crie uma nova API Key

- Clique em "Create API"
- Dê um nome (ex: "TradingBot")
- Complete a verificação

### 5. Salve suas credenciais

⚠️ **IMPORTANTE**: Salve imediatamente! O Secret só aparece uma vez!

```
API Key: xxxxxxxxxxxxxxxxxxxxxx
API Secret: yyyyyyyyyyyyyyyyyyyyyy
```

### 6. Configure as permissões

- ✅ Enable Reading
- ✅ Enable Spot & Margin Trading
- ❌ Enable Withdrawals (não necessário)

### 7. Obtenha fundos de teste

No testnet, você recebe fundos virtuais automaticamente:
- 10,000 USDT
- 1 BTC
- 100 ETH
- etc.

## 🔴 Conta Real (Após Validar no Testnet)

### ⚠️ AVISOS IMPORTANTES:

1. **Só use conta real após testar extensivamente no testnet**
2. **Comece com valores pequenos (50-100 USDT)**
3. **NUNCA compartilhe suas API keys**
4. **NUNCA habilite saques na API**

### Passos para Conta Real:

1. Acesse: https://www.binance.com/
2. Faça login na sua conta
3. Vá em "API Management"
4. Siga os mesmos passos do testnet
5. **Adicione restrição de IP** (recomendado)

### Configurar Restrição de IP:

1. Descubra seu IP: https://whatismyipaddress.com/
2. Na configuração da API, adicione seu IP
3. Isso impede uso da API de outros locais

## 🔐 Segurança

### Boas Práticas:

1. **Use variáveis de ambiente** em vez de hardcode:
   ```bash
   export BINANCE_REAL_API_KEY=sua_key
   export BINANCE_REAL_API_SECRET=seu_secret
   ```

2. **Crie arquivo `.env`** (adicione ao .gitignore!):
   ```
   BINANCE_TESTNET_API_KEY=xxx
   BINANCE_TESTNET_API_SECRET=yyy
   BINANCE_REAL_API_KEY=aaa
   BINANCE_REAL_API_SECRET=bbb
   ```

3. **Permissões mínimas**:
   - ✅ Leitura
   - ✅ Trading Spot
   - ❌ Saques
   - ❌ Trading Futuros
   - ❌ Trading Margem

4. **2FA obrigatório** na conta Binance

## 🧪 Testando a Conexão

Após configurar, teste com este script:

```python
import asyncio
from binance.client import AsyncClient

async def test_connection():
    client = await AsyncClient.create(
        api_key='SUA_API_KEY',
        api_secret='SEU_SECRET',
        testnet=True  # False para produção
    )
    
    # Testar conexão
    try:
        account = await client.get_account()
        print("✅ Conexão OK!")
        print(f"Saldos encontrados: {len(account['balances'])}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    await client.close_connection()

# Rodar teste
asyncio.run(test_connection())
```

## 🆘 Problemas Comuns

### "Invalid API-key, IP, or permissions"
- Verifique se copiou a key corretamente
- Confirme se está usando testnet/real correto
- Verifique restrições de IP

### "Signature for this request is not valid"
- Secret está incorreto
- Verifique espaços extras ao copiar/colar

### "Insufficient balance"
- No testnet: Aguarde alguns minutos para fundos aparecerem
- No real: Deposite USDT na conta spot

### "Too many requests"
- Aguarde 1 minuto
- Reduza frequência de requests

## 📞 Suporte Binance

- Testnet: Sem suporte oficial (é ambiente de testes)
- Produção: https://www.binance.com/pt-BR/support

---

⚠️ **Lembre-se**: NUNCA compartilhe suas API keys com ninguém!