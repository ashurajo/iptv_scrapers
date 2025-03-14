import re
import logging
import time
import random
from typing import List

import requests
from bs4 import BeautifulSoup
from base_scraper import BaseIPTVScraper, IPTVChannel
from config import ALLINONE_HEADERS

class IPTVSearchScraper(BaseIPTVScraper):
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.base_url = 'https://www.iptv-search.com'
        self.headers = ALLINONE_HEADERS

    def _extract_channels_from_html(self, html: str) -> List[IPTVChannel]:
        soup = BeautifulSoup(html, 'html.parser')
        channels = []

        for card in soup.find_all('div', class_='channel card'):
            # 频道名称
            name_tag = card.find('div', class_='channel-name')
            channel_name = name_tag.get_text(strip=True) if name_tag else '未知频道'

            # 频道URL
            url_tag = card.find('span', class_='link-text')
            channel_url = url_tag.get_text(strip=True) if url_tag else None

            # 日期信息
            date_tag = card.find('span', class_='date-text')
            date = date_tag.get_text(strip=True) if date_tag else None

            # 地区信息（根据新要求改为location-tag）
            location_tag = card.find('span', class_='location-tag') or card.find('span', class_='group-text')
            location = location_tag.get_text(strip=True) if location_tag else None

            # 分辨率信息（提取title属性）
            res_tag = card.find('span', class_='resolution-text')
            resolution = res_tag['title'] if res_tag and res_tag.has_attr('title') else None

            if channel_url:
                channels.append(IPTVChannel(
                    channel_name=channel_name,
                    url=channel_url,
                    date=date,
                    location=location,
                    resolution=resolution
                ))
        return channels

    def _get_max_pages(self, soup) -> int:
        """从分页控件获取最大页数"""
        try:
            # 优先从input的max属性获取
            page_input = soup.find('input', {'name': 'page'})
            if page_input and page_input.has_attr('max'):
                return int(page_input['max'])

            # 备选方案：从最后的分页链接获取
            last_page = soup.find('a', href=re.compile(r'page=\d+$'))
            if last_page:
                match = re.search(r'page=(\d+)', last_page['href'])
                return int(match.group(1)) if match else 1
        except Exception as e:
            pass
        return 1

    def fetch_channels(self, keyword: str, page_count: int, random_mode: bool = True) -> List[IPTVChannel]:
        channels = []
        logging.info("开始提取频道信息")  # 添加日志
        try:
            url = f"{self.base_url}/search/?q={keyword}"
            response = self.session.get(url, headers=self.headers)

            if response.status_code != 200:
                logging.error(f"首页请求失败，状态码: {response.status_code}")
                return channels

            # 解析第一页
            soup = BeautifulSoup(response.text, 'html.parser')
            page_channels = self._extract_channels_from_html(response.text)
            channels.extend(page_channels)
            max_pages = self._get_max_pages(soup)
            logging.info(f"第 1 页请求完毕，获取到 {len(page_channels)} 条数据，总页数限制：{max_pages}")

            # 处理分页
            if page_count > 1:
                pages_to_fetch = self._get_target_pages(page_count, max_pages, random_mode)
                logging.info(f"随机模式 {'已' if random_mode else '未'} 启用，将抓取以下页面：{pages_to_fetch}")

                for page in pages_to_fetch:
                    start_time = time.time()
                    page_url = f"{self.base_url}/search/?q={keyword}&page={page}"
                    response = self.session.get(page_url, headers=self.headers)
                    cost_time = time.time() - start_time

                    if response.status_code == 200:
                        page_channels = self._extract_channels_from_html(response.text)
                        channels.extend(page_channels)
                        logging.info(f"第 {page} 页请求成功（耗时{cost_time:.2f}s），获取到 {len(page_channels)} 条数据")
                    else:
                        logging.warning(f"第 {page} 页请求失败，状态码: {response.status_code}（耗时{cost_time:.2f}s）")
                    time.sleep(random.uniform(0.5, 1.2))  # 添加随机延迟

        except Exception as e:
            logging.exception("抓取过程中发生异常")

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

    def _get_target_pages(self, target: int, max_pages: int, random_mode: bool) -> List[int]:
        if max_pages <= 1:
            return []

        available = list(range(2, max_pages + 1))
        if not random_mode:
            return available[:target - 1]

        return random.sample(available, min(target - 1, len(available)))