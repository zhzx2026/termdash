# termdash

macOS 菜单栏系统状态，简洁优雅。

```text
  C:23% │ M:80% │ D:5% │ 100%    ← macOS 顶部菜单栏显示
```

点击菜单栏图标展开详情。

## 安装

```bash
pip install psutil rumps
git clone https://github.com/zhzx2026/termdash.git
cd termdash && pip install .
```

## 使用

```bash
termdash
```

菜单栏即出现状态信息，每秒刷新。点击图标查看详情，菜单中选「退出」关闭。

> 如果菜单栏空间不足（刘海屏 MacBook），状态文字可能被系统折叠，可在菜单栏拖动调整位置。
