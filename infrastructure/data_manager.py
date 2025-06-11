"""
Gerenciador de Dados - Download e Buffer
"""
import logging
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sqlite3
import json

logger = logging.getLogger(__name__)

class DataManager:
    """Gerencia download, armazenamento e acesso aos dados de mercado"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.data_config = config['data']
        self.db_path = config['database']['path']
        
        # Buffer em memória
        self.candles_buffer = {}  # {symbol: DataFrame}
        self.last_update = {}     # {symbol: timestamp}
        
        # Cliente Binance será injetado
        self.client = None
        
    async def initialize(self):
        """Inicializa o gerenciador e baixa dados históricos"""
        from infrastructure.binance_api import BinanceClient
        
        # Criar cliente temporário para download
        self.client = BinanceClient(self.config)
        await self.client.initialize()
        
        # Criar tabela se não existir
        self._create_tables()
        
        # Baixar dados históricos para cada par
        logger.info("📊 Baixando dados históricos...")
        
        for symbol in self.config['trading_pairs']:
            logger.info(f"Baixando {symbol}...")
            success = await self._download_historical_data(symbol)
            if not success:
                logger.error(f"Falha ao baixar dados de {symbol}")
                raise Exception(f"Falha ao inicializar dados de {symbol}")
        
        logger.info("✅ Dados históricos baixados com sucesso!")
    
    def _create_tables(self):
        """Cria tabelas para armazenar candles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def _download_historical_data(self, symbol: str) -> bool:
        """Baixa dados históricos de um símbolo"""
        try:
            # Calcular período
            days = self.data_config['download_days']
            interval = self.data_config['candle_interval']
            
            # Converter intervalo para limite de candles
            if interval == '1m':
                limit = min(days * 24 * 60, 1000)  # Máx 1000 candles por request
            elif interval == '5m':
                limit = min(days * 24 * 12, 1000)
            else:
                limit = 1000
            
            # Baixar dados
            klines = await self.client.get_klines(symbol, interval, limit=limit)
            
            if not klines:
                return False
            
            # Converter para DataFrame
            df = self._klines_to_dataframe(klines)
            
            # Salvar no buffer
            self.candles_buffer[symbol] = df
            self.last_update[symbol] = datetime.now()
            
            # Salvar no banco
            self._save_candles_to_db(symbol, df)
            
            logger.info(f"✅ {symbol}: {len(df)} candles baixados")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao baixar dados de {symbol}: {e}")
            return False
    
    def _klines_to_dataframe(self, klines: List) -> pd.DataFrame:
        """Converte klines da Binance para DataFrame"""
        data = []
        
        for kline in klines:
            data.append({
                'timestamp': pd.to_datetime(kline[0], unit='ms'),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def _save_candles_to_db(self, symbol: str, df: pd.DataFrame):
        """Salva candles no banco de dados"""
        conn = sqlite3.connect(self.db_path)
        
        # Preparar dados
        records = []
        for idx, row in df.iterrows():
            records.append((
                symbol,
                int(idx.timestamp()),
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume']
            ))
        
        # Inserir ou atualizar
        conn.executemany("""
            INSERT OR REPLACE INTO candles 
            (symbol, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, records)
        
        conn.commit()
        conn.close()
    
    async def get_latest_candles(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Retorna os últimos N candles do buffer"""
        # Verificar se precisa atualizar
        if symbol not in self.candles_buffer or self._needs_update(symbol):
            await self._update_candles(symbol)
        
        if symbol in self.candles_buffer:
            df = self.candles_buffer[symbol]
            return df.tail(limit) if len(df) > limit else df
        
        return None
    
    def _needs_update(self, symbol: str) -> bool:
        """Verifica se os dados precisam ser atualizados"""
        if symbol not in self.last_update:
            return True
        
        # Atualizar a cada minuto
        time_since_update = datetime.now() - self.last_update[symbol]
        return time_since_update.seconds > 60
    
    async def _update_candles(self, symbol: str):
        """Atualiza candles com dados mais recentes"""
        try:
            # Buscar últimos candles
            klines = await self.client.get_klines(
                symbol, 
                self.data_config['candle_interval'], 
                limit=100
            )
            
            if not klines:
                return
            
            # Converter para DataFrame
            new_df = self._klines_to_dataframe(klines)
            
            # Mesclar com dados existentes
            if symbol in self.candles_buffer:
                old_df = self.candles_buffer[symbol]
                # Combinar e remover duplicatas
                combined = pd.concat([old_df, new_df])
                combined = combined[~combined.index.duplicated(keep='last')]
                
                # Manter apenas os últimos N dias
                cutoff = datetime.now() - timedelta(days=self.data_config['buffer_days'])
                self.candles_buffer[symbol] = combined[combined.index > cutoff]
            else:
                self.candles_buffer[symbol] = new_df
            
            self.last_update[symbol] = datetime.now()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar candles de {symbol}: {e}")
    
    def get_buffer_stats(self) -> Dict:
        """Retorna estatísticas do buffer de dados"""
        stats = {}
        
        for symbol, df in self.candles_buffer.items():
            if len(df) > 0:
                stats[symbol] = {
                    'candles': len(df),
                    'first': df.index[0].strftime('%Y-%m-%d %H:%M'),
                    'last': df.index[-1].strftime('%Y-%m-%d %H:%M'),
                    'last_update': self.last_update.get(symbol, 'N/A')
                }
        
        return stats
    
    async def stream_candles(self, symbol: str, callback):
        """Stream de candles em tempo real via WebSocket"""
        # Implementar se necessário
        pass
    
    def clear_old_data(self):
        """Limpa dados antigos do banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Remover dados mais antigos que 60 dias
        cutoff = int((datetime.now() - timedelta(days=60)).timestamp())
        
        cursor.execute("""
            DELETE FROM candles WHERE timestamp < ?
        """, (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"Removidos {deleted} candles antigos do banco")
