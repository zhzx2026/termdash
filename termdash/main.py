"""一个实时更新的系统监控终端仪表盘。

用法:
    python -m termdash
    python -m termdash --interval 1.5
"""

import argparse
import platform
import socket
import sys
import time
from datetime import datetime

import psutil
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from . import __version__


def build_header() -> Panel:
    """返回一个渐变色的品牌标题面板。"""
    title = Text("🖥️  TERMDASH", style="bold white on blue")
    subtitle = Text(
        f"系统监控仪表盘  ·  v{__version__}  ·  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        style="dim cyan",
    )
    return Panel(Group(Align.center(title), Align.center(subtitle)), box=box.HEAVY)


def build_system_info() -> Panel:
    """返回系统基本信息面板。"""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    info = {
        "主机名": socket.gethostname(),
        "系统": f"{platform.system()} {platform.release()}",
        "架构": f"{platform.machine()} ({platform.processor()})",
        "内核": platform.platform(),
        "开机时间": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M"),
        "运行时长": _humanize_uptime(psutil.boot_time()),
        "Python": sys.version.split()[0],
        "CPU 核心": f"{psutil.cpu_count(logical=True)} 逻辑 / {psutil.cpu_count(logical=False)} 物理",
    }
    for key, value in info.items():
        table.add_row(Text(key, style="bold cyan"), Text(value))
    return Panel(table, title="📋  系统信息", border_style="cyan", box=box.ROUNDED)


def build_resource_gauges() -> Panel:
    """返回 CPU / 内存 / 磁盘 实时占用仪表。"""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}", style="bold"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%", style="white"),
    )

    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    t_cpu = progress.add_task("CPU    ", total=100)
    t_mem = progress.add_task("内存    ", total=100)
    t_disk = progress.add_task("磁盘 / ", total=100)
    progress.update(t_cpu, completed=cpu)
    progress.update(t_mem, completed=mem.percent)
    progress.update(t_disk, completed=disk.percent)

    mem_text = f" {_fmt_bytes(mem.used)} / {_fmt_bytes(mem.total)}"
    disk_text = f" {_fmt_bytes(disk.used)} / {_fmt_bytes(disk.total)}"

    return Panel(
        Group(progress, Text(mem_text, style="dim yellow"), Text(disk_text, style="dim yellow")),
        title="⚡  资源占用",
        border_style="green",
        box=box.ROUNDED,
    )


def build_network_panel() -> Panel:
    """返回网络收发面板。"""
    net = psutil.net_io_counters()
    return Panel(
        Group(
            Text(f"📥 已接收   {_fmt_bytes(net.bytes_recv)}", style="green"),
            Text(f"📤 已发送   {_fmt_bytes(net.bytes_sent)}", style="magenta"),
        ),
        title="🌐  网络流量",
        border_style="magenta",
        box=box.ROUNDED,
    )


def build_top_processes(max_rows: int = 5, max_cols: int = 4) -> Panel:
    """返回占用最高的前 N 个进程表格，行数列数随终端尺寸自适应。"""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda p: (p["cpu_percent"] or 0), reverse=True)

    table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
    table.add_column("PID", justify="right", min_width=5)
    table.add_column("进程名", no_wrap=True, min_width=12, max_width=24)
    if max_cols >= 3:
        table.add_column("CPU %", justify="right")
    if max_cols >= 4:
        table.add_column("内存 %", justify="right")

    for p in processes[:max_rows]:
        row = [str(p["pid"]), p["name"] or "?"]
        if max_cols >= 3:
            row.append(f"{p['cpu_percent'] or 0:.1f}")
        if max_cols >= 4:
            row.append(f"{p['memory_percent'] or 0:.1f}")
        table.add_row(*row)

    return Panel(
        table,
        title=f"🔥  进程 TOP {max_rows}",
        border_style="yellow",
        box=box.ROUNDED,
    )


def build_footer() -> Panel:
    """返回底部提示面板。"""
    footer = Text(
        "Ctrl+C 退出   ·   数据每秒实时刷新   ·   Powered by Rich & psutil",
        style="bold white on blue",
        justify="center",
    )
    return Panel(footer, box=box.ROUNDED)


def _fmt_bytes(num: int) -> str:
    """将字节数格式化为人类可读形式。"""
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num} B"


def _humanize_uptime(boot_time: float) -> str:
    """将开机时间转换为人类可读的时长。"""
    seconds = int(time.time() - boot_time)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days} 天 {hours} 小时 {minutes} 分"


def build_layout() -> Layout:
    """搭建整体仪表盘布局。"""
    layout = Layout()
    layout.split(
        Layout(name="header", size=5),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    layout["left"].split(
        Layout(name="sysinfo", ratio=2),
        Layout(name="gauges", ratio=3),
    )
    layout["right"].split(
        Layout(name="network", ratio=1),
        Layout(name="processes", ratio=3),
    )
    return layout


def render_dashboard(layout: Layout, width: int, height: int) -> Layout:
    """将实时数据渲染进布局，行数列数随终端尺寸自适应。"""
    body_height = max(height - 8, 5)
    processes_height = int(body_height * 0.75)
    rows = max(1, min(15, (processes_height - 8) // 2))
    cols = 4 if width >= 90 else 3 if width >= 75 else 2

    layout["header"].update(build_header())
    layout["sysinfo"].update(build_system_info())
    layout["gauges"].update(build_resource_gauges())
    layout["network"].update(build_network_panel())
    layout["processes"].update(build_top_processes(max_rows=rows, max_cols=cols))
    layout["footer"].update(build_footer())
    return layout


def main() -> None:
    parser = argparse.ArgumentParser(description="termdash - 系统监控终端仪表盘")
    parser.add_argument(
        "-i", "--interval", type=float, default=1.0, help="刷新间隔（秒），默认 1.0"
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="实时刷新模式（默认只打印一次即退出）",
    )
    args = parser.parse_args()

    console = Console()
    layout = build_layout()

    if not args.watch:
        console.print(render_dashboard(layout, console.width, console.height))
        console.print("[bold yellow]⏳ 界面显示 5 秒后自动关闭，按 Ctrl+C 立即退出[/]")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            pass
        return

    try:
        with Live(
            console=console,
            screen=False,
            auto_refresh=False,
            refresh_per_second=10,
        ) as live:
            live.update(render_dashboard(layout, console.width, console.height))
            live.refresh()
            while True:
                time.sleep(args.interval)
                live.update(render_dashboard(layout, console.width, console.height))
                live.refresh()
    except KeyboardInterrupt:
        console.print("[bold green]👋 再见！[/]")
    except Exception as exc:  # 兜底：避免静默闪退
        console.print(f"[bold red]❌ 出现错误：[/]{exc}")


if __name__ == "__main__":
    main()
