# 🖥️ termdash

一个好看的实时系统监控终端仪表盘。基于 Python + [Rich](https://github.com/Textualize/rich) + [psutil](https://github.com/giampaolo/psutil) 构建。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 特性

- 📋 系统基本信息（主机名、系统、内核、开机时间、CPU 核心数）
- ⚡ 实时资源占用（CPU / 内存 / 磁盘 进度条）
- 🌐 网络流量统计
- 🔥 占用最高的 TOP 5 进程
- 🎨 漂亮的富文本布局与颜色

## 🚀 安装

```bash
git clone https://github.com/zhzx2026/termdash.git
cd termdash
pip install -r requirements.txt
```

## 🎯 使用

```bash
# 直接运行
python -m termdash

# 自定义刷新间隔（秒）
python -m termdash --interval 1.5
python -m termdash -i 0.5
```

按 `Ctrl+C` 退出。

## 🛠 技术栈

- [Rich](https://github.com/Textualize/rich) — 终端富文本渲染
- [psutil](https://github.com/giampaolo/psutil) — 系统信息采集

## 📄 License

MIT
