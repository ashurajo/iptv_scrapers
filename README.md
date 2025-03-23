# IPTV频道抓取工具

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于Python 3.12 的IPTV频道抓取工具，支持多数据源搜索和速度测试。

## 功能特性

- 🕵️ 多数据源并行搜索
- ⚡ 实时速度测试
- 🖥️ 图形化界面操作
- 📦 一键打包为Windows可执行文件

## 项目结构

```text
iptv_scrapers/
├── main.py              # 程序入口
├── gui.py               # 图形界面实现
├── config.py            # 配置文件
├── app.spec             # 打包配置文件
├── requirements.txt     # 依赖库列表
├── scrapers/            # 抓取器模块
│   ├── base_scraper.py  # 抓取器基类
│   ├── tonkiang_scraper.py 
│   └── allinone_scraper.py
│   └── hacks_scraper.py
│   └── iptv365_scraper.py
└── build/               # 打包输出目录
```
## 快速开始
### 安装依赖
```text
pip freeze > requirements.txt
```
### 运行程序
```text
python main.py
```
## 添加新抓取器
1.新建新的类（例：new_scraper.py）
```text
from base_scraper import BaseScraper

class NewScraper(BaseScraper):
    def search(self, keyword, page=1):
        '''必须实现的抓取方法'''
        # 实现具体抓取逻辑
        return [
            {
                "name": "频道名称",
                "url": "直播源地址", 
                "resolution": "分辨率"
            }
        ]
        
```
2.在main.py注册抓取器
```text
# 文件顶部导入
from scrapers.new_scraper import NewScraper

# 修改main函数中的scrapers字典
def main():
    # ...其他代码...
    scrapers = {
        "NewSource": NewScraper(),
        # ...原有抓取器...
    }
```
## 打包指南
### 安装依赖
```text
pip install pyinstaller
```
### 使用spec文件打包
```text
pyinstaller app.spec
```
### 生成的可执行文件在dist目录中，包含：
- 自动识别依赖项
- 内置图标和版本信息
- 无控制台窗口模式

## 开源协议
[MIT License](https://opensource.org/licenses/MIT)
## 大模型声明
本项目原本为制作为 API 通过 Deepseek 大模型转为 GUI 形式，部分代码存在矛盾请谅解。