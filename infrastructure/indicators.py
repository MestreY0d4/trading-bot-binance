"""
Indicadores Técnicos - Implementação própria sem TA-Lib
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Calcula indicadores técnicos"""
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calcula RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0  # Valor neutro
        
        # Calcular mudanças de preço
        delta = prices.diff()
        
        # Separar ganhos e perdas
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calcular médias móveis
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        
        # Evitar divisão por zero
        rs = avg_gains / avg_losses.replace(0, 1e-10)
        
        # Calcular RSI
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1])
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calcula Bandas de Bollinger"""
        if len(prices) < period:
            mid = float(prices.iloc[-1])
            return {
                'upper': mid * 1.02,
                'middle': mid,
                'lower': mid * 0.98,
                'width': 0.04
            }
        
        # Calcular média móvel (banda do meio)
        middle = prices.rolling(window=period).mean()
        
        # Calcular desvio padrão
        std = prices.rolling(window=period).std()
        
        # Calcular bandas
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        # Calcular largura percentual
        width_pct = ((upper - lower) / middle * 100).iloc[-1]
        
        return {
            'upper': float(upper.iloc[-1]),
            'middle': float(middle.iloc[-1]),
            'lower': float(lower.iloc[-1]),
            'width': float(width_pct)
        }
    
    def calculate_ema(self, prices: pd.Series, period: int = 20) -> float:
        """Calcula Média Móvel Exponencial"""
        if len(prices) < period:
            return float(prices.iloc[-1])
        
        ema = prices.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])
    
    def calculate_volume_ratio(self, volumes: pd.Series, period: int = 20) -> float:
        """Calcula ratio do volume atual vs média"""
        if len(volumes) < period:
            return 1.0
        
        avg_volume = volumes.iloc[-period-1:-1].mean()
        current_volume = volumes.iloc[-1]
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def calculate_all(self, candles: pd.DataFrame) -> Dict[str, float]:
        """Calcula todos os indicadores de uma vez"""
        try:
            # Extrair séries necessárias
            close_prices = candles['close']
            volumes = candles['volume']
            
            # Calcular indicadores
            rsi = self.calculate_rsi(close_prices)
            bb = self.calculate_bollinger_bands(close_prices)
            ema = self.calculate_ema(close_prices)
            volume_ratio = self.calculate_volume_ratio(volumes)
            
            # Calcular indicadores adicionais
            current_price = float(close_prices.iloc[-1])
            
            # Posição relativa nas Bandas de Bollinger (0-1)
            bb_position = 0.5
            if bb['upper'] != bb['lower']:
                bb_position = (current_price - bb['lower']) / (bb['upper'] - bb['lower'])
            
            # Distância da EMA (%)
            ema_distance = ((current_price - ema) / ema) * 100
            
            # Momentum (mudança % nos últimos 5 candles)
            momentum = 0
            if len(close_prices) >= 5:
                momentum = ((current_price - close_prices.iloc[-5]) / close_prices.iloc[-5]) * 100
            
            # Volatilidade (desvio padrão dos últimos 20 candles)
            volatility = 0
            if len(close_prices) >= 20:
                volatility = (close_prices.iloc[-20:].std() / close_prices.iloc[-20:].mean()) * 100
            
            return {
                'rsi': rsi,
                'bb_upper': bb['upper'],
                'bb_middle': bb['middle'],
                'bb_lower': bb['lower'],
                'bb_width': bb['width'],
                'bb_position': bb_position,
                'ema': ema,
                'ema_distance': ema_distance,
                'volume_ratio': volume_ratio,
                'momentum': momentum,
                'volatility': volatility,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            return self._default_indicators()
    
    def _default_indicators(self) -> Dict[str, float]:
        """Retorna indicadores padrão em caso de erro"""
        return {
            'rsi': 50.0,
            'bb_upper': 0,
            'bb_middle': 0,
            'bb_lower': 0,
            'bb_width': 0,
            'bb_position': 0.5,
            'ema': 0,
            'ema_distance': 0,
            'volume_ratio': 1.0,
            'momentum': 0,
            'volatility': 0,
            'current_price': 0
        }
    
    def detect_bb_squeeze(self, bb_width: float, threshold: float = 0.8) -> bool:
        """Detecta compressão das Bandas de Bollinger"""
        return bb_width < threshold
    
    def detect_divergence(self, prices: pd.Series, rsi_values: pd.Series) -> Optional[str]:
        """Detecta divergências entre preço e RSI"""
        if len(prices) < 5 or len(rsi_values) < 5:
            return None
        
        # Simplificado: verificar apenas os últimos 5 pontos
        price_trend = prices.iloc[-1] > prices.iloc[-5]
        rsi_trend = rsi_values.iloc[-1] > rsi_values.iloc[-5]
        
        if price_trend and not rsi_trend:
            return "bearish_divergence"
        elif not price_trend and rsi_trend:
            return "bullish_divergence"
        
        return None