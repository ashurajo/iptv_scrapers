import tkinter as tk
import logging
from gui import IPTVScraperGUI  # 移除点号，使用简单导入
from tonkiang_scraper import TonkiangScraper
from config import VERSION, MAX_PAGE, LOG_CONFIG

def setup_logging():
    """配置日志系统"""
    # 先清除所有已有的处理器，避免重复日志
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG['level']),
        format=LOG_CONFIG['format'],
        handlers=[
            logging.FileHandler(LOG_CONFIG['filename'], encoding='utf-8')
            # 移除控制台处理器，让GUI自己处理日志显示
        ]
    )

def main():
    setup_logging()
    logging.info(f"启动频道工具 v{VERSION}")
    
    root = tk.Tk()
    app = IPTVScraperGUI(root, version=VERSION, max_page=MAX_PAGE)
    scraper = TonkiangScraper()
    app.set_scraper(scraper)
    root.mainloop()

if __name__ == "__main__":
    main()