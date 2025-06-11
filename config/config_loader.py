"""
Carregador de Configurações YAML
"""
import yaml
import logging
import os
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Carrega configurações do arquivo YAML"""
    try:
        # Verificar se arquivo existe
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
        
        # Carregar YAML
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Validar configurações essenciais
        validate_config(config)
        
        # Aplicar variáveis de ambiente se existirem
        config = apply_env_vars(config)
        
        logger.info(f"✅ Configurações carregadas de {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {e}")
        raise

def validate_config(config: Dict[str, Any]):
    """Valida se todas as configurações necessárias estão presentes"""
    required_sections = [
        'mode',
        'trading_pairs',
        'strategy',
        'risk',
        'data',
        'binance',
        'database'
    ]
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Seção obrigatória ausente: {section}")
    
    # Validar modo
    if config['mode'] not in ['testnet', 'real']:
        raise ValueError("Modo deve ser 'testnet' ou 'real'")
    
    # Validar pares de trading
    if not config['trading_pairs'] or not isinstance(config['trading_pairs'], list):
        raise ValueError("trading_pairs deve ser uma lista não vazia")
    
    # Validar configurações de risco
    risk = config['risk']
    if risk['position_size_pct'] > 50:
        logger.warning("⚠️ Position size > 50% é muito arriscado!")
    
    if risk['stop_loss_pct'] < 1:
        logger.warning("⚠️ Stop loss < 1% pode resultar em muitas paradas falsas")
    
    # Validar API keys
    mode = config['mode']
    api_key = config['binance'].get(f'{mode}_api_key', '')
    api_secret = config['binance'].get(f'{mode}_api_secret', '')
    
    if not api_key or api_key == 'YOUR_TESTNET_API_KEY':
        raise ValueError(f"API key para {mode} não configurada!")
    
    if not api_secret or api_secret == 'YOUR_TESTNET_API_SECRET':
        raise ValueError(f"API secret para {mode} não configurada!")

def apply_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica variáveis de ambiente às configurações"""
    
    # Binance API keys
    mode = config['mode']
    
    # Testnet
    testnet_key = os.getenv('BINANCE_TESTNET_API_KEY')
    testnet_secret = os.getenv('BINANCE_TESTNET_API_SECRET')
    
    if testnet_key:
        config['binance']['testnet_api_key'] = testnet_key
    if testnet_secret:
        config['binance']['testnet_api_secret'] = testnet_secret
    
    # Real
    real_key = os.getenv('BINANCE_REAL_API_KEY')
    real_secret = os.getenv('BINANCE_REAL_API_SECRET')
    
    if real_key:
        config['binance']['real_api_key'] = real_key
    if real_secret:
        config['binance']['real_api_secret'] = real_secret
    
    # Telegram (se configurado)
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat = os.getenv('TELEGRAM_CHAT_ID')
    
    if telegram_token and 'notifications' in config:
        config['notifications']['telegram']['bot_token'] = telegram_token
    if telegram_chat and 'notifications' in config:
        config['notifications']['telegram']['chat_id'] = telegram_chat
    
    return config

def save_config(config: Dict[str, Any], config_path: str = "config/settings.yaml"):
    """Salva configurações no arquivo YAML"""
    try:
        # Criar backup
        if os.path.exists(config_path):
            backup_path = f"{config_path}.backup"
            import shutil
            shutil.copy2(config_path, backup_path)
        
        # Salvar configurações
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configurações salvas em {config_path}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar configurações: {e}")
        raise

def update_config_value(key_path: str, value: Any, config_path: str = "config/settings.yaml"):
    """Atualiza um valor específico na configuração"""
    try:
        # Carregar config atual
        config = load_config(config_path)
        
        # Navegar pelo path (ex: "strategy.rsi_oversold")
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Atualizar valor
        old_value = current.get(keys[-1])
        current[keys[-1]] = value
        
        # Salvar
        save_config(config, config_path)
        
        logger.info(f"Config atualizada: {key_path} = {value} (era {old_value})")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração: {e}")
        raise

