import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Callable, Dict, Any

from base_scraper import IPTVChannel, BaseIPTVScraper


class SpeedTester:
    """频道测速器类，负责测试IPTV频道的可用性和响应时间"""
    
    def __init__(self, scraper: BaseIPTVScraper, progress_callback: Callable[[str, int, int], None] | None = None):
        """
        初始化测速器
        
        Args:
            scraper: 用于测试频道的抓取器实例
            progress_callback: 进度回调函数，用于更新UI
        """
        self.scraper = scraper
        self.progress_callback = progress_callback
    
    def test_channels(self, channels: List[IPTVChannel], max_workers: int = 20) -> Tuple[List[IPTVChannel], Dict[str, Any]]:
        """
        测试频道列表的可用性和响应时间
        
        Args:
            channels: 要测试的频道列表
            max_workers: 最大并发测试数量
            
        Returns:
            Tuple[List[IPTVChannel], Dict]: 可访问的频道列表和结果统计
        """
        if not channels:
            logging.warning("没有频道可供测试")
            return [], {"total": 0, "accessible": 0}
        
        # 更新进度
        if self.progress_callback:
            self.progress_callback("开始测速", 0, len(channels))
        
        logging.info("开始测速检查频道可用性")
        accessible_channels = []
        total = len(channels)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._check_channel, channel): channel for channel in channels}
            for future in as_completed(futures):
                completed += 1
                try:
                    channel, is_accessible = future.result(timeout=5)
                    if is_accessible:
                        accessible_channels.append(channel)
                        logging.debug(f"频道可用: {channel.channel_name} - {channel.url}")
                except Exception as e:
                    logging.warning(f"测速任务异常: {str(e)}")
                finally:
                    if self.progress_callback:
                        self.progress_callback("测速中", completed, total)
        
        # 按响应时间排序
        accessible_channels.sort(key=lambda x: x.response_time)
        logging.info(f"测速完成，共 {len(accessible_channels)}/{total} 个频道可用")
        
        return accessible_channels, {
            "total": total,
            "accessible": len(accessible_channels)
        }
    
    def _check_channel(self, channel: IPTVChannel) -> Tuple[IPTVChannel, bool]:
        """检查单个频道可用性"""
        is_accessible = self.scraper.check_channel_availability(channel)
        return channel, is_accessible