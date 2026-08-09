"""termdash - 一个好看的可交互系统监控终端仪表盘。"""

from __future__ import annotations

import platform
import socket
import time
from datetime import datetime

import psutil
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, ProgressBar, Static

BORDER = "#33dd88"
ACCENT = "#00d4ff"
WARN = "#ffd000"
DANGER = "#ff5555"
TEXT = "#d0d0d0"


def fmt_bytes(num: float) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num} B"


def fmt_uptime(boot_time: float) -> str:
    seconds = int(time.time() - boot_time)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}天 {hours}小时 {minutes}分"


def bar_color(value: float) -> str:
    if value < 50:
        return "green"
    if value < 80:
        return "yellow"
    return "red"


class GaugeCard(Static):
    """带标签、百分比和进度条的卡片。"""

    def __init__(self, title: str, symbol: str) -> None:
        super().__init__(classes="card")
        self.title_text = title
        self.symbol = symbol
        self.pct_label = Label("0%", classes="pct")
        self.bar = ProgressBar(total=100, show_eta=False)
        self.value_label = Label("", classes="sub")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="card-head"):
            yield Label(f"{self.symbol}  {self.title_text}", classes="card-title")
            yield self.pct_label
        yield self.bar
        yield self.value_label

    def update_value(self, pct: float, detail: str = "") -> None:
        self.bar.update(progress=pct)
        self.pct_label.update(f"{pct:.1f}%")
        self.pct_label.styles.color = bar_color(pct)
        self.bar.styles.color = bar_color(pct)
        if detail:
            self.value_label.update(detail)


class TermdashApp(App):
    """termdash 主应用。"""

    TITLE = "🖥️  TERMDASH"
    CSS = f"""
    Screen {{
        background: #0a0f14;
    }}
    Header {{
        background: #0a0f14;
        color: {ACCENT};
    }}
    Header .header-title {{
        color: {ACCENT};
        text-style: bold;
    }}
    Footer {{
        background: #10161d;
        color: {TEXT};
    }}
    #tabs {{
        height: 1;
        dock: top;
    }}
    .tab {{
        padding: 0 2;
        text-style: bold;
        color: #8a8a8a;
        background: #10161d;
    }}
    .tab.active {{
        color: #061014;
        background: {ACCENT};
    }}
    #overview {{
        layout: grid;
        grid-size: 2 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr;
        padding: 1;
        height: 100%;
    }}
    #procs-page, #disks-page, #net-page {{
        padding: 1;
        height: 100%;
    }}
    #syscard {{
        height: 1fr;
    }}
    .card {{
        border: round {BORDER};
        background: #0d141b;
        padding: 0 1;
        margin: 0 1 1 1;
        min-height: 6;
    }}
    .card-head {{
        height: 1;
    }}
    .card-title {{
        color: {ACCENT};
        text-style: bold;
    }}
    .pct {{
        dock: right;
        color: {BORDER};
        text-style: bold;
    }}
    .sub {{
        color: {TEXT};
    }}
    .k {{
        color: {ACCENT};
    }}
    .v {{
        color: {TEXT};
    }}
    DataTable {{
        background: #0d141b;
        border: round {BORDER};
    }}
    DataTable:focus {{
        border: round {ACCENT};
    }}
    DataTable > .datatable--header {{
        color: {ACCENT};
        text-style: bold;
    }}
    DataTable > .datatable--cursor {{
        background: {ACCENT};
        color: #061014;
    }}
    #syscard {{
        border: round {BORDER};
        background: #0d141b;
        margin: 0 1 1 1;
        padding: 0 1;
    }}
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("tab", "next_tab", "切换页面"),
        ("1", "goto_overview", "概览"),
        ("2", "goto_procs", "进程"),
        ("3", "goto_disks", "磁盘"),
        ("4", "goto_net", "网络"),
        ("up", "cursor_up", "上移"),
        ("down", "cursor_down", "下移"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.page = "overview"
        self.prev_bytes = psutil.net_io_counters()
        self.prev_time = time.time()

    def compose(self) -> ComposeResult:
        self.syscard = Static("", id="syscard", classes="card")
        self.cpu_card = GaugeCard("CPU", "⚡")
        self.mem_card = GaugeCard("内存", "🧠")
        self.disk_card = GaugeCard("磁盘 /", "💾")
        self.procs_table = DataTable(cursor_type="row", zebra_stripes=True)
        self.procs_table.add_columns("PID", "进程名", "CPU%", "内存%")
        self.disks_table = DataTable(cursor_type="row", zebra_stripes=True)
        self.disks_table.add_columns("挂载点", "文件系统", "总量", "已用", "可用", "使用率")
        self.net_table = DataTable(cursor_type="row", zebra_stripes=True)
        self.net_table.add_columns("接口", "接收/秒", "发送/秒", "接收总量", "发送总量")

        yield Header(show_clock=True)
        with Horizontal(id="tabs"):
            yield Label("1 概览", classes="tab active", id="tab-overview")
            yield Label("2 进程", classes="tab", id="tab-procs")
            yield Label("3 磁盘", classes="tab", id="tab-disks")
            yield Label("4 网络", classes="tab", id="tab-net")

        with Grid(id="overview"):
            yield self.syscard
            yield self.cpu_card
            yield self.mem_card
            yield self.disk_card

        with Vertical(id="procs-page"):
            yield self.procs_table
        with Vertical(id="disks-page"):
            yield self.disks_table
        with Vertical(id="net-page"):
            yield self.net_table
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_interval = self.set_interval(1.0, self.update_all, pause=False)
        self.update_all()
        self.show_page("overview")

    def show_page(self, page: str) -> None:
        self.page = page
        for name in ("overview", "procs", "disks", "net"):
            widget = self.query_one(f"#overview" if name == "overview" else f"#{name}-page")
            widget.display = (name == page)
            tab = self.query_one(f"#tab-{name}", Label)
            tab.set_class(name == page, "active")
        if page == "procs":
            self.procs_table.focus()

    def action_next_tab(self) -> None:
        order = ["overview", "procs", "disks", "net"]
        nxt = order[(order.index(self.page) + 1) % len(order)]
        self.show_page(nxt)

    def action_goto_overview(self) -> None:
        self.show_page("overview")

    def action_goto_procs(self) -> None:
        self.show_page("procs")

    def action_goto_disks(self) -> None:
        self.show_page("disks")

    def action_goto_net(self) -> None:
        self.show_page("net")

    def action_cursor_up(self) -> None:
        if self.page == "procs":
            self.procs_table.action_cursor_up()

    def action_cursor_down(self) -> None:
        if self.page == "procs":
            self.procs_table.action_cursor_down()

    def update_all(self) -> None:
        self.update_sys()
        self.update_gauges()
        self.update_procs()
        self.update_disks()
        self.update_net()

    def update_sys(self) -> None:
        cpu_count = psutil.cpu_count()
        load = psutil.getloadavg()
        self.syscard.update(
            f"""[b]{socket.gethostname()}[/b]
