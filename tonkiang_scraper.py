import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from base_scraper import BaseIPTVScraper, IPTVChannel
from config import TONKIANG_HEADERS

class TonkiangScraper(BaseIPTVScraper):
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.base_url = 'https://tonkiang.us'
        self.headers = TONKIANG_HEADERS

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
            city = response.text.strip()
            logging.info(f"成功获取动态city参数: {city}")  # 添加日志
            return city
        except Exception as e:
            logging.error(f"获取city参数失败: {e}")
            raise

    def _extract_channels_from_html(self, html: str) -> List[IPTVChannel]:
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
        channels = []
        logging.info("开始提取频道信息")  # 添加日志
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
            logging.error(f"请求失败，状态码: {response.status_code}")  # 添加日志
            return channels

        # 解析第一页
        soup = BeautifulSoup(response.text, 'html.parser')
        page_channels = self._extract_channels_from_html(response.text)
        channels.extend(page_channels)
        logging.info(f"第 1 页请求完毕，获取到 {len(page_channels)} 条数据，共 {page_count} 页")  # 添加日志

        # 提取l参数
        match = re.search(r'l=([a-f0-9]{9,})', response.text)
        if not match:
            logging.warning("未找到l参数，无法获取更多页面")  # 添加日志
            return channels
        
        l_param = match.group(1)
        
        # 获取实际的总页数
        max_available_pages = self._get_max_pages(soup)

        if page_count > 1:
            base_visit_url = f'{self.base_url}/?iptv={keyword}&l={l_param}'
            self.session.get(
                base_visit_url, 
                headers=self.headers,
                proxies=self.proxies if self.proxy_enabled else None
            )
            time.sleep(0.5)
            
            # 确定要获取的页面
            if random_mode:
                available_pages = list(range(2, max_available_pages + 1))
                pages_to_fetch = random.sample(
                    available_pages, 
                    min(page_count - 1, len(available_pages))
                )
                pages_to_fetch.sort()
                logging.info(f"随机模式已启用，将从 {max_available_pages} 页中随机抓取以下页面：{pages_to_fetch}")  # 添加日志
            else:
                pages_to_fetch = range(2, min(page_count + 1, max_available_pages + 1))
        
            # 获取其他页面
            for page in pages_to_fetch:
                url = f'{self.base_url}/?page={page}&iptv={keyword}&l={l_param}'
                response = self.session.get(
                    url,
                    headers=self.headers,
                    proxies=self.proxies if self.proxy_enabled else None
                )
                
                if response.status_code == 200:
                    page_channels = self._extract_channels_from_html(response.text)
                    channels.extend(page_channels)
                    logging.info(f"第 {page} 页请求完毕，获取到 {len(page_channels)} 条数据")  # 添加日志
                else:
                    logging.error(f"第 {page} 页请求失败，状态码: {response.status_code}")  # 添加日志
        
        return channels

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
                logging.debug(f"无效响应[{response.status_code}]: {channel.url}")  # 添加日志
                return False

            chunk = response.raw.read(512, decode_content=True)
            if not chunk:
                logging.debug(f"空数据响应: {channel.url}")  # 添加日志
                return False

            # 验证M3U8文件特征
            if b'#EXTM3U' in chunk[:128]:
                logging.debug(f"检测到M3U8文件: {channel.url}")  # 添加日志

            response_time = time.time() - start_time
            channel.response_time = response_time
            return True
        except Exception as e:
            logging.debug(f"连接错误 {channel.url}: {str(e)}")  # 添加日志
            return False
        finally:
            if 'response' in locals():
                response.close()

    def _get_max_pages(self, soup) -> int:
        """从页面中提取最大页数"""
        max_available_pages = 15  # 默认值
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
                max_available_pages = max(page_numbers)
                logging.info(f"检测到总页数: {max_available_pages}")
        return max_available_pages