# Configuração padrão caso o arquivo não exista
DEFAULT_CONFIG = {
    'mode': 'testnet',
    'trading_pairs': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
    'strategy': {
        'timeframe': '5m',
        'rsi_period': 14,
        'rsi_oversold': 32,
        'rsi_overbought': 68,
        'bb_period': 20,
        'bb_std_dev': 2,
        'ema_period': 20,
        'volume_multiplier': 1.2,
        'min_volume_ratio': 0.5,
        'min_bb_width': 0.8,
        'max_spread': 0.1,
        'bb_squeeze_threshold': 0.8,
        'cooldown_seconds': 300,
        'wait_candles_confirm': 1,
        'trading_hours': {
            'enabled': True,
            'avoid_hours': ['00:00-02:00', '12:00-13:00'],
            'best_hours': ['14:00-20:00']
        }
    },
    'risk': {
        'position_size_pct': 15,
        'position_size_min': 15,
        'position_size_max': 40,
        'max_positions': 2,
        'stop_loss_pct': 1.5,
        'take_profit_pct': 2.5,
        'trailing_stop': False,
        'daily_loss_limit': 15.0,
        'max_consecutive_losses': 3,
        'max_spread_pct': 0.3,
        'min_order_size': 10.0
    },
    'data': {
        'download_days': 30,
        'buffer_days': 7,
        'candle_interval': '5m'
    },
    'optimization': {
        'enabled': True,
        'frequency': 'weekly',
        'min_trades_required': 50,
        'min_improvement_pct': 5.0,
        'max_param_change_pct': 15.0,
        'optimize_params': {
            'rsi_oversold': [30, 32, 35],
            'rsi_overbought': [65, 68, 70],
            'stop_loss_pct': [1.25, 1.5, 1.75],
            'take_profit_pct': [2.0, 2.5, 3.0]
        }
    },
    'costs': {
        'maker_fee': 0.001,
        'taker_fee': 0.001,
        'avg_spread_pct': 0.03,
        'avg_slippage_pct': 0.02,
        'total_cost_pct': 0.25
    },
    'validation': {
        'testnet_days': 5,
        'min_trades': 50,
        'min_win_rate': 0.55,
        'min_profit_factor': 1.2,
        'max_drawdown': 0.15
    },
    'binance': {
        'testnet_api_key': 'YOUR_TESTNET_API_KEY',
        'testnet_api_secret': 'YOUR_TESTNET_API_SECRET',
        'testnet_base_url': 'https://testnet.binance.vision',
        'real_api_key': '',
        'real_api_secret': '',
        'real_base_url': 'https://api.binance.com',
        'requests_per_minute': 1200,
        'orders_per_minute': 50,
        'ws_keepalive_interval': 30,
        'ws_reconnect_delay': 5,
        'ws_max_reconnect_attempts': 5
    },
    'database': {
        'path': 'data/trading_bot.db',
        'backup_enabled': True,
        'backup_frequency': 'daily'
    },
    'logging': {
        'level': 'INFO',
        'console_output': True,
        'file_output': True,
        'max_file_size_mb': 50,
        'backup_count': 5
    },
    'notifications': {
        'enabled': False,
        'telegram': {
            'bot_token': '',
            'chat_id': ''
        }
    },
    'targets': {
        'daily_target_pct': 1.5,
        'weekly_target_pct': 8.0,
        'monthly_target_pct': 25.0
    },
    'system': {
        'timezone': 'UTC',
        'update_check': True,
        'debug_mode': False
    }
}

def create_default_config(config_path: str = "config/settings.yaml"):
    """Cria arquivo de configuração padrão"""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as file:
        yaml.dump(DEFAULT_CONFIG, file, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Arquivo de configuração padrão criado: {config_path}")
