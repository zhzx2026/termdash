"""termdash — 一条简洁的系统状态栏，实时刷新。"""

import socket
import time
from datetime import datetime

import psutil


def fmt_bytes(n: float) -> str:
    for u in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024 or u == "T":
            return f"{n:.1f}{u}"
        n /= 1024
    return str(n)


def main() -> None:
    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    print("\033[?25l")  # 隐藏光标
    try:
        while True:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            bat = psutil.sensors_battery()
            load = psutil.getloadavg()

            now = time.time()
            net = psutil.net_io_counters()
            interval = max(now - prev_time, 0.001)
            down = (net.bytes_recv - prev_net.bytes_recv) / interval
            up = (net.bytes_sent - prev_net.bytes_sent) / interval
            prev_net = net
            prev_time = now

            host = socket.gethostname().split(".")[0]
            t = datetime.now().strftime("%H:%M:%S")

            parts = [
                f"\033[1;36m{host}\033[0m",
                f"CPU \033[1;32m{cpu:5.1f}%\033[0m",
                f"MEM \033[1;33m{mem.percent:5.1f}%\033[0m",
                f"DSK \033[1;34m{disk.percent:5.1f}%\033[0m",
                f"↓\033[32m{fmt_bytes(down):>6s}\033[0m/s",
                f"↑\033[31m{fmt_bytes(up):>6s}\033[0m/s",
                f"LOAD \033[35m{load[0]:.1f}\033[0m",
            ]
            if bat:
                icon = "🔌" if bat.power_plugged else "🔋"
                parts.append(f"{icon} \033[1;33m{bat.percent}%\033[0m")
            parts.append(f"\033[2m{t}\033[0m")

            line = " │ ".join(parts)
            print(f"\r\033[K{line}", end="", flush=True)
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\r\033[K\033[?25h", end="")  # 清行 + 恢复光标


if __name__ == "__main__":
    main()
