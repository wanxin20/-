import random
from utils.anti_spider import get_random_ua

class AntiSpiderMiddleware:
    def process_request(self, request, spider):
        request.headers['User-Agent'] = get_random_ua()
        request.meta['proxy'] = random.choice(spider.proxy_pool) if hasattr(spider, 'proxy_pool') else None