# 全局配置文件

# 请求配置
REQUEST_SETTINGS = {
    'timeout': 30,
    'verify_ssl': False,  # 是否验证SSL证书
    'retry_times': 3,     # 重试次数
    'retry_delay': 2,     # 重试延迟（秒）
}

# 默认请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 代理设置
PROXY_SETTINGS = {
    'enabled': False,  # 是否启用代理
    'proxy': 'http://127.0.0.1:7890',  # 代理地址
}

# 数据存储路径
DATA_PATHS = {
    'link_pool': 'data/link_pool',
    'policy_data': 'data/policy_data',
    'logs': 'logs',
}

# 监测服务配置
MONITOR_SETTINGS = {
    'check_interval': 60,  # 检查间隔（秒）
    'high_priority_threshold': 8,  # 高优先级阈值
}

# 爬虫配置
SPIDER_SETTINGS = {
    'default_config_path': 'config/spiders',
}