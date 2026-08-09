# termdash

一条简洁的终端系统状态栏，实时刷新。

```text
zhongdeMacBook-Air │ CPU  23.5% │ MEM  82.0% │ DSK   5.3% │ ↓  1.2K/s │ ↑ 456B/s │ LOAD 2.1 │ 🔌 100% │ 14:30:00
```

## 安装

```bash
pip install psutil
git clone https://github.com/zhzx2026/termdash.git
cd termdash && pip install .
```

## 使用

```bash
termdash
```

单行显示，每秒刷新，`Ctrl+C` 退出。

## 显示内容

| 项目 | 说明 |
|------|------|
| 主机名 | 当前主机 |
| CPU | CPU 使用率 |
| MEM | 内存使用率 |
| DSK | 根分区磁盘使用率 |
| ↓ / ↑ | 网络下载 / 上传速率 |
| LOAD | 系统负载 |
| 🔋 / 🔌 | 电池电量（笔记本） |
| 时间 | 当前时间 |
