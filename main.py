import tkinter as tk
import logging
from gui import IPTVScraperGUI
from tonkiang_scraper import TonkiangScraper
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
    scraper = TonkiangScraper()
    app.set_scraper(scraper)
    root.mainloop()

if __name__ == "__main__":
    main()


# pyinstaller app.spec