系统: {platform.system()} {platform.release()} ({platform.machine()})
内核: {platform.platform()}
开机: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M')}  已运行 {fmt_uptime(psutil.boot_time())}
CPU 核心: {cpu_count}   负载: {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}
Python: {platform.python_version()}
"""
        )

    def update_gauges(self) -> None:
        self.cpu_card.update_value(
            psutil.cpu_percent(interval=None),
            f"负载 {psutil.getloadavg()[0]:.2f}",
        )
        mem = psutil.virtual_memory()
        self.mem_card.update_value(
            mem.percent,
            f"已用 {fmt_bytes(mem.used)} / 共 {fmt_bytes(mem.total)}",
        )
        disk = psutil.disk_usage("/")
        self.disk_card.update_value(
            disk.percent,
            f"已用 {fmt_bytes(disk.used)} / 共 {fmt_bytes(disk.total)}",
        )

    def update_procs(self) -> None:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda p: (p["cpu_percent"] or 0), reverse=True)
        rows = [(
            str(p["pid"]),
            (p["name"] or "?")[:24],
            f"{p['cpu_percent'] or 0:.1f}",
            f"{p['memory_percent'] or 0:.1f}",
        ) for p in procs[:50]]
        self.replace_rows(self.procs_table, rows)

    def update_disks(self) -> None:
        rows = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            rows.append((
                part.mountpoint,
                part.fstype,
                fmt_bytes(usage.total),
                fmt_bytes(usage.used),
                fmt_bytes(usage.free),
                f"{usage.percent:.0f}%",
            ))
        self.replace_rows(self.disks_table, rows)

    def update_net(self) -> None:
        now = time.time()
        net = psutil.net_io_counters()
        interval = max(now - self.prev_time, 0.001)
        down = (net.bytes_recv - self.prev_bytes.bytes_recv) / interval
        up = (net.bytes_sent - self.prev_bytes.bytes_sent) / interval
        self.prev_bytes = net
        self.prev_time = now
        rows = [(
            "合计",
            fmt_bytes(down) + "/s",
            fmt_bytes(up) + "/s",
            fmt_bytes(net.bytes_recv),
            fmt_bytes(net.bytes_sent),
        )]
        self.replace_rows(self.net_table, rows)

    @staticmethod
    def replace_rows(table: DataTable, rows: list[tuple]) -> None:
        table.clear()
        for row in rows:
            table.add_row(*row)


def main() -> None:
    TermdashApp().run()


if __name__ == "__main__":
    main()
