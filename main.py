#!/usr/bin/env python3
"""
Bot de Trading Binance V5.1
Ponto de entrada principal
"""
import asyncio
import signal
import sys
import logging
from datetime import datetime
from pathlib import Path

# Criar diretórios necessários
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Imports dos módulos
from core.trading_bot import TradingBot
from interface.simple_dashboard import Dashboard
from infrastructure.data_manager import DataManager
from config.config_loader import load_config

class BotManager:
    """Gerenciador principal do bot"""
    
    def __init__(self):
        self.bot = None
        self.dashboard = None
        self.running = False
        self.config = None
        
    async def initialize(self):
        """Inicializa todos os componentes"""
        try:
            logger.info("=== INICIANDO BOT DE TRADING V5.1 ===")
            
            # Carregar configurações
            self.config = load_config()
            logger.info(f"Modo: {self.config['mode'].upper()}")
            
            # Inicializar gerenciador de dados
            logger.info("Baixando dados históricos...")
            data_manager = DataManager(self.config)
            await data_manager.initialize()
            
            # Criar bot de trading
            self.bot = TradingBot(self.config, data_manager)
            await self.bot.initialize()
            
            # Criar dashboard
            self.dashboard = Dashboard(self.bot)
            
            logger.info("✅ Bot inicializado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar: {e}")
            return False
    
    async def start(self):
        """Inicia o bot e dashboard"""
        if not await self.initialize():
            return
        
        self.running = True
        
        # Configurar sinais para shutdown gracioso
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)
        
        # Criar tasks assíncronas
        tasks = [
            asyncio.create_task(self.bot.run()),
            asyncio.create_task(self.dashboard.run()),
            asyncio.create_task(self._monitor_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Bot interrompido pelo usuário")
        finally:
            await self.shutdown()
    
    async def _monitor_loop(self):
        """Loop de monitoramento principal"""
        while self.running:
            await asyncio.sleep(1)
            
            # Verificar comandos do dashboard
            if self.dashboard.should_stop:
                self.running = False
                break
            
            if self.dashboard.trading_paused != self.bot.paused:
                self.bot.paused = self.dashboard.trading_paused
                logger.info(f"Trading {'pausado' if self.bot.paused else 'resumido'}")
    
    def _signal_handler(self, signum, frame):
        """Manipula sinais do sistema"""
        logger.info(f"Sinal {signum} recebido, encerrando...")
        self.running = False
    
    async def shutdown(self):
        """Encerra o bot graciosamente"""
        logger.info("Encerrando bot...")
        
        if self.bot:
            await self.bot.shutdown()
        
        if self.dashboard:
            await self.dashboard.shutdown()
        
        logger.info("✅ Bot encerrado com segurança")

async def main():
    """Função principal"""
    manager = BotManager()
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
    finally:
        sys.exit(0)

if __name__ == "__main__":
    # Verificar Python 3.9+
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ é necessário!")
        sys.exit(1)
    
    # Rodar bot
    asyncio.run(main())
