# 全局配置
VERSION = "1.3.0"
MAX_PAGE = 5

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'filename': 'iptv_scraper.log',
    'encoding': 'utf-8'
}

# 通用请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

# 特定源的请求头
TONKIANG_HEADERS = {
    **DEFAULT_HEADERS,  # 继承通用请求头
    'Host': 'tonkiang.us',
    'Origin': 'https://tonkiang.us',
    'Referer': 'https://tonkiang.us'
}

# 可以继续添加其他源的请求头
# OTHER_SOURCE_HEADERS = {
#     **DEFAULT_HEADERS,
#     'specific-header': 'value'
# }