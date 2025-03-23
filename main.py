import tkinter as tk
import logging
from gui import IPTVScraperGUI

# 在此处添加新的抓取类
from tonkiang_scraper import TonkiangScraper
from allinone_scraper import AllinoneScraper
from config import VERSION, MAX_PAGE, LOG_CONFIG
from hacks_scraper import HacksScraper

# 添加requests库的连接池配置
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 在文件顶部添加导入
from iptv365_scraper import IPTV365Scraper

def main():
    # 配置requests的连接池
    session = requests.Session()
    retry_strategy = Retry(
        total=1,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 将session设置为默认session
    requests.Session = lambda: session
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_CONFIG['filename'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    # 抑制urllib3和requests的警告日志
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('requests').setLevel(logging.ERROR)
    logging.info(f"启动频道工具 v{VERSION}")
    
    root = tk.Tk()
    app = IPTVScraperGUI(root, version=VERSION, max_page=MAX_PAGE)
    
    # 创建多个抓取器实例
    # 在scrapers字典中添加新的抓取器
    scrapers = {
        "Tonkiang": TonkiangScraper(),
        "Allinone": AllinoneScraper(),
        "Hacks": HacksScraper(),
        "IPTV365": IPTV365Scraper()
    }

    if hasattr(app, 'set_scrapers'):
        app.set_scrapers(scrapers)
    else:
        logging.error("IPTVScraperGUI类缺少set_scrapers方法")
        raise AttributeError("IPTVScraperGUI类未定义set_scrapers方法")
    
    root.mainloop()

if __name__ == "__main__":
    main()


# pyinstaller app.spec