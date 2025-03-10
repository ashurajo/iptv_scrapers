import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from .base_scraper import BaseIPTVScraper, IPTVChannel

class TonkiangScraper(BaseIPTVScraper):
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.base_url = 'https://tonkiang.us'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }

    def _get_city_param(self) -> str:
        """获取动态city参数"""
        ac_headers = {
            'referer': f'{self.base_url}/?',
            'user-agent': self.headers['User-Agent'],
        }
        try:
            response = self.session.get(
                f"{self.base_url}/ag.php?s=ai&c=ch",
                headers=ac_headers,
                proxies=self.proxies if self.proxy_enabled else None,
            )
            return response.text.strip()
        except Exception as e:
            logging.error(f"获取city参数失败: {e}")
            raise

    def _extract_channels_from_html(self, html: str) -> List[IPTVChannel]:
        """从HTML中提取频道信息"""
        channels = []
        soup = BeautifulSoup(html, 'html.parser')
        
        for resultplus_div in soup.find_all('div', class_='resultplus'):
            tba_tags = resultplus_div.find_all('tba')
            if not tba_tags:
                continue

            channel_div = resultplus_div.find('div', class_='channel')
            channel_name = ""
            if channel_div:
                tip_div = channel_div.find('div', class_='tip')
                channel_name = tip_div.text.strip() if tip_div else "未知频道"

            info_div = resultplus_div.find('div', style='font-size: 10px; color: #aaa;')
            date = location = resolution = None
            if info_div:
                info_text = info_div.get_text(strip=True)
                parts = [p.strip() for p in info_text.split('•') if p.strip()]
                if len(parts) >= 1:
                    date_location = parts[0].split()
                    date = date_location[0] if len(date_location) > 0 else None
                    location = date_location[1] if len(date_location) > 1 else None
                if len(parts) >= 2:
                    resolution = parts[1].split()[0] if ' ' in parts[1] else parts[1]

            for tba_tag in tba_tags:
                url = tba_tag.text.strip()
                if url and re.match(r'^(http|rtmp|mms)://', url, re.I):
                    channel = IPTVChannel(
                        channel_name=channel_name,
                        url=url,
                        date=date,
                        location=location,
                        resolution=resolution
                    )
                    channels.append(channel)

        return channels

    def fetch_channels(self, keyword: str, page_count: int, random_mode: bool = True) -> List[IPTVChannel]:
        """获取频道列表"""
        channels = []
        city = self._get_city_param()
        
        # 获取第一页和l参数
        post_data = {"seerch": keyword, "Submit": "+", "city": city}
        response = self.session.post(
            self.base_url,
            headers=self.headers,
            data=post_data,
            proxies=self.proxies if self.proxy_enabled else None
        )

        if response.status_code != 200:
            return channels

        # 提取l参数
        match = re.search(r'l=([a-f0-9]{9,})', response.text)
        l_param = match.group(1) if match else ""

        # 提取总页数
        soup = BeautifulSoup(response.text, 'html.parser')
        max_pages = self._get_max_pages(soup)
        
        # 处理第一页数据
        channels.extend(self._extract_channels_from_html(response.text))

        if page_count > 1:
            # 建立会话
            self.session.get(
                f'{self.base_url}/?iptv={keyword}&l={l_param}',
                headers=self.headers,
                proxies=self.proxies if self.proxy_enabled else None
            )
            time.sleep(0.5)

            # 确定要抓取的页面
            if random_mode:
                available_pages = list(range(2, max_pages + 1))
                pages_to_fetch = random.sample(
                    available_pages,
                    min(page_count - 1, len(available_pages))
                )
                pages_to_fetch.sort()
            else:
                pages_to_fetch = range(2, min(page_count + 1, max_pages + 1))

            # 抓取后续页面
            for page in pages_to_fetch:
                url = f'{self.base_url}/?page={page}&iptv={keyword}&l={l_param}'
                try:
                    response = self.session.get(
                        url,
                        headers=self.headers,
                        proxies=self.proxies if self.proxy_enabled else None
                    )
                    if response.status_code == 200:
                        channels.extend(self._extract_channels_from_html(response.text))
                except Exception as e:
                    logging.error(f"请求第 {page} 页失败: {e}")

        return channels

    def _get_max_pages(self, soup: BeautifulSoup) -> int:
        """获取最大页数"""
        max_pages = 15  # 默认值
        page_links = soup.find_all('a', href=re.compile(r'\?page=\d+.*$'))
        if page_links:
            page_numbers = []
            for link in page_links:
                page_match = re.search(r'page=(\d+)', link['href'])
                if page_match:
                    try:
                        page_numbers.append(int(page_match.group(1)))
                    except ValueError:
                        continue
            if page_numbers:
                max_pages = max(page_numbers) - 1
        return max_pages

    def check_channel_availability(self, channel: IPTVChannel) -> bool:
        """检查频道可用性"""
        try:
            start_time = time.time()
            response = self.session.get(
                channel.url,
                headers=self.headers,
                timeout=(3.05, 4.5),
                proxies=self.proxies if self.proxy_enabled else None,
                stream=True
            )

            if response.status_code not in (200, 206):
                return False

            chunk = response.raw.read(512, decode_content=True)
            if not chunk:
                return False

            channel.response_time = time.time() - start_time
            return True

        except Exception as e:
            logging.debug(f"连接错误 {channel.url}: {str(e)}")
            return False
        finally:
            if 'response' in locals():
                response.close()