"""
Gerenciador de Risco - Proteção do Capital
"""
import logging
from typing import Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskManager:
    """Gerencia riscos e protege o capital"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.risk_config = config['risk']
        self.daily_stats = {
            'start_time': datetime.now(),
            'total_loss': 0,
            'total_profit': 0,
            'trades': 0,
            'consecutive_losses': 0,
            'max_drawdown': 0,
            'peak_balance': 200.0  # Assumindo capital inicial
        }
    
    def check_circuit_breakers(self, consecutive_losses: int, daily_pnl: float, max_spread: float) -> bool:
        """Verifica todos os circuit breakers"""
        
        # 1. Limite de perdas consecutivas
        if consecutive_losses >= self.risk_config['max_consecutive_losses']:
            logger.warning(f"⚠️ Circuit Breaker: {consecutive_losses} perdas consecutivas")
            return False
        
        # 2. Limite de perda diária
        if daily_pnl <= -self.risk_config['daily_loss_limit']:
            logger.warning(f"⚠️ Circuit Breaker: Perda diária de ${daily_pnl:.2f}")
            return False
        
        # 3. Spread muito alto
        if max_spread >= self.risk_config['max_spread_pct'] / 100:
            logger.warning(f"⚠️ Circuit Breaker: Spread muito alto {max_spread:.2%}")
            return False
        
        return True
    
    def calculate_position_size(self, available_balance: float, current_price: float) -> float:
        """Calcula tamanho da posição com base no risco"""
        
        # Position size base (15% do capital disponível)
        base_size = available_balance * (self.risk_config['position_size_pct'] / 100)
        
        # Aplicar limites
        size = max(base_size, self.risk_config['position_size_min'])
        size = min(size, self.risk_config['position_size_max'])
        
        # Verificar se é suficiente
        if size < self.risk_config['min_order_size']:
            logger.warning(f"Position size ${size:.2f} abaixo do mínimo")
            return 0
        
        logger.debug(f"Position size calculado: ${size:.2f}")
        return size
    
    def calculate_stops(self, entry_price: float, side: str = 'BUY') -> Tuple[float, float]:
        """Calcula stop loss e take profit"""
        
        stop_loss_pct = self.risk_config['stop_loss_pct']
        take_profit_pct = self.risk_config['take_profit_pct']
        
        if side == 'BUY':
            stop_loss = entry_price * (1 - stop_loss_pct / 100)
            take_profit = entry_price * (1 + take_profit_pct / 100)
        else:  # SELL/SHORT
            stop_loss = entry_price * (1 + stop_loss_pct / 100)
            take_profit = entry_price * (1 - take_profit_pct / 100)
        
        return stop_loss, take_profit
    
    def update_daily_stats(self, trade_result: Dict):
        """Atualiza estatísticas diárias"""
        pnl = trade_result.get('pnl', 0)
        
        if pnl > 0:
            self.daily_stats['total_profit'] += pnl
            self.daily_stats['consecutive_losses'] = 0
        else:
            self.daily_stats['total_loss'] += abs(pnl)
            self.daily_stats['consecutive_losses'] += 1
        
        self.daily_stats['trades'] += 1
        
        # Calcular drawdown
        current_balance = 200 + self.daily_stats['total_profit'] - self.daily_stats['total_loss']
        if current_balance > self.daily_stats['peak_balance']:
            self.daily_stats['peak_balance'] = current_balance
        
        drawdown = (self.daily_stats['peak_balance'] - current_balance) / self.daily_stats['peak_balance']
        self.daily_stats['max_drawdown'] = max(self.daily_stats['max_drawdown'], drawdown)
    
    def should_trade(self, symbol: str, signal_strength: float = 1.0) -> bool:
        """Verifica se deve executar trade baseado em condições de risco"""
        
        # Verificar se excedeu limite diário de trades
        # (não implementado no config, mas útil)
        
        # Verificar correlação entre posições
        # (simplificado por enquanto)
        
        # Verificar força do sinal
        if signal_strength < 0.7:  # Threshold arbitrário
            return False
        
        return True
    
    def get_risk_metrics(self) -> Dict:
        """Retorna métricas de risco atuais"""
        net_pnl = self.daily_stats['total_profit'] - self.daily_stats['total_loss']
        win_rate = 0
        
        if self.daily_stats['trades'] > 0:
            wins = self.daily_stats['trades'] - self.daily_stats.get('losses', 0)
            win_rate = wins / self.daily_stats['trades']
        
        return {
            'daily_pnl': net_pnl,
            'max_drawdown': self.daily_stats['max_drawdown'],
            'consecutive_losses': self.daily_stats['consecutive_losses'],
            'total_trades': self.daily_stats['trades'],
            'win_rate': win_rate,
            'risk_status': 'OK' if net_pnl > -self.risk_config['daily_loss_limit'] * 0.8 else 'WARNING'
        }
    
    def reset_daily_stats(self):
        """Reseta estatísticas diárias"""
        self.daily_stats = {
            'start_time': datetime.now(),
            'total_loss': 0,
            'total_profit': 0,
            'trades': 0,
            'consecutive_losses': 0,
            'max_drawdown': 0,
            'peak_balance': self.daily_stats.get('peak_balance', 200.0)
        }
        logger.info("Estatísticas diárias resetadas")
    
    def validate_order(self, symbol: str, side: str, quantity: float, price: float) -> bool:
        """Valida ordem antes de enviar"""
        
        # Verificar valor mínimo
        notional = quantity * price
        if notional < self.risk_config['min_order_size']:
            logger.warning(f"Ordem abaixo do valor mínimo: ${notional:.2f}")
            return False
        
        # Verificar se não excede limites de exposição
        # (implementar se necessário)
        
        return True
    
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calcula fração ótima de Kelly para position sizing"""
        if avg_loss == 0:
            return 0
        
        # Kelly % = (p * b - q) / b
        # p = probabilidade de ganho
        # q = probabilidade de perda
        # b = ratio ganho/perda
        
        p = win_rate
        q = 1 - win_rate
        b = avg_win / avg_loss
        
        kelly = (p * b - q) / b
        
        # Aplicar fração de Kelly (25% do valor total por segurança)
        kelly_fraction = 0.25
        optimal_size = kelly * kelly_fraction
        
        # Limitar entre 5% e 25%
        return max(0.05, min(0.25, optimal_size))
