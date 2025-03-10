from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class IPTVChannel:
    channel_name: str = ''
    url: str = ''
    date: Optional[str] = None
    location: Optional[str] = None
    resolution: Optional[str] = None
    response_time: Optional[float] = None

class BaseIPTVScraper(ABC):
    def __init__(self):
        self.session = None
        self.proxies = None
        self.proxy_enabled = False

    @abstractmethod
    def fetch_channels(self, keyword: str, page_count: int, random_mode: bool = True) -> List[IPTVChannel]:
        """获取频道列表的抽象方法"""
        pass

    @abstractmethod
    def check_channel_availability(self, channel: IPTVChannel) -> bool:
        """检查频道可用性的抽象方法"""
        pass

    def set_proxy(self, proxy_url: str, proxy_type: str = 'http') -> None:
        """设置代理服务器"""
        if not proxy_url:
            self.proxy_enabled = False
            self.proxies = None
            return

        self.proxies = {
            'http': f'{proxy_type}://{proxy_url}',
            'https': f'{proxy_type}://{proxy_url}'
        }
        self.proxy_enabled = True

    @property
    def name(self) -> str:
        """获取数据源名称"""
        return self.__class__.__name__