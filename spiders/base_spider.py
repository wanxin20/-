# 在文件顶部添加导入
import yaml
import json
from abc import ABC, abstractmethod
from urllib.parse import urljoin
from core.db_client import DBClient
from utils.logger import setup_logger
from utils.anti_spider import get_random_ua
from scrapy.http import HtmlResponse

class BaseSpider(ABC):
    def __init__(self, config_path):
        self.logger = setup_logger(self.__class__.__name__)
        self.db = DBClient()
        self.config = self._load_config(config_path)
        self.headers = {'User-Agent': get_random_ua()}

    @abstractmethod
    def parse_list(self, response):
        """解析列表页，返回详情页链接集合"""
        pass

    @abstractmethod
    def parse_detail(self, response):
        """解析详情页，返回结构化数据"""
        pass

    def process_response(self, response):
        """统一响应处理入口"""
        if 'parse_detail' in response.meta['callback'].__name__:
            return self.parse_detail(response)
        return self.parse_list(response)

    def _load_config(self, config_path):
        # 加载爬虫规则配置
        with open(config_path, 'r', encoding='utf-8') as f:
            # 这里需要根据实际配置文件格式解析
            return yaml.safe_load(f) if config_path.endswith('.yaml') else json.load(f)

    def _absolute_url(self, base_url, relative_path):
        return urljoin(base_url, relative_path)