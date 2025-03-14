import random
import time
import logging
from datetime import datetime, timedelta

class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger('ProxyManager')
        self.proxies = []
        self.last_update = None
        self.update_interval = 3600  # 1小时更新一次代理列表
        self.enabled = False  # 添加启用/禁用标志
    
    def set_enabled(self, enabled):
        """设置是否启用代理"""
        self.enabled = enabled
    
    def get_proxy(self):
        """获取一个代理
        
        Returns:
            dict: 代理配置，格式为 {'http': 'http://ip:port', 'https': 'https://ip:port'}
        """
        # 如果代理列表为空或者已经过期，则更新代理列表
        if not self.proxies or (self.last_update and 
                               datetime.now() - self.last_update > timedelta(seconds=self.update_interval)):
            self._update_proxies()
        
        # 如果代理列表仍然为空，返回None
        if not self.proxies:
            return None
        
        # 随机选择一个代理
        proxy = random.choice(self.proxies)
        return {
            'http': f'http://{proxy}',
            'https': f'https://{proxy}'
        }
    
    def _update_proxies(self):
        """更新代理列表"""
        try:
            # 这里应该实现从代理服务获取代理列表的逻辑
            # 例如，从代理API获取，或者从本地文件读取
            
            # 示例：从本地文件读取代理列表
            # with open('proxies.txt', 'r') as f:
            #     self.proxies = [line.strip() for line in f if line.strip()]
            
            # 示例：硬编码一些代理（仅用于演示）
            self.proxies = [
                '127.0.0.1:8080',  # 这只是一个示例，实际使用时应该替换为真实的代理
            ]
            
            self.last_update = datetime.now()
            self.logger.info(f"更新代理列表成功，共{len(self.proxies)}个代理")
            
        except Exception as e:
            self.logger.error(f"更新代理列表失败: {str(e)}")

# 用户代理列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36 Edg/91.0.864.71'
]

# 全局代理管理器实例
proxy_manager = ProxyManager()

def get_random_ua():
    """获取随机用户代理"""
    return random.choice(USER_AGENTS)

def get_proxy():
    """获取代理"""
    return proxy_manager.get_proxy()

def random_delay(min_seconds=1, max_seconds=3):
    """随机延迟一段时间，用于模拟人类行为"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay