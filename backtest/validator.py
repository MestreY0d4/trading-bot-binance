"""
Sistema de Backtest e Validação
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

logger = logging.getLogger(__name__)

class BacktestValidator:
    """Sistema de backtest e otimização semanal"""
    
    def __init__(self, config: Dict, data_manager, indicators):
        self.config = config
        self.data_manager = data_manager
        self.indicators = indicators
        
        # Parâmetros de validação
        self.validation_config = config['validation']
        self.optimization_config = config['optimization']
        
        # Resultados
        self.results = []
        self.best_params = None
        
    async def run_backtest(self, symbol: str, params: Dict = None) -> Dict:
        """Executa backtest com parâmetros específicos"""
        
        # Usar parâmetros padrão se não fornecidos
        if params is None:
            params = self._get_default_params()
        
        # Obter dados históricos
        candles = await self.data_manager.get_latest_candles(symbol, limit=1000)
        if candles is None or len(candles) < 100:
            logger.error(f"Dados insuficientes para backtest de {symbol}")
            return None
        
        # Simular trades
        trades = self._simulate_trades(candles, params)
        
        # Calcular métricas
        metrics = self._calculate_metrics(trades)
        
        return {
            'symbol': symbol,
            'params': params,
            'trades': trades,
            'metrics': metrics
        }
    
    def _simulate_trades(self, candles: pd.DataFrame, params: Dict) -> List[Dict]:
        """Simula trades baseado nos dados históricos"""
        trades = []
        position = None
        
        for i in range(50, len(candles)):
            # Pegar janela de dados
            window = candles.iloc[i-50:i+1]
            current_candle = candles.iloc[i]
            
            # Calcular indicadores
            indicators = self.indicators.calculate_all(window)
            
            # Se não tem posição, verificar entrada
            if position is None:
                if self._check_entry_conditions(indicators, current_candle, params):
                    position = {
                        'entry_time': current_candle.name,
                        'entry_price': current_candle['close'],
                        'stop_loss': current_candle['close'] * (1 - params['stop_loss_pct'] / 100),
                        'take_profit': current_candle['close'] * (1 + params['take_profit_pct'] / 100)
                    }
            
            # Se tem posição, verificar saída
            else:
                exit_price = None
                exit_reason = None
                
                # Verificar stop loss
                if current_candle['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'stop_loss'
                
                # Verificar take profit
                elif current_candle['high'] >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'take_profit'
                
                if exit_price:
                    # Calcular P&L
                    pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    pnl_pct -= self.config['costs']['total_cost_pct']  # Deduzir custos
                    
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': current_candle.name,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl_percent': pnl_pct,
                        'exit_reason': exit_reason,
                        'duration_minutes': (current_candle.name - position['entry_time']).seconds // 60
                    }
                    
                    trades.append(trade)
                    position = None
        
        return trades
    
    def _check_entry_conditions(self, indicators: Dict, candle: pd.Series, params: Dict) -> bool:
        """Verifica condições de entrada baseado nos parâmetros"""
        
        # Condições de compra
        conditions = [
            indicators['rsi'] < params['rsi_oversold'],
            candle['close'] < indicators['bb_lower'],
            candle['close'] > indicators['ema'],
            indicators['volume_ratio'] > self.config['strategy']['min_volume_ratio'],
            indicators['bb_width'] > self.config['strategy']['min_bb_width']
        ]
        
        return all(conditions)
    
    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """Calcula métricas de performance"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'expectancy': 0
            }
        
        # Converter para DataFrame
        df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_trades = len(trades)
        winning_trades = len(df[df['pnl_percent'] > 0])
        losing_trades = len(df[df['pnl_percent'] < 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Profit factor
        total_profit = df[df['pnl_percent'] > 0]['pnl_percent'].sum()
        total_loss = abs(df[df['pnl_percent'] < 0]['pnl_percent'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Médias
        avg_profit = df[df['pnl_percent'] > 0]['pnl_percent'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl_percent'] < 0]['pnl_percent'].mean() if losing_trades > 0 else 0
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_profit) + ((100 - win_rate) / 100 * avg_loss)
        
        # Drawdown
        cumulative_returns = (1 + df['pnl_percent'] / 100).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = ((cumulative_returns - running_max) / running_max).min() * 100
        
        # Sharpe Ratio (simplificado)
        returns = df['pnl_percent']
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': abs(drawdown),
            'sharpe_ratio': sharpe,
            'expectancy': expectancy,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades
        }
    
    async def optimize_parameters(self) -> Dict:
        """Otimiza parâmetros testando múltiplas combinações"""
        logger.info("🔧 Iniciando otimização de parâmetros...")
        
        # Parâmetros para otimizar
        param_grid = self.optimization_config['optimize_params']
        
        # Gerar todas as combinações
        combinations = self._generate_param_combinations(param_grid)
        logger.info(f"Testando {len(combinations)} combinações...")
        
        best_score = -float('inf')
        best_params = None
        
        # Testar cada combinação
        for i, params in enumerate(combinations):
            # Merge com parâmetros padrão
            test_params = self._get_default_params()
            test_params.update(params)
            
            # Rodar backtest para cada símbolo
            total_score = 0
            for symbol in self.config['trading_pairs']:
                result = await self.run_backtest(symbol, test_params)
                if result:
                    # Score baseado em múltiplas métricas
                    score = self._calculate_optimization_score(result['metrics'])
                    total_score += score
            
            # Verificar se é melhor
            avg_score = total_score / len(self.config['trading_pairs'])
            if avg_score > best_score:
                best_score = avg_score
                best_params = test_params
                logger.info(f"Nova melhor configuração encontrada! Score: {avg_score:.2f}")
        
        self.best_params = best_params
        return best_params
    
    def _generate_param_combinations(self, param_grid: Dict) -> List[Dict]:
        """Gera todas as combinações de parâmetros"""
        import itertools
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        combinations = []
        for combination in itertools.product(*values):
            combinations.append(dict(zip(keys, combination)))
        
        return combinations
    
    def _calculate_optimization_score(self, metrics: Dict) -> float:
        """Calcula score de otimização baseado em múltiplas métricas"""
        # Pesos para cada métrica
        weights = {
            'win_rate': 0.3,
            'profit_factor': 0.3,
            'sharpe_ratio': 0.2,
            'max_drawdown': 0.2
        }
        
        # Normalizar e calcular score
        score = 0
        score += metrics['win_rate'] * weights['win_rate']
        score += min(metrics['profit_factor'], 3) * 33.33 * weights['profit_factor']  # Cap em 3
        score += min(metrics['sharpe_ratio'], 2) * 50 * weights['sharpe_ratio']  # Cap em 2
        score += max(0, 100 - metrics['max_drawdown']) * weights['max_drawdown']
        
        return score
    
    def _get_default_params(self) -> Dict:
        """Retorna parâmetros padrão da configuração"""
        return {
            'rsi_oversold': self.config['strategy']['rsi_oversold'],
            'rsi_overbought': self.config['strategy']['rsi_overbought'],
            'stop_loss_pct': self.config['risk']['stop_loss_pct'],
            'take_profit_pct': self.config['risk']['take_profit_pct']
        }
    
    async def validate_strategy(self) -> bool:
        """Valida se a estratégia atende aos critérios mínimos"""
        logger.info("📊 Validando estratégia...")
        
        # Usar parâmetros atuais
        params = self._get_default_params()
        
        # Rodar backtest completo
        all_trades = []
        for symbol in self.config['trading_pairs']:
            result = await self.run_backtest(symbol, params)
            if result:
                all_trades.extend(result['trades'])
        
        # Calcular métricas agregadas
        if len(all_trades) < self.validation_config['min_trades']:
            logger.warning(f"Trades insuficientes: {len(all_trades)} < {self.validation_config['min_trades']}")
            return False
        
        metrics = self._calculate_metrics(all_trades)
        
        # Verificar critérios
        passed = True
        
        if metrics['win_rate'] < self.validation_config['min_win_rate'] * 100:
            logger.warning(f"Win rate baixo: {metrics['win_rate']:.1f}% < {self.validation_config['min_win_rate'] * 100}%")
            passed = False
        
        if metrics['profit_factor'] < self.validation_config['min_profit_factor']:
            logger.warning(f"Profit factor baixo: {metrics['profit_factor']:.2f} < {self.validation_config['min_profit_factor']}")
            passed = False
        
        if metrics['max_drawdown'] > self.validation_config['max_drawdown'] * 100:
            logger.warning(f"Drawdown alto: {metrics['max_drawdown']:.1f}% > {self.validation_config['max_drawdown'] * 100}%")
            passed = False
        
        if passed:
            logger.info("✅ Estratégia validada com sucesso!")
            self._print_validation_report(metrics)
        else:
            logger.error("❌ Estratégia falhou na validação")
        
        return passed
    
    def _print_validation_report(self, metrics: Dict):
        """Imprime relatório de validação"""
        report = f"""
╔══════════════════════════════════════════════╗
║          RELATÓRIO DE VALIDAÇÃO              ║
╠══════════════════════════════════════════════╣
║ Total de Trades: {metrics['total_trades']:>28} ║
║ Taxa de Acerto: {metrics['win_rate']:>28.1f}% ║
║ Profit Factor: {metrics['profit_factor']:>29.2f} ║
║ Lucro Médio: {metrics['avg_profit']:>30.1f}% ║
║ Perda Média: {metrics['avg_loss']:>30.1f}% ║
║ Drawdown Máximo: {metrics['max_drawdown']:>26.1f}% ║
║ Sharpe Ratio: {metrics['sharpe_ratio']:>29.2f} ║
║ Expectancy: {metrics['expectancy']:>31.2f}% ║
╚══════════════════════════════════════════════╝
        """
        logger.info(report)
    
    def should_update_params(self, current_metrics: Dict, new_metrics: Dict) -> bool:
        """Verifica se deve atualizar parâmetros baseado em melhoria"""
        if not current_metrics:
            return True
        
        # Calcular scores
        current_score = self._calculate_optimization_score(current_metrics)
        new_score = self._calculate_optimization_score(new_metrics)
        
        # Requer melhoria mínima
        improvement = ((new_score - current_score) / current_score) * 100
        
        return improvement >= self.optimization_config['min_improvement_pct']
