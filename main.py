import tkinter as tk
import logging
from gui import IPTVScraperGUI
from tonkiang_scraper import TonkiangScraper
# 导入新的抓取器
from allinone_scraper import AllinoneScraper
from config import VERSION, MAX_PAGE, LOG_CONFIG


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_CONFIG['filename'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info(f"启动频道工具 v{VERSION}")
    
    root = tk.Tk()
    app = IPTVScraperGUI(root, version=VERSION, max_page=MAX_PAGE)
    
    # 创建多个抓取器实例
    scrapers = {
        "Tonkiang": TonkiangScraper(),
        "Allinone": AllinoneScraper()
    }
    
    # 使用set_scrapers方法设置抓取器，而不是直接设置属性
    if hasattr(app, 'set_scrapers'):
        app.set_scrapers(scrapers)
    else:
        logging.error("IPTVScraperGUI类缺少set_scrapers方法")
        raise AttributeError("IPTVScraperGUI类未定义set_scrapers方法")
    
    root.mainloop()

if __name__ == "__main__":
    main()


# pyinstaller app.spec