"""
Manipulador de Banco de Dados - SQLite
"""
import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """Gerencia todas as operações do banco de dados"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        
    def initialize(self):
        """Inicializa o banco de dados e cria tabelas"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            
            # Criar tabelas
            self._create_tables()
            
            logger.info("✅ Banco de dados inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco: {e}")
            raise
    
    def _create_tables(self):
        """Cria as tabelas necessárias"""
        cursor = self.conn.cursor()
        
        # Tabela de trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pair TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                pnl REAL,
                pnl_percent REAL,
                fees REAL,
                duration_minutes INTEGER,
                exit_reason TEXT,
                config_hash TEXT,
                market_volatility REAL,
                indicators_snapshot TEXT,
                status TEXT DEFAULT 'OPEN',
                order_id TEXT
            )
        """)
        
        # Tabela de logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        
        # Índices para performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
        
        self.conn.commit()
    
    def save_trade(self, trade_data: Dict) -> int:
        """Salva um novo trade"""
        cursor = self.conn.cursor()
        
        # Serializar indicadores se existirem
        if 'indicators_snapshot' in trade_data and isinstance(trade_data['indicators_snapshot'], dict):
            trade_data['indicators_snapshot'] = json.dumps(trade_data['indicators_snapshot'])
        
        cursor.execute("""
            INSERT INTO trades (
                timestamp, pair, side, entry_price, quantity, 
                status, config_hash, indicators_snapshot, order_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('timestamp', datetime.now()),
            trade_data['pair'],
            trade_data['side'],
            trade_data['entry_price'],
            trade_data['quantity'],
            trade_data.get('status', 'OPEN'),
            trade_data.get('config_hash', ''),
            trade_data.get('indicators_snapshot', '{}'),
            trade_data.get('order_id', '')
        ))
        
        trade_id = cursor.lastrowid
        self.conn.commit()
        
        logger.debug(f"Trade salvo com ID: {trade_id}")
        return trade_id
    
    def update_trade(self, update_data: Dict):
        """Atualiza um trade existente"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE trades SET 
                exit_price = ?,
                pnl = ?,
                pnl_percent = ?,
                fees = ?,
                duration_minutes = ?,
                exit_reason = ?,
                status = 'CLOSED',
                timestamp = ?
            WHERE order_id = ? AND status = 'OPEN'
        """, (
            update_data['exit_price'],
            update_data['pnl'],
            update_data['pnl_percent'],
            update_data['fees'],
            update_data['duration_minutes'],
            update_data['exit_reason'],
            update_data.get('exit_time', datetime.now()),
            update_data['order_id']
        ))
        
        self.conn.commit()
    
    def save_log(self, level: str, message: str):
        """Salva uma mensagem de log"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO logs (timestamp, level, message)
            VALUES (?, ?, ?)
        """, (datetime.now(), level, message))
        
        self.conn.commit()
    
    def get_trades(self, limit: int = 100, status: Optional[str] = None) -> List[Dict]:
        """Recupera trades do banco"""
        cursor = self.conn.cursor()
        
        if status:
            query = """
                SELECT * FROM trades 
                WHERE status = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            cursor.execute(query, (status, limit))
        else:
            query = """
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            cursor.execute(query, (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trade = dict(row)
            # Deserializar indicadores
            if trade.get('indicators_snapshot'):
                try:
                    trade['indicators_snapshot'] = json.loads(trade['indicators_snapshot'])
                except:
                    trade['indicators_snapshot'] = {}
            trades.append(trade)
        
        return trades
    
    def get_daily_stats(self, date: Optional[datetime] = None) -> Dict:
        """Calcula estatísticas diárias"""
        if date is None:
            date = datetime.now()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        cursor = self.conn.cursor()
        
        # Total de trades
        cursor.execute("""
            SELECT COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                   SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                   SUM(pnl) as total_pnl,
                   SUM(fees) as total_fees,
                   AVG(pnl_percent) as avg_pnl_percent,
                   MAX(pnl) as best_trade,
                   MIN(pnl) as worst_trade
            FROM trades
            WHERE timestamp BETWEEN ? AND ?
            AND status = 'CLOSED'
        """, (start_of_day, end_of_day))
        
        stats = dict(cursor.fetchone())
        
        # Calcular win rate
        if stats['total_trades'] > 0:
            stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
        else:
            stats['win_rate'] = 0
        
        # Net P&L
        stats['net_pnl'] = stats['total_pnl'] - stats['total_fees'] if stats['total_pnl'] else 0
        
        return stats
    
    def get_performance_history(self, days: int = 30) -> pd.DataFrame:
        """Retorna histórico de performance"""
        cursor = self.conn.cursor()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as daily_pnl,
                SUM(fees) as daily_fees
            FROM trades
            WHERE timestamp >= ?
            AND status = 'CLOSED'
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (start_date,))
        
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=['date', 'trades', 'wins', 'daily_pnl', 'daily_fees'])
        
        # Calcular métricas adicionais
        df['net_pnl'] = df['daily_pnl'] - df['daily_fees']
        df['win_rate'] = (df['wins'] / df['trades'] * 100).fillna(0)
        df['cumulative_pnl'] = df['net_pnl'].cumsum()
        
        return df
    
    def get_trade_by_config(self, config_hash: str) -> List[Dict]:
        """Busca trades por hash de configuração"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades
            WHERE config_hash = ?
            ORDER BY timestamp DESC
        """, (config_hash,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_logs(self, days: int = 7):
        """Remove logs antigos"""
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            DELETE FROM logs
            WHERE timestamp < ?
        """, (cutoff_date,))
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        if deleted > 0:
            logger.info(f"Removidos {deleted} logs antigos")
    
    def backup(self, backup_path: str):
        """Faz backup do banco de dados"""
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup criado: {backup_path}")
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
    
    def close(self):
        """Fecha a conexão com o banco"""
        if self.conn:
            self.conn.close()
            logger.debug("Conexão com banco fechada")
