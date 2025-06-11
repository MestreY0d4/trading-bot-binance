"""
Dashboard Minimalista - Interface de Terminal
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.align import Align
from rich.text import Text
import keyboard

logger = logging.getLogger(__name__)

class Dashboard:
    """Dashboard de terminal para monitoramento do bot"""
    
    def __init__(self, trading_bot):
        self.bot = trading_bot
        self.console = Console()
        self.running = True
        self.should_stop = False
        self.trading_paused = False
        
        # Estado do dashboard
        self.last_trades = []
        self.current_status = "Inicializando..."
        
    def create_header(self) -> Panel:
        """Cria cabeçalho do dashboard"""
        mode = self.bot.config['mode'].upper()
        mode_color = "green" if mode == "TESTNET" else "red"
        connection_status = "●" if self.bot.client else "○"
        
        header_text = f"[bold]BOT TRADING V5.1[/bold] [{mode_color}]{mode}[/{mode_color}] [{connection_status}] Conectado"
        
        return Panel(
            Align.center(header_text),
            style="bold white on blue"
        )
    
    def create_stats_panel(self) -> Panel:
        """Cria painel de estatísticas"""
        status = self.bot.get_status()
        
        # Calcular capital disponível
        capital_total = 200.0  # Por simplicidade
        capital_usado = sum(
            pos['quantity'] * pos['entry_price'] 
            for pos in status['positions'].values()
        )
        capital_livre = capital_total - capital_usado
        
        # P&L do dia
        pnl = status['daily_pnl']
        pnl_percent = (pnl / capital_total) * 100
        pnl_color = "green" if pnl >= 0 else "red"
        pnl_sign = "+" if pnl >= 0 else ""
        
        stats_text = f"""Capital: [bold]${capital_total:.0f} USDT[/bold] | Livre: ${capital_livre:.0f} USDT
P&L Hoje: [{pnl_color}]{pnl_sign}{pnl_percent:.1f}% ({pnl_sign}${pnl:.2f})[/{pnl_color}]
Trades Hoje: {status['daily_trades']} | Perdas Consecutivas: {status['consecutive_losses']}"""
        
        return Panel(stats_text, title="📊 Estatísticas")
    
    def create_controls_panel(self) -> Panel:
        """Cria painel de controles"""
        pause_text = "⏸️ PAUSAR" if not self.trading_paused else "▶️ RETOMAR"
        
        controls = f"""[{pause_text}] (P)    [⏹️ PARAR] (S)    [📊 RELATÓRIO] (R)    [🔄 REFRESH] (F5)"""
        
        return Panel(
            Align.center(controls),
            style="bold white on dark_blue"
        )
    
    def create_positions_panel(self) -> Panel:
        """Cria painel de posições abertas"""
        status = self.bot.get_status()
        positions = status['positions']
        
        if not positions:
            content = "[dim]Nenhuma posição aberta[/dim]"
        else:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Par", style="cyan")
            table.add_column("Entrada", justify="right")
            table.add_column("Atual", justify="right")
            table.add_column("P&L", justify="right")
            table.add_column("Tempo", justify="right")
            
            for symbol, pos in positions.items():
                # Simular preço atual (em produção, buscar da API)
                current_price = pos['entry_price'] * 1.01  # Simulado
                pnl_percent = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                pnl_color = "green" if pnl_percent >= 0 else "red"
                
                duration = (datetime.now() - pos['entry_time']).seconds // 60
                
                table.add_row(
                    symbol,
                    f"${pos['entry_price']:.2f}",
                    f"${current_price:.2f}",
                    f"[{pnl_color}]{pnl_percent:+.1f}%[/{pnl_color}]",
                    f"{duration}min"
                )
            
            content = table
        
        return Panel(
            content,
            title=f"💼 Posições Abertas ({len(positions)}/{self.bot.config['risk']['max_positions']})"
        )
    
    def create_trades_panel(self) -> Panel:
        """Cria painel com últimos trades"""
        # Buscar últimos trades do banco
        trades = self.bot.db.get_trades(limit=5)
        
        if not trades:
            content = "[dim]Nenhum trade executado[/dim]"
        else:
            lines = []
            for trade in trades:
                if trade['status'] == 'CLOSED':
                    emoji = "✅" if trade['pnl'] > 0 else "❌"
                    pnl_pct = trade.get('pnl_percent', 0)
                    duration = trade.get('duration_minutes', 0)
                    reason = trade.get('exit_reason', 'signal')
                    
                    line = f"{emoji} {trade['pair']} {pnl_pct:+.1f}% ({duration}min) [{reason}]"
                    lines.append(line)
                else:
                    lines.append(f"🔄 {trade['pair']} - ABERTO @ ${trade['entry_price']:.2f}")
            
            content = "\n".join(lines)
        
        return Panel(content, title="📈 Últimos Trades")
    
    def create_status_panel(self) -> Panel:
        """Cria painel de status"""
        status = self.bot.get_status()
        
        if status['paused']:
            status_text = "[yellow]⚠️ Bot pausado por circuit breaker[/yellow]"
        elif not status['running']:
            status_text = "[red]⏹️ Bot parado[/red]"
        else:
            status_text = f"[green]🔍 {self.current_status}[/green]"
        
        # Adicionar informações de mercado
        market_info = []
        for symbol in self.bot.config['trading_pairs']:
            if symbol in self.bot.client.price_cache:
                price = self.bot.client.price_cache[symbol]['price']
                market_info.append(f"{symbol}: ${price:.2f}")
        
        market_text = " | ".join(market_info) if market_info else "Aguardando dados..."
        
        content = f"""Status: {status_text}
