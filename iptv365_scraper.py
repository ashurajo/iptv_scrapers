import json
import logging
import time
import requests
from typing import List
from base_scraper import BaseIPTVScraper, IPTVChannel
from config import IPTV365_HEADERS

class IPTV365Scraper(BaseIPTVScraper):
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.base_url = "https://search.iptv365.org/"
        self.headers = IPTV365_HEADERS

    def fetch_channels(self, keyword: str, page_count: int = 1, random_mode: bool = False) -> List[IPTVChannel]:
        """
        获取频道列表
        注意：此抓取器忽略page_count和random_mode参数，因为API不支持分页
        """
        channels = []
        logging.info(f"开始从 IPTV365 获取频道信息: {keyword}")

        try:
            payload = {
                "searchTerm": keyword
            }

            response = self.session.post(
                self.base_url,
                data=json.dumps(payload),
                headers=self.headers,
                proxies=self.proxies if self.proxy_enabled else None
            )

            if response.status_code != 200:
                logging.error(f"请求失败，状态码: {response.status_code}")
                return channels

            data = response.json()
            
            # 处理返回的数据
            for source in data:
                source_url = source.get("url", "")
                lines = source.get("lines", [])
                
                for line in lines:
                    # 解析频道信息
                    try:
                        channel_name, url = line.split(",", 1)
                        channel_name = channel_name.strip()
                        url = url.strip()
                        
                        # 检测并移除URL中$符号后的内容
                        if '$' in url:
                            url = url.split('$', 1)[0]
                        
                        if url:  # 确保URL不为空
                            channel = IPTVChannel(
                                channel_name=channel_name,
                                url=url,
                            )
                            channels.append(channel)
                    except ValueError:
                        logging.warning(f"无法解析频道信息: {line}")
                        continue

            logging.info(f"IPTV365抓取完成，共获取到 {len(data)} 个订阅源，{len(channels)} 个频道")

        except Exception as e:
            logging.error(f"抓取过程发生错误: {str(e)}")
            
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
                logging.debug(f"无效响应[{response.status_code}]: {channel.url}")
                return False

            chunk = response.raw.read(512, decode_content=True)
            if not chunk:
                logging.debug(f"空数据响应: {channel.url}")
                return False

            # 验证M3U8文件特征
            if b'#EXTM3U' in chunk[:128]:
                logging.debug(f"检测到M3U8文件: {channel.url}")

            response_time = time.time() - start_time
            channel.response_time = response_time
            return True
            
        except Exception as e:
            logging.debug(f"连接错误 {channel.url}: {str(e)}")
            return False
            
        finally:
            if 'response' in locals():
                response.close()