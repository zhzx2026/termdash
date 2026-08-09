"""termdash — 全面的可交互系统监控终端仪表盘。

7 个页面：概览 / 进程 / 磁盘 / 网络 / 传感器 / 终端 / 帮助
"""

from __future__ import annotations

import os
import platform
import shlex
import socket
import subprocess
import time
from collections import defaultdict
from datetime import datetime

import psutil
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Static,
)

# ───── 常量 ─────
CYAN = "#00d4ff"
GREEN = "#33dd88"
YELLOW = "#ffd000"
RED = "#ff5555"
PURPLE = "#cc88ff"
BLUE = "#4488ff"
GRAY = "#8a8a8a"
BG = "#0a0f14"
CARD_BG = "#0d141b"

ORDER = ["overview", "procs", "disks", "net", "sensors", "shell", "help"]
ICONS = {
    "overview": "🖥️", "procs": "📊", "disks": "💾",
    "net": "🌐", "sensors": "🌡️", "shell": ">_", "help": "?",
}


def fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or u == "TB":
            return f"{n:.1f} {u}"
        n /= 1024
    return str(n)


def fmt_uptime(boot: float) -> str:
    s = int(time.time() - boot)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    return f"{d}d {h}h {m}m"


def bar_clr(v: float) -> str:
    return "green" if v < 60 else "yellow" if v < 85 else "red"


# ───── 自定义小部件 ─────
class Gauge(Static):
    """带标签、百分比、进度条和详情的仪表卡片。"""

    def __init__(self, title: str, icon: str) -> None:
        super().__init__(classes="gauge")
        self.gtitle = title
        self.gicon = icon

    def compose(self) -> ComposeResult:
        yield Label(f"{self.gicon}  {self.gtitle}", classes="gtitle")
        yield ProgressBar(total=100, show_eta=False, id="bar")
        yield Label("0%", id="pct")
        yield Label("", id="detail")

    def set(self, pct: float, detail: str = "") -> None:
        bar = self.query_one("#bar", ProgressBar)
        pct_label = self.query_one("#pct", Label)
        det = self.query_one("#detail", Label)
        bar.update(progress=pct)
        pct_label.update(f"{pct:.1f}%")
        for w in (bar, pct_label):
            w.styles.color = bar_clr(pct)
        if detail:
            det.update(detail)


class PerCore(Static):
    """CPU 每核心进度条。"""

    def __init__(self) -> None:
        super().__init__(classes="gauge")
        self.bars: dict[str, ProgressBar] = {}

    def compose(self) -> ComposeResult:
        yield Label("🧮  每核心 CPU", classes="gtitle")
        for i in range(psutil.cpu_count() or 4):
            uid = f"core-{i}"
            bar = ProgressBar(total=100, show_eta=False, id=uid)
            self.bars[uid] = bar
            yield Horizontal(Label(f"C{i:2d}", classes="clbl"), bar)

    def update_cores(self, percents: list[float]) -> None:
        for i, pct in enumerate(percents):
            uid = f"core-{i}"
            if uid in self.bars:
                self.bars[uid].update(progress=pct)


