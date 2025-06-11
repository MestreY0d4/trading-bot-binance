"""
Executor de Ordens - Execução rápida e confiável
"""
import logging
import asyncio
from typing import Dict, Optional
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger(__name__)

class OrderExecutor:
    """Responsável pela execução rápida de ordens"""
    
    def __init__(self, client, config: Dict):
        self.client = client
        self.config = config
        self.symbol_info = {}  # Cache de informações dos símbolos
        
    async def initialize(self):
        """Inicializa executor e carrega informações dos símbolos"""
        for symbol in self.config['trading_pairs']:
            info = await self.client.get_symbol_info(symbol)
            if info:
                self.symbol_info[symbol] = self._parse_symbol_info(info)
                
    def _parse_symbol_info(self, info: Dict) -> Dict:
        """Extrai informações relevantes do símbolo"""
        filters = {f['filterType']: f for f in info['filters']}
        
        return {
            'min_qty': float(filters['LOT_SIZE']['minQty']),
            'max_qty': float(filters['LOT_SIZE']['maxQty']),
            'step_size': float(filters['LOT_SIZE']['stepSize']),
            'min_notional': float(filters['MIN_NOTIONAL']['minNotional']),
            'price_precision': info['quotePrecision'],
            'qty_precision': info['baseAssetPrecision']
        }
    
    def _adjust_quantity(self, symbol: str, quantity: float) -> float:
        """Ajusta quantidade para os requisitos do símbolo"""
        if symbol not in self.symbol_info:
            logger.error(f"Informações do símbolo {symbol} não encontradas")
            return 0
        
        info = self.symbol_info[symbol]
        
        # Converter para Decimal para precisão
        qty = Decimal(str(quantity))
        step = Decimal(str(info['step_size']))
        
        # Arredondar para o step size
        qty = (qty // step) * step
        
        # Verificar limites
        qty = max(qty, Decimal(str(info['min_qty'])))
        qty = min(qty, Decimal(str(info['max_qty'])))
        
        return float(qty)
    
    async def market_buy(self, symbol: str, usdt_amount: float) -> Optional[Dict]:
        """Executa ordem de compra a mercado"""
        try:
            # Obter preço atual para calcular quantidade
            current_price = await self.client.get_current_price(symbol)
            if not current_price:
                logger.error(f"Não foi possível obter preço de {symbol}")
                return None
            
            # Calcular quantidade
            quantity = usdt_amount / current_price
            quantity = self._adjust_quantity(symbol, quantity)
            
            if quantity == 0:
                logger.error(f"Quantidade ajustada é zero para {symbol}")
                return None
            
            # Verificar valor mínimo (minNotional)
            notional = quantity * current_price
            min_notional = self.symbol_info[symbol]['min_notional']
            
            if notional < min_notional:
                logger.error(f"Valor abaixo do mínimo: ${notional:.2f} < ${min_notional}")
                return None
            
            # Executar ordem
            logger.info(f"Executando compra: {symbol} | Qtd: {quantity} | Valor: ${notional:.2f}")
            
            order = await self.client.place_order(
                symbol=symbol,
                side='BUY',
                order_type='MARKET',
                quantity=quantity
            )
            
            if order:
                logger.info(f"✅ Ordem executada: {order['orderId']}")
                return order
            else:
                logger.error("Falha ao executar ordem")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao executar compra: {e}", exc_info=True)
            return None
    
    async def market_sell(self, symbol: str, quantity: float) -> Optional[Dict]:
        """Executa ordem de venda a mercado"""
        try:
            # Ajustar quantidade
            quantity = self._adjust_quantity(symbol, quantity)
            
            if quantity == 0:
                logger.error(f"Quantidade ajustada é zero para {symbol}")
                return None
            
            # Executar ordem
            logger.info(f"Executando venda: {symbol} | Qtd: {quantity}")
            
            order = await self.client.place_order(
                symbol=symbol,
                side='SELL',
                order_type='MARKET',
                quantity=quantity
            )
            
            if order:
                logger.info(f"✅ Ordem de venda executada: {order['orderId']}")
                return order
            else:
                logger.error("Falha ao executar ordem de venda")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao executar venda: {e}", exc_info=True)
            return None
    
    async def limit_buy(self, symbol: str, price: float, usdt_amount: float) -> Optional[Dict]:
        """Executa ordem de compra limitada"""
        try:
            # Calcular quantidade
            quantity = usdt_amount / price
            quantity = self._adjust_quantity(symbol, quantity)
            
            if quantity == 0:
                return None
            
            # Ajustar preço para precisão
            precision = self.symbol_info[symbol]['price_precision']
            price = round(price, precision)
            
            # Executar ordem
            order = await self.client.place_order(
                symbol=symbol,
                side='BUY',
                order_type='LIMIT',
                price=price,
                quantity=quantity,
                time_in_force='GTC'  # Good Till Cancelled
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Erro ao executar ordem limitada: {e}")
            return None
    
    async def cancel_order(self, symbol: str, order_id: int) -> bool:
        """Cancela uma ordem"""
        try:
            result = await self.client.cancel_order(symbol, order_id)
            return result is not None
        except Exception as e:
            logger.error(f"Erro ao cancelar ordem: {e}")
            return False
    
    async def get_order_status(self, symbol: str, order_id: int) -> Optional[Dict]:
        """Verifica status de uma ordem"""
        try:
            return await self.client.get_order(symbol, order_id)
        except Exception as e:
            logger.error(f"Erro ao verificar ordem: {e}")
            return None
    
    def calculate_fees(self, order: Dict) -> float:
        """Calcula taxas totais de uma ordem executada"""
        if 'fills' not in order:
            return 0
        
        total_fee = 0
        for fill in order['fills']:
            # Assumir taxa em USDT ou converter
            fee = float(fill.get('commission', 0))
            # Se a taxa for em outra moeda, precisaria converter
            # Por simplicidade, assumindo USDT
            total_fee += fee
        
        return total_fee
