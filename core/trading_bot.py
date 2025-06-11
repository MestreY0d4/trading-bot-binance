"""
Core do Bot de Trading - Lógica Principal
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
import json

from core.executor import OrderExecutor
from core.risk_manager import RiskManager
from infrastructure.binance_api import BinanceClient
from infrastructure.indicators import TechnicalIndicators
from database.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)

class TradingBot:
    """Motor principal de trading"""
    
    def __init__(self, config: Dict, data_manager):
        self.config = config
        self.data_manager = data_manager
        self.db = DatabaseHandler(config['database']['path'])
        
        # Estado do bot
        self.running = False
        self.paused = False
        self.positions = {}  # {symbol: position_data}
        self.last_trades = {}  # {symbol: timestamp}
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.daily_trades = 0
        
        # Componentes
        self.client = None
        self.executor = None
        self.risk_manager = None
        self.indicators = TechnicalIndicators()
        
        # Cache de configuração para rastreabilidade
        self._config_hash = self._calculate_config_hash()
        
    def _calculate_config_hash(self) -> str:
        """Calcula hash da configuração atual"""
        config_str = json.dumps({
            'rsi_oversold': self.config['strategy']['rsi_oversold'],
            'rsi_overbought': self.config['strategy']['rsi_overbought'],
            'stop_loss': self.config['risk']['stop_loss_pct'],
            'take_profit': self.config['risk']['take_profit_pct']
        }, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    async def initialize(self):
        """Inicializa componentes do bot"""
        logger.info("Inicializando componentes do bot...")
        
        # Criar cliente Binance
        self.client = BinanceClient(self.config)
        await self.client.initialize()
        
        # Criar executor e risk manager
        self.executor = OrderExecutor(self.client, self.config)
        self.risk_manager = RiskManager(self.config)
        
        # Inicializar banco de dados
        self.db.initialize()
        
        # Carregar estado anterior se existir
        await self._load_state()
        
        logger.info("✅ Bot inicializado")
    
    async def run(self):
        """Loop principal de trading"""
        self.running = True
        logger.info("🚀 Bot de trading iniciado")
        
        while self.running:
            try:
                if not self.paused:
                    # Verificar horário de trading
                    if self._is_trading_hour():
                        await self._trading_cycle()
                    else:
                        logger.debug("Fora do horário de trading")
                
                await asyncio.sleep(10)  # Intervalo entre ciclos
                
            except Exception as e:
                logger.error(f"Erro no ciclo de trading: {e}", exc_info=True)
                await asyncio.sleep(30)
    
    async def _trading_cycle(self):
        """Ciclo de trading para todos os pares"""
        
        # Verificar circuit breakers
        if not self.risk_manager.check_circuit_breakers(
            self.consecutive_losses, 
            self.daily_pnl,
            await self._get_max_spread()
        ):
            logger.warning("⚠️ Circuit breaker ativado")
            self.paused = True
            return
        
        # Atualizar posições abertas
        await self._update_positions()
        
        # Analisar oportunidades em cada par
        for symbol in self.config['trading_pairs']:
            try:
                # Verificar cooldown
                if not self._check_cooldown(symbol):
                    continue
                
                # Verificar se já tem posição no par
                if symbol in self.positions:
                    await self._manage_position(symbol)
                else:
                    # Verificar limite de posições
                    if len(self.positions) < self.config['risk']['max_positions']:
                        await self._analyze_entry(symbol)
                        
            except Exception as e:
                logger.error(f"Erro ao processar {symbol}: {e}")
    
    async def _analyze_entry(self, symbol: str):
        """Analisa possível entrada"""
        
        # Obter dados atuais
        candles = await self.data_manager.get_latest_candles(symbol, limit=100)
        if candles is None or len(candles) < 50:
            return
        
        current_price = candles['close'].iloc[-1]
        
        # Calcular indicadores
        indicators = self.indicators.calculate_all(candles)
        
        # Verificar condições de COMPRA
        buy_signal = self._check_buy_conditions(indicators, current_price)
        
        # Verificar condições de VENDA (short - se implementado)
        # sell_signal = self._check_sell_conditions(indicators, current_price)
        
        if buy_signal:
            # Verificar spread
            spread = await self._get_spread(symbol)
            if spread > self.config['strategy']['max_spread']:
                logger.debug(f"Spread muito alto em {symbol}: {spread:.2%}")
                return
            
            # Calcular tamanho da posição
            position_size = self.risk_manager.calculate_position_size(
                self.get_available_balance(),
                current_price
            )
            
            if position_size < self.config['risk']['min_order_size']:
                logger.warning("Saldo insuficiente para nova posição")
                return
            
            # Executar ordem
            await self._execute_buy(symbol, position_size, indicators)
    
    def _check_buy_conditions(self, indicators: Dict, current_price: float) -> bool:
        """Verifica condições de compra"""
        
        rsi = indicators['rsi']
        bb_lower = indicators['bb_lower']
        bb_upper = indicators['bb_upper']
        bb_width = indicators['bb_width']
        ema = indicators['ema']
        volume_ratio = indicators['volume_ratio']
        
        # Condições AND (todas devem ser verdadeiras)
        conditions = [
            rsi < self.config['strategy']['rsi_oversold'],
            current_price < bb_lower,
            current_price > ema,  # Tendência de alta
            volume_ratio > self.config['strategy']['min_volume_ratio'],
            bb_width > self.config['strategy']['min_bb_width'],
            bb_width < self.config['strategy']['bb_squeeze_threshold']  # Não muito volátil
        ]
        
        # Log para debug
        if all(conditions[:-2]):  # Se quase todas condições OK
            logger.debug(f"Sinal parcial - RSI: {rsi:.1f}, BB: {(current_price-bb_lower)/(bb_upper-bb_lower):.2f}")
        
        return all(conditions)
    
    async def _execute_buy(self, symbol: str, size: float, indicators: Dict):
        """Executa ordem de compra"""
        logger.info(f"📈 Executando COMPRA em {symbol}")
        
        # Enviar ordem
        order = await self.executor.market_buy(symbol, size)
        if not order:
            return
        
        # Calcular stops
        entry_price = float(order['fills'][0]['price'])
        stop_loss = entry_price * (1 - self.config['risk']['stop_loss_pct'] / 100)
        take_profit = entry_price * (1 + self.config['risk']['take_profit_pct'] / 100)
        
        # Registrar posição
        position = {
            'symbol': symbol,
            'side': 'BUY',
            'entry_price': entry_price,
            'quantity': float(order['executedQty']),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': datetime.now(),
            'order_id': order['orderId'],
            'indicators_snapshot': indicators,
            'config_hash': self._config_hash
        }
        
        self.positions[symbol] = position
        self.last_trades[symbol] = datetime.now()
        
        # Salvar no banco
        self.db.save_trade({
            'timestamp': datetime.now(),
            'pair': symbol,
            'side': 'BUY',
            'entry_price': entry_price,
            'quantity': position['quantity'],
            'status': 'OPEN',
            'config_hash': self._config_hash,
            'indicators_snapshot': json.dumps(indicators)
        })
        
        logger.info(f"✅ Posição aberta: {symbol} @ {entry_price:.2f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
    
    async def _manage_position(self, symbol: str):
        """Gerencia posição aberta"""
        position = self.positions[symbol]
        current_price = await self.client.get_current_price(symbol)
        
        if not current_price:
            return
        
        pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
        
        # Verificar Stop Loss
        if current_price <= position['stop_loss']:
            logger.info(f"🛑 Stop Loss atingido em {symbol}")
            await self._close_position(symbol, current_price, 'stop_loss')
            self.consecutive_losses += 1
            
        # Verificar Take Profit
        elif current_price >= position['take_profit']:
            logger.info(f"🎯 Take Profit atingido em {symbol}")
            await self._close_position(symbol, current_price, 'take_profit')
            self.consecutive_losses = 0  # Reset
            
        # Quick exit se lucro rápido
        elif pnl_percent >= 1.0 and (datetime.now() - position['entry_time']).seconds < 900:
            logger.info(f"💨 Quick exit em {symbol} com +{pnl_percent:.1f}%")
            await self._close_position(symbol, current_price, 'quick_exit')
            self.consecutive_losses = 0
    
    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Fecha posição"""
        position = self.positions[symbol]
        
        # Executar ordem de venda
        order = await self.executor.market_sell(symbol, position['quantity'])
        if not order:
            logger.error(f"Falha ao fechar posição em {symbol}")
            return
        
        # Calcular P&L
        actual_exit_price = float(order['fills'][0]['price'])
        pnl = (actual_exit_price - position['entry_price']) * position['quantity']
        pnl_percent = ((actual_exit_price - position['entry_price']) / position['entry_price']) * 100
        
        # Considerar custos
        fees = position['quantity'] * position['entry_price'] * self.config['costs']['total_cost_pct'] / 100
        net_pnl = pnl - fees
        
        # Atualizar estado
        self.daily_pnl += net_pnl
        self.daily_trades += 1
        
        # Salvar trade completo
        self.db.update_trade({
            'order_id': position['order_id'],
            'exit_price': actual_exit_price,
            'exit_time': datetime.now(),
            'pnl': net_pnl,
            'pnl_percent': pnl_percent - self.config['costs']['total_cost_pct'],
            'fees': fees,
            'exit_reason': reason,
            'duration_minutes': (datetime.now() - position['entry_time']).seconds // 60
        })
        
        # Remover posição
        del self.positions[symbol]
        
        # Log resultado
        emoji = "✅" if net_pnl > 0 else "❌"
        logger.info(f"{emoji} Trade fechado: {symbol} | P&L: ${net_pnl:.2f} ({pnl_percent:.1f}%) | Motivo: {reason}")
    
    def _check_cooldown(self, symbol: str) -> bool:
        """Verifica se passou o cooldown desde último trade"""
        if symbol not in self.last_trades:
            return True
        
        cooldown = timedelta(seconds=self.config['strategy']['cooldown_seconds'])
        return datetime.now() - self.last_trades[symbol] > cooldown
    
    def _is_trading_hour(self) -> bool:
        """Verifica se está no horário de trading"""
        if not self.config['strategy']['trading_hours']['enabled']:
            return True
        
        current_hour = datetime.now().hour
        current_time = datetime.now().strftime("%H:%M")
        
        # Verificar horários a evitar
        for avoid_range in self.config['strategy']['trading_hours']['avoid_hours']:
            start, end = avoid_range.split('-')
            if start <= current_time <= end:
                return False
        
        return True
    
    async def _get_spread(self, symbol: str) -> float:
        """Calcula spread atual"""
        ticker = await self.client.get_ticker(symbol)
        if ticker:
            bid = float(ticker['bidPrice'])
            ask = float(ticker['askPrice'])
            return (ask - bid) / bid
        return 0.1  # Default alto se falhar
    
    async def _get_max_spread(self) -> float:
        """Obtém maior spread entre os pares"""
        max_spread = 0
        for symbol in self.config['trading_pairs']:
            spread = await self._get_spread(symbol)
            max_spread = max(max_spread, spread)
        return max_spread
    
    def get_available_balance(self) -> float:
        """Calcula saldo disponível para trading"""
        # Por simplicidade, assumindo saldo fixo
        # Em produção, buscar saldo real da API
        total_capital = 200.0
        used_capital = sum(
            pos['quantity'] * pos['entry_price'] 
            for pos in self.positions.values()
        )
        return total_capital * 0.75 - used_capital  # 75% para trading
    
    async def _update_positions(self):
        """Atualiza dados das posições abertas"""
        # Implementar se necessário
        pass
    
    async def _load_state(self):
        """Carrega estado anterior do bot"""
        # Implementar se necessário - carregar posições abertas do DB
        pass
    
    async def shutdown(self):
        """Encerra o bot graciosamente"""
        self.running = False
        
        # Fechar todas as posições se configurado
        if self.positions and self.config.get('close_on_shutdown', False):
            logger.warning("Fechando todas as posições...")
            for symbol in list(self.positions.keys()):
                await self._close_position(symbol, 0, 'shutdown')
        
        # Fechar conexões
        if self.client:
            await self.client.close()
        
        if self.db:
            self.db.close()
        
        logger.info("Bot encerrado")
    
    def get_status(self) -> Dict:
        """Retorna status atual do bot para o dashboard"""
        return {
            'running': self.running,
            'paused': self.paused,
            'positions': self.positions,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'consecutive_losses': self.consecutive_losses,
            'last_update': datetime.now()
        }