# ───── 主应用 ─────
class TermdashApp(App):
    TITLE = "🖥️  TERMDASH"
    CSS = f"""
    Screen {{ background: {BG}; }}
    Header {{ background: {BG}; color: {CYAN}; }}
    Header .header-title {{ color: {CYAN}; text-style: bold; }}
    Footer {{ background: #10161d; color: {GRAY}; }}
    #tabs {{ height: 1; dock: top; }}
    .tab {{ padding: 0 2; background: #10161d; color: {GRAY}; }}
    .tab.active {{ background: {CYAN}; color: #061014; text-style: bold; }}
    .page {{ padding: 1; height: 100%; }}
    #overview {{ layout: grid; grid-size: 2 3; grid-rows: 2fr 1fr 1fr; grid-columns: 1fr 1fr; }}
    .gauge {{ border: round {GREEN}; background: {CARD_BG}; margin: 0 1 1 1; padding: 0 1; min-height: 4; }}
    .gtitle {{ color: {CYAN}; text-style: bold; height: 1; }}
    #pct {{ dock: top; text-align: right; color: {GREEN}; text-style: bold; margin: 0 1; }}
    #detail {{ color: {GRAY}; }}
    .clbl {{ width: 4; color: {GRAY}; }}
    DataTable {{ background: {CARD_BG}; margin: 0 1 1 1; }}
    DataTable > .datatable--header {{ color: {CYAN}; text-style: bold; }}
    DataTable > .datatable--cursor {{ background: {CYAN}; color: #061014; }}
    #sysinfo {{ border: round {CYAN}; background: {CARD_BG}; margin: 0 1 1 1; padding: 0 1; }}
    #bat {{ border: round {YELLOW}; background: {CARD_BG}; margin: 0 1 1 1; padding: 0 1; }}
    #help-content {{ border: round {CYAN}; background: {CARD_BG}; margin: 0 1 1 1; padding: 1 2; }}
    #shell-input {{ border: round {CYAN}; background: {CARD_BG}; margin: 1; padding: 0 1; }}
    #shell-log {{ margin: 0 1 1 1; }}
    #sensor-scroll {{ overflow: auto; }}
    .kv {{ height: auto; }}
    .k {{ color: {CYAN}; }}
    .v {{ color: {GRAY}; }}
    .hdr {{ color: {CYAN}; text-style: bold; }}
    .val {{ color: {GREEN}; }}
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("tab", "next_page", "下一页"),
        ("1", "goto_overview", "概览"),
        ("2", "goto_procs", "进程"),
        ("3", "goto_disks", "磁盘"),
        ("4", "goto_net", "网络"),
        ("5", "goto_sensors", "传感器"),
        ("6", "goto_shell", "终端"),
        ("h", "show_help", "帮助"),
        ("/", "focus_shell", "终端输入"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.page = "overview"
        self.prev_net = psutil.net_io_counters()
        self.prev_disk = psutil.disk_io_counters()
        self.prev_time = time.time()
        self.shell_history: list[str] = []

    # ── compose ──
    def compose(self) -> ComposeResult:
        # 系统信息
        self.sys_label = Static("", id="sysinfo")
        # 仪表
        self.cpu_gauge = Gauge("CPU", "⚡")
        self.mem_gauge = Gauge("内存", "🧠")
        self.disk_gauge = Gauge("磁盘 /", "💾")
        self.percore = PerCore()
        # 电池
        self.bat_label = Static("", id="bat")
        # 表格
        self.procs_tbl = DataTable(cursor_type="row", zebra_stripes=True)
        self.procs_tbl.add_columns("PID", "进程名", "CPU%", "内存%")
        self.disks_tbl = DataTable(cursor_type="row", zebra_stripes=True)
        self.disks_tbl.add_columns("挂载点", "类型", "总量", "已用", "可用", "使用率", "读/s", "写/s")
        self.net_tbl = DataTable(cursor_type="row", zebra_stripes=True)
        self.net_tbl.add_columns("接口", "下载/s", "上传/s", "下载总量", "上传总量")
        self.sensors_tbl = DataTable(cursor_type="row", zebra_stripes=True)
        self.sensors_tbl.add_columns("指标", "值")
        # 帮助
        self.help_w = Static("", id="help-content", classes="page")
        # 终端
        self.shell_log = RichLog(id="shell-log", highlight=True, markup=True, wrap=True)
        self.shell_input = Input(id="shell-input", placeholder="输入命令后回车…")

        yield Header(show_clock=True)
        with Horizontal(id="tabs"):
            for _i, name in enumerate(ORDER):
                yield Label(
                    f"{ICONS[name]} {name}",
                    id=f"tab-{name}",
                    classes="tab active" if name == "overview" else "tab",
                )

        with Grid(id="overview", classes="page"):
            yield self.sys_label
            yield self.cpu_gauge
            yield self.mem_gauge
            yield self.disk_gauge
            yield self.percore
            yield self.bat_label

        with Vertical(id="procs-page", classes="page"):
            yield self.procs_tbl

        with Vertical(id="disks-page", classes="page"):
            yield self.disks_tbl

        with Vertical(id="net-page", classes="page"):
            yield self.net_tbl

        with Vertical(id="sensors-page", classes="page"):
            with Vertical(id="sensor-scroll"):
                yield self.sensors_tbl
                yield Static("💡 macOS 默认不暴露温度传感器，可用 osx-cpu-temp 工具获取",
                             id="sensor-note", classes="v")

        with Vertical(id="shell-page", classes="page"):
            yield self.shell_log
            yield self.shell_input

        yield self.help_w
        yield Footer()

    # ── on_mount ──
    def on_mount(self) -> None:
        self.set_interval(1.0, self.tick, pause=False)
        self.tick()
        self.show_page("overview")
        self.update_help()

    # ── 页面切换 ──
    def show_page(self, page: str) -> None:
        self.page = page
        mapping = {"overview": "#overview", "procs": "#procs-page",
               "disks": "#disks-page", "net": "#net-page",
               "sensors": "#sensors-page", "shell": "#shell-page",
               "help": "#help-content"}
        for name, cid in mapping.items():
            widget = self.query_one(cid)
            is_current = (name == page)
            widget.display = is_current
            if is_current and name == "shell":
                self.shell_input.focus()
            elif is_current and name == "procs":
                self.procs_tbl.focus()
            self.query_one(f"#tab-{name}", Label).set_class(is_current, "active")
        self.sub_title = f"[{page}]  ·  h 帮助  ·  q 退出"

    def action_next_page(self) -> None:
        idx = (ORDER.index(self.page) + 1) % len(ORDER)
        self.show_page(ORDER[idx])
    action_goto_overview = lambda self: self.show_page("overview")
    action_goto_procs = lambda self: self.show_page("procs")
    action_goto_disks = lambda self: self.show_page("disks")
    action_goto_net = lambda self: self.show_page("net")
    action_goto_sensors = lambda self: self.show_page("sensors")
    action_goto_shell = lambda self: self.show_page("shell")
    action_show_help = lambda self: self.show_page("help")
    action_focus_shell = lambda self: self.show_page("shell")

    # ── 定时刷新 ──
    def tick(self) -> None:
        self.update_sys()
        self.update_gauges()
        self.update_percore()
        self.update_battery()
        self.update_procs()
        self.update_disks()
        self.update_net()
        self.update_sensors()

    def update_sys(self) -> None:
        load = psutil.getloadavg()
        self.sys_label.update(
            f"主机: [b]{socket.gethostname()}[/]    系统: {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"内核: {platform.platform()}\n"
            f"开机: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M')}   "
            f"运行: {fmt_uptime(psutil.boot_time())}\n"
            f"CPU: {psutil.cpu_count()} 核  "
            f"频率: {psutil.cpu_freq().current:.0f} MHz   "
            f"负载: {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
        )

    def update_gauges(self) -> None:
        self.cpu_gauge.set(psutil.cpu_percent(interval=None),
                           f"频率 {psutil.cpu_freq().current:.0f} MHz")
        m = psutil.virtual_memory()
        self.mem_gauge.set(m.percent, f"{fmt_bytes(m.used)} / {fmt_bytes(m.total)}")
        d = psutil.disk_usage("/")
        self.disk_gauge.set(d.percent, f"{fmt_bytes(d.used)} / {fmt_bytes(d.total)}")

    def update_percore(self) -> None:
        self.percore.update_cores(psutil.cpu_percent(interval=None, percpu=True))

    def update_battery(self) -> None:
        try:
            bat = psutil.sensors_battery()
            if bat:
                icon = "🔌" if bat.power_plugged else "🔋"
                self.bat_label.update(
                    f"电池: {icon} {bat.percent}%  "
                    f"{'充电中' if bat.power_plugged else '放电中'}"
                )
            else:
                self.bat_label.update("电池: 无")
        except Exception:
            self.bat_label.update("电池: 无")

    def update_procs(self) -> None:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda p: (p["cpu_percent"] or 0), reverse=True)
        rows = [(str(p["pid"]), (p["name"] or "?")[:28],
                 f"{p['cpu_percent'] or 0:.1f}",
                 f"{p['memory_percent'] or 0:.1f}") for p in procs[:100]]
        self._replace(self.procs_tbl, rows)

    def update_disks(self) -> None:
        now = time.time()
        interval = max(now - self.prev_time, 0.001)
        cur = psutil.disk_io_counters()
        read_s = (cur.read_bytes - self.prev_disk.read_bytes) / interval
        write_s = (cur.write_bytes - self.prev_disk.write_bytes) / interval
        self.prev_disk = cur
        rows = []
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
            except (PermissionError, OSError):
                continue
            rows.append((p.mountpoint, p.fstype, fmt_bytes(u.total),
                         fmt_bytes(u.used), fmt_bytes(u.free), f"{u.percent:.0f}%",
                         fmt_bytes(read_s) + "/s", fmt_bytes(write_s) + "/s"))
        self._replace(self.disks_tbl, rows)

    def update_net(self) -> None:
        now = time.time()
        interval = max(now - self.prev_time, 0.001)
        cur = psutil.net_io_counters()
        down = (cur.bytes_recv - self.prev_net.bytes_recv) / interval
        up = (cur.bytes_sent - self.prev_net.bytes_sent) / interval
        self.prev_net = cur
        self.prev_time = now
        rows = [("总流量", fmt_bytes(down) + "/s", fmt_bytes(up) + "/s",
                 fmt_bytes(cur.bytes_recv), fmt_bytes(cur.bytes_sent))]
        self._replace(self.net_tbl, rows)

    def update_sensors(self) -> None:
        rows = []
        try:
            bat = psutil.sensors_battery()
            if bat:
                rows.append(("🔋 电量", f"{bat.percent}% {'(充电)' if bat.power_plugged else '(放电)'}"))
        except Exception:
            pass
        rows.append(("🧮 CPU 频率", f"{psutil.cpu_freq().current:.0f} MHz / {psutil.cpu_freq().max:.0f} MHz"))
        load = psutil.getloadavg()
        rows.append(("📈 系统负载", f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"))
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        rows.append(("💾 交换空间", f"{fmt_bytes(swap.used)} / {fmt_bytes(swap.total)}"))
        self._replace(self.sensors_tbl, rows)

    def update_help(self) -> None:
        self.help_w.update("""\
