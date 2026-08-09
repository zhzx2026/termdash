"""termdash — macOS 菜单栏系统状态。"""

import subprocess
import sys
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
        super().__init__("", quit_button=None)
        self.prev_net = psutil.net_io_counters()
        self.prev_time = time.time()

        # 一次建好菜单结构，只改标题不重建
        self.cpu_item = rumps.MenuItem("CPU")
        self.mem_item = rumps.MenuItem("内存")
        self.disk_item = rumps.MenuItem("磁盘")
        self.net_item = rumps.MenuItem("网络")
        self.bat_item = rumps.MenuItem("电池")
        self.time_item = rumps.MenuItem("时间")
        self.quit_item = rumps.MenuItem("退出 Termdash", callback=self._quit)

        self.menu = [
            self.cpu_item,
            self.mem_item,
            self.disk_item,
            self.net_item,
            self.bat_item,
            self.time_item,
            None,
            self.quit_item,
        ]

        self.timer = rumps.Timer(self.tick, 1)
        self.timer.start()

    def _quit(self, _: rumps.MenuItem) -> None:
        rumps.quit_application()

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
        t = datetime.now().strftime("%H:%M:%S")

        self.title = f"{cpu:.0f}%  {mem.percent:.0f}%  {disk.percent:.0f}%"
        if bat:
            self.title += f"  {bat.percent}%"

        self.cpu_item.title = f"CPU     {cpu:.1f}%      负载 {load[0]:.1f} / {load[1]:.1f} / {load[2]:.1f}"
        self.mem_item.title = f"内存    {mem.percent:.1f}%      {fmt(mem.used)} / {fmt(mem.total)}"
        self.disk_item.title = f"磁盘    {disk.percent:.1f}%      {fmt(disk.used)} / {fmt(disk.total)}"
        self.net_item.title = f"网络    ↓ {fmt(down)}/s   ↑ {fmt(up)}/s"
        self.bat_item.title = (
            f"电池    {bat.percent}% 充电中" if (bat and bat.power_plugged)
            else f"电池    {bat.percent}% 电池供电" if bat
            else "电池    无"
        )
        self.time_item.title = f"时间    {t}"


def main() -> None:
    if "--fg" not in sys.argv:
        subprocess.Popen(
            [sys.executable, "-m", "termdash", "--fg"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        )
        return
    TermdashApp().run()


if __name__ == "__main__":
    main()
