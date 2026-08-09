# 🖥️ termdash

一个好看、可交互的实时系统监控终端仪表盘。基于 Python + [Textual](https://github.com/Textualize/textual) + [psutil](https://github.com/giampaolo/psutil) 构建。

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 特性

- 📋 **4 个页面**：概览 / 进程 / 磁盘 / 网络，用 `Tab` 或数字键 `1-4` 切换
- ⚡ 实时资源占用（CPU / 内存 / 磁盘 彩色进度条）
- 🔥 进程 TOP 50，支持方向键上下浏览
- 💾 所有磁盘分区详情
- 🌐 实时网络收发速度与总量
- 🎨 深色主题 + 圆角边框 + 高亮配色

## 🚀 安装

```bash
pip install rich textual psutil
git clone https://github.com/zhzx2026/termdash.git
cd termdash
pip install .
```

## 🎯 使用

```bash
termdash
```

或（不用安装）：

```bash
cd termdash
python3 -m termdash
```

## ⌨️ 快捷键

| 按键 | 功能 |
|------|------|
| `1` / `2` / `3` / `4` | 切换到 概览 / 进程 / 磁盘 / 网络 |
| `Tab` | 循环切换页面 |
| `↑` / `↓` | 进程列表上下移动 |
| `q` / `Ctrl+C` | 退出 |

## 🛠 技术栈

- [Textual](https://github.com/Textualize/textual) — 交互式终端 UI 框架
- [psutil](https://github.com/giampaolo/psutil) — 系统信息采集

## 📄 License

MIT