[b cyan]🖥️  TERMDASH  帮助[/]

[b]页面切换[/]
  [b green]1-7[/]  快速切换页面
  [b green]Tab[/]  循环切换
  [b green]h[/]    显示帮助

[b]页面功能[/]
  [b green]↑/↓[/]  进程/表格行移动
  终端页支持 [b green]回车[/] 执行命令

[b]退出[/]
  [b green]q[/] 或 [b green]Ctrl+C[/]

[b]终端使用[/]
  支持任何 shell 命令，输出滚动显示

[b]说明[/]
  数据每秒自动刷新，macOS 默认不暴露温度/风扇传感器
""")

    @staticmethod
    def _replace(tbl: DataTable, rows: list[tuple]) -> None:
        tbl.clear()
        for r in rows:
            tbl.add_row(*r)

    # ── 终端 Shell ──
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input is not self.shell_input:
            return
        cmd = event.value.strip()
        event.input.clear()
        if not cmd:
            return
        self.shell_log.write(f"\n[bold cyan]$ {cmd}[/]")
        self.shell_history.append(cmd)
        self.run_command(cmd)

    async def run_command(self, cmd: str) -> None:
        try:
            proc = await self.run_async(
                subprocess.run,
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd(),
            )
            if proc.stdout:
                self.shell_log.write(proc.stdout.rstrip())
            if proc.stderr:
                self.shell_log.write(f"[red]{proc.stderr.rstrip()}[/]")
            if proc.returncode != 0:
                self.shell_log.write(f"[yellow]退出码: {proc.returncode}[/]")
        except subprocess.TimeoutExpired:
            self.shell_log.write("[red]⏱️ 命令超时（30秒）[/]")
        except Exception as e:
            self.shell_log.write(f"[red]错误: {e}[/]")
        self.shell_input.focus()


def main() -> None:
    TermdashApp().run()


if __name__ == "__main__":
    main()
