import tkinter as tk
import logging
from gui import IPTVScraperGUI

# 在此处添加新的抓取类
from tonkiang_scraper import TonkiangScraper
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

    if hasattr(app, 'set_scrapers'):
        app.set_scrapers(scrapers)
    else:
        logging.error("IPTVScraperGUI类缺少set_scrapers方法")
        raise AttributeError("IPTVScraperGUI类未定义set_scrapers方法")
    
    root.mainloop()

if __name__ == "__main__":
    main()


# pyinstaller app.spec