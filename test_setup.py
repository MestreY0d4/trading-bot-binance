#!/usr/bin/env python3
"""
Script de Teste - Verifica se tudo está configurado corretamente
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message: str, status: str = "info"):
    """Imprime mensagem colorida"""
    if status == "success":
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
    elif status == "error":
        print(f"{Colors.RED}✗{Colors.END} {message}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
    else:
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")

async def test_python_version():
    """Testa versão do Python"""
    print("\n1. Verificando versão do Python...")
    
    if sys.version_info < (3, 9):
        print_status(f"Python {sys.version} - Versão muito antiga! Requer 3.9+", "error")
        return False
    
    print_status(f"Python {sys.version.split()[0]} ✓", "success")
    return True

async def test_dependencies():
    """Testa se todas as dependências estão instaladas"""
    print("\n2. Verificando dependências...")
    
    required_packages = [
        'binance',
        'pandas',
        'numpy',
        'yaml',
        'websockets',
        'aiohttp',
        'rich',
        'keyboard'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print_status(f"{package} instalado", "success")
        except ImportError:
            print_status(f"{package} NÃO instalado", "error")
            missing.append(package)
    
    if missing:
        print_status(f"\nInstale os pacotes faltantes com:", "warning")
        print(f"pip install {' '.join(missing)}")
        return False
    
    return True

async def test_directory_structure():
    """Testa se a estrutura de diretórios está correta"""
    print("\n3. Verificando estrutura de diretórios...")
    
    required_dirs = [
        'core',
        'infrastructure',
        'config',
        'database',
        'interface',
        'backtest',
        'data',
        'logs'
    ]
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print_status(f"Diretório '{dir_name}' existe", "success")
        else:
            print_status(f"Criando diretório '{dir_name}'", "warning")
            os.makedirs(dir_name, exist_ok=True)
    
    return True

async def test_config_file():
    """Testa arquivo de configuração"""
    print("\n4. Verificando arquivo de configuração...")
    
    config_path = "config/settings.yaml"
    
    if not os.path.exists(config_path):
        print_status("settings.yaml não encontrado", "error")
        print_status("Criando arquivo padrão...", "warning")
        
        from config.config_loader import create_default_config
        create_default_config()
        return False
    
    # Tentar carregar
    try:
        from config.config_loader import load_config
        config = load_config()
        print_status("Configuração carregada com sucesso", "success")
        
        # Verificar API keys
        mode = config['mode']
        api_key = config['binance'].get(f'{mode}_api_key', '')
        
        if not api_key or 'YOUR_' in api_key:
            print_status(f"API keys para {mode} NÃO configuradas!", "error")
            print_status("Configure suas API keys em config/settings.yaml", "warning")
            return False
        else:
            print_status(f"API keys para {mode} configuradas", "success")
            
    except Exception as e:
        print_status(f"Erro ao carregar configuração: {e}", "error")
        return False
    
    return True

async def test_binance_connection():
    """Testa conexão com Binance"""
    print("\n5. Testando conexão com Binance...")
    
    try:
        from config.config_loader import load_config
        from infrastructure.binance_api import BinanceClient
        
        config = load_config()
        client = BinanceClient(config)
        
        print_status("Conectando...", "info")
        await client.initialize()
        
        # Testar obter preço
        price = await client.get_current_price('BTCUSDT')
        if price:
            print_status(f"Conexão OK! BTC/USDT: ${price:.2f}", "success")
        else:
            print_status("Erro ao obter preço", "error")
            return False
        
        await client.close()
        
    except Exception as e:
        print_status(f"Erro de conexão: {e}", "error")
        return False
    
    return True

async def test_indicators():
    """Testa cálculo de indicadores"""
    print("\n6. Testando indicadores técnicos...")
    
    try:
        from infrastructure.indicators import TechnicalIndicators
        import pandas as pd
        import numpy as np
        
        # Dados de teste
        prices = pd.Series(np.random.uniform(40000, 42000, 100))
        volumes = pd.Series(np.random.uniform(100, 200, 100))
        
        df = pd.DataFrame({
            'close': prices,
            'volume': volumes
        })
        
        indicators = TechnicalIndicators()
        result = indicators.calculate_all(df)
        
        if result['rsi'] > 0 and result['bb_upper'] > 0:
            print_status("RSI calculado: {:.2f}".format(result['rsi']), "success")
            print_status("Bollinger Bands calculadas", "success")
            print_status("Todos os indicadores OK", "success")
        else:
            print_status("Erro no cálculo dos indicadores", "error")
            return False
            
    except Exception as e:
        print_status(f"Erro: {e}", "error")
        return False
    
    return True

async def test_database():
    """Testa conexão com banco de dados"""
    print("\n7. Testando banco de dados...")
    
    try:
        from database.db_handler import DatabaseHandler
        
        db = DatabaseHandler('data/test.db')
        db.initialize()
        
        # Teste de escrita
        trade_id = db.save_trade({
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'entry_price': 42000,
            'quantity': 0.001,
            'timestamp': datetime.now()
        })
        
        if trade_id:
            print_status("Escrita no banco OK", "success")
        
        # Teste de leitura
        trades = db.get_trades(limit=1)
        if trades:
            print_status("Leitura do banco OK", "success")
        
        db.close()
        
        # Limpar teste
        os.remove('data/test.db')
        
    except Exception as e:
        print_status(f"Erro: {e}", "error")
        return False
    
    return True

async def main():
    """Executa todos os testes"""
    print("=" * 50)
    print("🔧 TESTE DE CONFIGURAÇÃO - BOT TRADING V5.1")
    print("=" * 50)
    
    tests = [
        ("Python", test_python_version()),
        ("Dependências", test_dependencies()),
        ("Diretórios", test_directory_structure()),
        ("Configuração", test_config_file()),
        ("Binance API", test_binance_connection()),
        ("Indicadores", test_indicators()),
        ("Banco de Dados", test_database())
    ]
    
    results = []
    for name, test in tests:
        try:
            result = await test
            results.append((name, result))
        except Exception as e:
            print_status(f"Erro no teste {name}: {e}", "error")
            results.append((name, False))
    
    # Resumo
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{name:.<30} {status}")
    
    print("-" * 50)
    print(f"Total: {passed}/{total} testes passaram")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 TUDO PRONTO! Você pode executar o bot com: python main.py{Colors.END}")
    else:
        print(f"\n{Colors.RED}❌ Corrija os problemas acima antes de executar o bot{Colors.END}")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário")
        sys.exit(1)
