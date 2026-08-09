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
        sec = max(now - self.prev_time, 0.001)
        down = (net.bytes_recv - self.prev_net.bytes_recv) / sec
        up = (net.bytes_sent - self.prev_net.bytes_sent) / sec
        self.prev_net = net
        self.prev_time = now

        bat = psutil.sensors_battery()

        # 菜单栏：中文简写 + 图标
        title = f"⚡{cpu:.0f}  🧠{mem.percent:.0f}  💿{disk.percent:.0f}"
        if bat:
            title += f"  {'🔌' if bat.power_plugged else '🔋'}{bat.percent}"
        self.title = title

        # 重建下拉菜单
        bat_str = (
            f"🔌 电池  {bat.percent}%  充电中" if (bat and bat.power_plugged)
            else f"🔋 电池  {bat.percent}%  放电中" if bat
            else "🔋 电池  无"
        )
        t = datetime.now().strftime("%H:%M:%S")
        noop = lambda _: None

        self.menu.clear()
        for s in [
            f"⚡ CPU    {cpu:.1f}%      负载 {load[0]:.1f} {load[1]:.1f} {load[2]:.1f}",
            f"🧠 内存   {mem.percent:.1f}%      {fmt(mem.used)} / {fmt(mem.total)}",
            f"💿 磁盘   {disk.percent:.1f}%      {fmt(disk.used)} / {fmt(disk.total)}",
            f"🌐 网络   ↓{fmt(down)}/s  ↑{fmt(up)}/s",
            bat_str,
            f"⏰ 时间   {t}",
        ]:
            self.menu.add(rumps.MenuItem(s, callback=noop))
        self.menu.add(None)
        self.menu.add(rumps.MenuItem("❌ 退出 Termdash", callback=self._quit))


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
