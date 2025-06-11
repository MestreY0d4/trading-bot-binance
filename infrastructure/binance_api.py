"""
Cliente Binance - API REST + WebSocket
"""
import logging
import asyncio
import json
import time
from typing import Dict, Optional, List, Callable
from datetime import datetime
import aiohttp
import websockets
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

class BinanceClient:
    """Cliente unificado para Binance API e WebSocket"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.mode = config['mode']
        self.binance_config = config['binance']
        
        # Cliente REST
        self.client = None
        
        # WebSocket
        self.ws_connections = {}
        self.ws_callbacks = {}
        self.ws_running = False
        self.use_rest_fallback = False
        self.reconnect_attempts = 0
        
        # Cache de dados
        self.price_cache = {}
        self.ticker_cache = {}
        
        # URLs
        if self.mode == 'testnet':
            self.rest_url = self.binance_config['testnet_base_url']
            self.ws_url = "wss://testnet.binance.vision/ws"
        else:
            self.rest_url = self.binance_config['real_base_url']
            self.ws_url = "wss://stream.binance.com:9443/ws"
    
    async def initialize(self):
        """Inicializa cliente e conexões"""
        try:
            # Criar cliente REST
            api_key = self.binance_config[f'{self.mode}_api_key']
            api_secret = self.binance_config[f'{self.mode}_api_secret']
            
            self.client = await AsyncClient.create(
                api_key=api_key,
                api_secret=api_secret,
                testnet=self.mode == 'testnet'
            )
            
            logger.info(f"✅ Cliente Binance inicializado em modo {self.mode.upper()}")
            
            # Iniciar WebSocket
            await self._start_websocket()
            
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Binance: {e}")
            raise
    
    async def _start_websocket(self):
        """Inicia conexões WebSocket"""
        self.ws_running = True
        
        # Criar streams para cada par
        for symbol in self.config['trading_pairs']:
            asyncio.create_task(self._ws_connect(symbol))
    
    async def _ws_connect(self, symbol: str):
        """Conecta WebSocket para um símbolo com reconexão robusta"""
        stream_name = f"{symbol.lower()}@ticker"
        url = f"{self.ws_url}/{stream_name}"
        
        while self.ws_running:
            try:
                async with websockets.connect(url) as ws:
                    self.ws_connections[symbol] = ws
                    self.reconnect_attempts = 0
                    logger.info(f"✅ WebSocket conectado para {symbol}")
                    
                    # Loop de recepção
                    while self.ws_running:
                        try:
                            msg = await asyncio.wait_for(
                                ws.recv(), 
                                timeout=self.binance_config['ws_keepalive_interval']
                            )
                            
                            data = json.loads(msg)
                            await self._process_ws_message(symbol, data)
                            
                        except asyncio.TimeoutError:
                            # Enviar ping
                            await ws.ping()
                            
                        except websockets.ConnectionClosed:
                            logger.warning(f"WebSocket {symbol} desconectado")
                            break
                            
            except Exception as e:
                logger.error(f"Erro WebSocket {symbol}: {e}")
                
                # Backoff exponencial para reconexão
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= self.binance_config['ws_max_reconnect_attempts']:
                    logger.error(f"❌ Máximo de tentativas excedido para {symbol}. Usando REST API.")
                    self.use_rest_fallback = True
                    break
                
                wait_time = min(2 ** self.reconnect_attempts, 32)
                logger.info(f"Reconectando {symbol} em {wait_time}s...")
                await asyncio.sleep(wait_time)
    
    async def _process_ws_message(self, symbol: str, data: Dict):
        """Processa mensagem do WebSocket"""
        # Atualizar cache
        if 'c' in data:  # Current price
            self.price_cache[symbol] = {
                'price': float(data['c']),
                'timestamp': datetime.now()
            }
        
        # Atualizar ticker completo
        self.ticker_cache[symbol] = {
            'bid': float(data['b']),
            'ask': float(data['a']),
            'last': float(data['c']),
            'volume': float(data['v']),
            'timestamp': datetime.now()
        }
        
        # Chamar callbacks se existirem
        if symbol in self.ws_callbacks:
            await self.ws_callbacks[symbol](data)
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Obtém preço atual (WebSocket primeiro, REST como fallback)"""
        
        # Tentar cache do WebSocket primeiro
        if symbol in self.price_cache:
            cache_data = self.price_cache[symbol]
            # Verificar se não está muito antigo (5 segundos)
            if (datetime.now() - cache_data['timestamp']).seconds < 5:
                return cache_data['price']
        
        # Fallback para REST API
        if self.use_rest_fallback or symbol not in self.price_cache:
            try:
                ticker = await self.client.get_symbol_ticker(symbol=symbol)
                price = float(ticker['price'])
                
                # Atualizar cache
                self.price_cache[symbol] = {
                    'price': price,
                    'timestamp': datetime.now()
                }
                
                return price
                
            except Exception as e:
                logger.error(f"Erro ao obter preço de {symbol}: {e}")
                return None
        
        return None
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Obtém ticker completo"""
        # Tentar cache primeiro
        if symbol in self.ticker_cache:
            cache_data = self.ticker_cache[symbol]
            if (datetime.now() - cache_data['timestamp']).seconds < 5:
                return cache_data
        
        # Fallback para REST
        try:
            ticker = await self.client.get_ticker(symbol=symbol)
            return {
                'bid': float(ticker['bidPrice']),
                'ask': float(ticker['askPrice']),
                'last': float(ticker['lastPrice']),
                'volume': float(ticker['volume'])
            }
        except Exception as e:
            logger.error(f"Erro ao obter ticker: {e}")
            return None
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> Optional[List]:
        """Obtém candles históricos"""
        try:
            klines = await self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return klines
        except Exception as e:
            logger.error(f"Erro ao obter klines: {e}")
            return None
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Obtém informações do símbolo"""
        try:
            info = await self.client.get_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    return s
            return None
        except Exception as e:
            logger.error(f"Erro ao obter info do símbolo: {e}")
            return None
    
    async def place_order(self, **params) -> Optional[Dict]:
        """Coloca uma ordem"""
        try:
            # Log para debug
            logger.debug(f"Enviando ordem: {params}")
            
            # Criar ordem
            if params['order_type'] == 'MARKET':
                order = await self.client.create_order(
                    symbol=params['symbol'],
                    side=params['side'],
                    type=params['order_type'],
                    quantity=params['quantity']
                )
            else:  # LIMIT
                order = await self.client.create_order(
                    symbol=params['symbol'],
                    side=params['side'],
                    type=params['order_type'],
                    quantity=params['quantity'],
                    price=params['price'],
                    timeInForce=params.get('time_in_force', 'GTC')
                )
            
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Erro Binance API: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Erro ao criar ordem: {e}")
            return None
    
    async def cancel_order(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Cancela uma ordem"""
        try:
            result = await self.client.cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            return result
        except Exception as e:
            logger.error(f"Erro ao cancelar ordem: {e}")
            return None
    
    async def get_order(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Obtém status de uma ordem"""
        try:
            order = await self.client.get_order(
                symbol=symbol,
                orderId=order_id
            )
            return order
        except Exception as e:
            logger.error(f"Erro ao buscar ordem: {e}")
            return None
    
    async def get_account_balance(self) -> Optional[Dict]:
        """Obtém saldo da conta"""
        try:
            account = await self.client.get_account()
            balances = {}
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                
                if free > 0 or locked > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    }
            
            return balances
            
        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            return None
    
    def subscribe_price_updates(self, symbol: str, callback: Callable):
        """Inscreve callback para atualizações de preço"""
        self.ws_callbacks[symbol] = callback
    
    async def ensure_connection(self):
        """Garante que as conexões estão ativas"""
        if self.use_rest_fallback:
            logger.info("Usando REST API (WebSocket indisponível)")
            return True
        
        # Verificar conexões WebSocket
        all_connected = all(
            symbol in self.ws_connections and not self.ws_connections[symbol].closed
            for symbol in self.config['trading_pairs']
        )
        
        if not all_connected:
            logger.warning("Reconectando WebSockets...")
            await self._start_websocket()
        
        return True
    
    async def close(self):
        """Fecha todas as conexões"""
        self.ws_running = False
        
        # Fechar WebSockets
        for symbol, ws in self.ws_connections.items():
            if ws and not ws.closed:
                await ws.close()
        
        # Fechar cliente REST
        if self.client:
            await self.client.close_connection()
        
        logger.info("Conexões Binance fechadas")
