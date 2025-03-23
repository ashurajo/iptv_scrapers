import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Callable, Dict, Any

from base_scraper import IPTVChannel, BaseIPTVScraper


class SpeedTester:
    
    def __init__(self, scraper: BaseIPTVScraper, progress_callback: Callable[[str, int, int], None] | None = None):
        self.scraper = scraper
        self.progress_callback = progress_callback
    
    def test_channels(self, channels: List[IPTVChannel], max_workers: int = 20) -> Tuple[List[IPTVChannel], Dict[str, Any]]:
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
            # 提交所有任务并获取future对象
            futures = {executor.submit(self._check_channel, channel): channel for channel in channels}
            
            try:
                # 添加进度停滞检测
                last_completed = 0
                last_progress_time = time.time()
                stall_timeout = 6 
                
                # 使用as_completed而不是设置总体超时
                for future in as_completed(futures):
                    # 检查是否停滞
                    current_time = time.time()
                    if completed > last_completed:
                        last_completed = completed
                        last_progress_time = current_time
                    elif current_time - last_progress_time > stall_timeout:
                        logging.info(f"测速进度已停滞 {stall_timeout} 秒，终止当前批次测试")
                        break
                    
                    completed += 1
                    try:
                        channel, is_accessible = future.result(timeout=3)  # 单个任务超时
                        if is_accessible:
                            accessible_channels.append(channel)
                    except TimeoutError:
                        logging.info(f"任务执行超时")
                    except Exception as e:
                        logging.info(f"测速任务异常: {str(e)}")
                    finally:
                        if self.progress_callback:
                            self.progress_callback("测速中", completed, total)
            except Exception as e:
                logging.info(f"测速过程发生异常: {str(e)}")
            finally:
                # 强制关闭所有任务
                for future in futures:
                    future.cancel()
                
                executor.shutdown(wait=False, cancel_futures=True)
                futures.clear()
                
                # 更新进度
                if self.progress_callback:
                    self.progress_callback("测速完成", completed, total)
        
        # 按响应时间排序
        accessible_channels.sort(key=lambda x: x.response_time)
        logging.info(f"测速完成，共 {len(accessible_channels)}/{completed} 个频道可用 (总计 {total} 个)")
        
        return accessible_channels, {
            "total": total,
            "tested": completed,
            "accessible": len(accessible_channels)
        }
    
    def _check_channel(self, channel: IPTVChannel) -> Tuple[IPTVChannel, bool]:
        is_accessible = self.scraper.check_channel_availability(channel)
        return channel, is_accessible