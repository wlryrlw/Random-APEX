# Apex Legends 英雄与武器生成器

这是一个娱乐向的 PyQt6 桌面应用，用于为 Apex Legends 三人小队随机分配不重复英雄和武器组合。

## 安装依赖

请使用 Python 3.8 或更高版本。
当前项目使用 PyQt6，旧版 Python 可能无法安装或运行。

```powershell
pip install -r requirements.txt
```

## 运行
# 命令行
```powershell
python apex_randomizer.py
```
# 运行 .bat文件

## 功能

- 为可编辑昵称的三名玩家生成各自的英雄和 2 把武器
- 支持排除空投武器
- 支持禁止双近战、双远程、双中距离等同类武器组合
- 支持英雄和武器的随机选择、优先热门、优先冷门三种权重模式
- 支持爬虫抓取英雄登场率或武器强度（以TTK为准），抓取失败时保留默认数据或上一次成功缓存
- 生成日志写入 `apex_roll_log.txt`，抓取日志写入 `apex_fetch_log.txt`

## 说明
- 英雄登场率抓取自 https://apexlegendsstatus.com/game-stats/legends-pick-rates/Diamond ，以钻石排位为准
- 武器强度抓取自文件目录下 `weapon.xlsx`，表格来自bilibili up主 @老葛你又在打电动
- 本应用仅供作者本人休闲娱乐使用，部分资源来源网络，如有侵权请联系bilibili @图图家的摄影师 删除