Mercado: {market_text}
Última atualização: {datetime.now().strftime('%H:%M:%S')}"""
        
        return Panel(content, title="🤖 Status do Bot")
    
    def create_layout(self) -> Layout:
        """Cria layout completo do dashboard"""
        layout = Layout()
        
        layout.split_column(
            Layout(self.create_header(), size=3),
            Layout(self.create_stats_panel(), size=4),
            Layout(self.create_controls_panel(), size=3),
            Layout(name="middle", size=8),
            Layout(self.create_trades_panel(), size=7),
            Layout(self.create_status_panel(), size=4)
        )
        
        layout["middle"].split_row(
            Layout(self.create_positions_panel())
        )
        
        return layout
    
    async def handle_keyboard(self):
        """Manipula entrada do teclado"""
        while self.running:
            try:
                if keyboard.is_pressed('p'):  # Pausar/Retomar
                    self.trading_paused = not self.trading_paused
                    await asyncio.sleep(0.5)  # Debounce
                    
                elif keyboard.is_pressed('s'):  # Parar
                    self.should_stop = True
                    self.running = False
                    
                elif keyboard.is_pressed('r'):  # Relatório
                    await self.show_report()
                    await asyncio.sleep(1)
                    
                elif keyboard.is_pressed('f5'):  # Refresh
                    # Força atualização
                    pass
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro no handler de teclado: {e}")
                await asyncio.sleep(1)
    
    async def show_report(self):
        """Mostra relatório diário"""
        self.console.clear()
        
        # Buscar estatísticas
        stats = self.bot.db.get_daily_stats()
        
        report = f"""
╔══════════════════════════════════════════════╗
║           RELATÓRIO DIÁRIO - {datetime.now().strftime('%d/%m/%Y')}           ║
╠══════════════════════════════════════════════╣
║ Total de Trades: {stats.get('total_trades', 0):>27} ║
║ Trades Vencedores: {stats.get('winning_trades', 0):>24} ║
║ Trades Perdedores: {stats.get('losing_trades', 0):>24} ║
║ Win Rate: {stats.get('win_rate', 0):>33.1f}% ║
║                                              ║
║ P&L Total: ${stats.get('total_pnl', 0):>31.2f} ║
║ Taxas Totais: ${stats.get('total_fees', 0):>28.2f} ║
║ P&L Líquido: ${stats.get('net_pnl', 0):>29.2f} ║
║                                              ║
║ Melhor Trade: ${stats.get('best_trade', 0):>28.2f} ║
║ Pior Trade: ${stats.get('worst_trade', 0):>30.2f} ║
╚══════════════════════════════════════════════╝
        """
        
        self.console.print(report)
        self.console.print("\n[Pressione qualquer tecla para voltar]")
        await asyncio.sleep(5)
    
    async def run(self):
        """Loop principal do dashboard"""
        # Criar task para keyboard handler
        keyboard_task = asyncio.create_task(self.handle_keyboard())
        
        # Atualizar dashboard a cada segundo
        with Live(self.create_layout(), refresh_per_second=1, console=self.console) as live:
            while self.running:
                try:
                    # Atualizar status
                    self.current_status = self._get_current_status()
                    
                    # Atualizar layout
                    live.update(self.create_layout())
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Erro no dashboard: {e}")
                    await asyncio.sleep(1)
        
        # Cancelar keyboard handler
        keyboard_task.cancel()
    
    def _get_current_status(self) -> str:
        """Obtém status atual do bot"""
        status = self.bot.get_status()
        
        if not status['running']:
            return "Bot parado"
        elif status['paused']:
            return "Bot pausado"
        elif len(status['positions']) >= self.bot.config['risk']['max_positions']:
            return "Máximo de posições atingido"
        else:
            return "Aguardando sinal..."
    
    async def shutdown(self):
        """Encerra o dashboard"""
        self.running = False
        self.console.clear()
        self.console.print("[bold green]Dashboard encerrado[/bold green]")
