"""termdash — macOS 菜单栏系统状态。"""

import time
from datetime import datetime

import psutil
import rumps


def fmt(n: float) -> str:
    for u in ("B", "K", "M", "G"):
        if abs(n) < 1024 or u == "G":
            return f"{n:.1f}{u}"
        n /= 1024
    return str(n)


class TermdashApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("⏳", quit_button=None)
        self.prev_net = psutil.net_io_counters()
        self.prev_time = time.time()
        self.timer = rumps.Timer(self.tick, 1)
        self.timer.start()

    @rumps.clicked("退出 Termdash")
    def quit_app(self, _: rumps.MenuItem) -> None:
        rumps.quit_application()

    @rumps.clicked("──── 系统信息 ────")
    def info_header(self, _: rumps.MenuItem) -> None:
        pass

    def tick(self, _: rumps.Timer) -> None:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        now = time.time()
        net = psutil.net_io_counters()
        interval = max(now - self.prev_time, 0.001)
        down = (net.bytes_recv - self.prev_net.bytes_recv) / interval
        up = (net.bytes_sent - self.prev_net.bytes_sent) / interval
        self.prev_net = net
        self.prev_time = now

        bat = psutil.sensors_battery()
        load = psutil.getloadavg()

        # 菜单栏标题（简洁）
        parts = []
        if cpu >= 50:
            parts.append(f"C:{cpu:.0f}%")
        else:
            parts.append(f"C:{cpu:.0f}%")
        parts.append(f"M:{mem.percent:.0f}%")
        parts.append(f"D:{disk.percent:.0f}%")
        if bat:
            parts.append(f"{bat.percent}%")
        self.title = " │ ".join(parts)

        # 下拉菜单详情
        t = datetime.now().strftime("%H:%M:%S")
        bat_str = f"🔋 {bat.percent}% (充电)" if (bat and bat.power_plugged) else f"🔋 {bat.percent}%" if bat else "无电池"
        self.menu.clear()
        self.menu.update([
            f"🖥️  CPU  {cpu:.1f}%  │  负载 {load[0]:.1f} / {load[1]:.1f} / {load[2]:.1f}",
            f"🧠  内存  {mem.percent:.1f}%  ({fmt(mem.used)} / {fmt(mem.total)})",
            f"💾  磁盘  {disk.percent:.1f}%  ({fmt(disk.used)} / {fmt(disk.total)})",
            f"🌐  ↓{fmt(down)}/s  ↑{fmt(up)}/s",
            bat_str,
            f"⏰  {t}",
            None,  # separator
            "退出 Termdash",
        ])


def main() -> None:
    TermdashApp().run()


if __name__ == "__main__":
    main()
