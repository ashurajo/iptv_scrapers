import base64
import logging
import requests
from bs4 import BeautifulSoup
from typing import List
from base_scraper import BaseIPTVScraper, IPTVChannel
from config import HACKS_HEADERS
from urllib.parse import quote
import time

def generate_search_url(query: str) -> str:
    base64_str = base64.b64encode(query.encode('utf-8')).decode('utf-8')
    url_encoded = quote(base64_str)
    return f"https://iptvs.hacks.tools/api/search?query={url_encoded}"


class HacksScraper(BaseIPTVScraper):
    def __init__(self) -> None:
        super().__init__()
        self.session: requests.Session = requests.Session()
        self.base_url: str = "https://iptvs.hacks.tools"
        self.headers: dict = HACKS_HEADERS  # 使用配置中的请求头

    def fetch_channels(self, keyword: str, page_count: int, random_mode: bool = True) -> List[IPTVChannel]:
        """实现Hacks平台频道抓取的核心逻辑"""
        channels = []
        try:
            search_url = generate_search_url(keyword)
            logging.info(f"开始请求Hacks API: {search_url}")
            
            response = self.session.get(
                search_url,
                headers=self.headers,
                proxies=self.proxies if self.proxy_enabled else None,
                timeout=10
            )
            
            if response.status_code == 200:
                page_channels = self._parse_api_response(response.text)
                channels.extend(page_channels)
                logging.info(f"请求成功，获取到 {len(page_channels)} 条数据")
            else:
                logging.info(f"请求失败，状态码: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logging.info("Hacks API请求超时")
        except requests.exceptions.RequestException as e:
            logging.info(f"Hacks API网络请求异常: {str(e)}")
        except Exception as e:
            logging.info(f"抓取过程中发生异常: {str(e)}")
        
        return channels

    def _parse_api_response(self, html: str) -> List[IPTVChannel]:
        """解析HTML页面中的频道信息"""
        channels = []
        soup = BeautifulSoup(html, 'html.parser')
        
        for row in soup.select('table tr'):
            tds = row.find_all('td')
            if len(tds) < 6:
                continue

            channel_name = tds[0].get_text(strip=True)
            resolution = tds[1].get_text(strip=True)
            date = tds[3].get_text(strip=True)
            
            # 提取所有URL
            for url_tag in tds[4].find_all('a', class_='stream_url'):
                if url := url_tag.get('title', '').strip():
                    channels.append(IPTVChannel(
                        url=url,
                        channel_name=channel_name,
                        date=date,
                        resolution=resolution,
                        location=None, 
                        response_time=None 
                    ))
        
        return channels

    def check_channel_availability(self, channel: IPTVChannel) -> bool:
        """实现频道可用性检查"""
        response = None
        try:
            start_time = time.time()
            headers = self.headers.copy()
            headers['Accept-Encoding'] = 'gzip, deflate, br'
            
            # 设置更严格的超时控制
            response = self.session.get(
                channel.url,
                headers=headers,
                timeout=3,  # 固定3秒超时
                proxies=self.proxies if self.proxy_enabled else None,
                stream=False,
                allow_redirects=True,
                verify=False
            )
            
            if response.status_code not in (200, 206):
                return False

            # 获取响应内容，但限制读取大小
            try:
                content = response.content[:128].decode('utf-8', errors='ignore')

            except Exception as e:
                logging.info(f"内容解码错误: {channel.url}, {str(e)}")
                # 如果解码失败但状态码正常，可能是二进制流，也认为是有效的
                if response.status_code in (200, 206):
                    channel.response_time = round(time.time() - start_time, 2)
                    return True
                return False
            
            # 检查是否为M3U8格式
            if '#EXTM3U' in content and '#EXT-X-STREAM-INF' in content:
                
                # 解析内容获取真实URL
                lines = content.strip().split('\n')
                for line in lines:
                    if line.startswith('http'):
                        real_url = line.strip()
                        # 更新channel的URL为真实地址
                        channel.url = real_url
                        
                        # 测试真实URL
                        try:
                            real_response = self.session.get(
                                real_url,
                                headers=headers,
                                timeout=3,
                                verify=False,
                                stream=False
                            )
                            if real_response.status_code in (200, 206):
                                channel.response_time = round(time.time() - start_time, 2)
                                return True
                        except:
                            pass
                        break
            
            # 如果有内容，视为可用
            if content and len(content) > 10:
                channel.response_time = round(time.time() - start_time, 2)
                return True
                
            logging.info(f"无效内容: {channel.url}")
            return False
            
        except requests.exceptions.Timeout:
            logging.info(f"请求超时: {channel.url}")
            return False
        except requests.exceptions.ConnectionError:
            logging.info(f"连接错误: {channel.url}")
            return False
        except Exception as e:
            logging.info(f"连接错误 {channel.url}: {str(e)}")
            return False
        finally:
            if response:
                try:
                    response.close()
                except:
                    pass
