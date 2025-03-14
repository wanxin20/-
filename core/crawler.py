from spiders import SPIDERS
from utils.logger import setup_logger
import importlib

class CrawlerEngine:
    def __init__(self):
        self.logger = setup_logger('CrawlerEngine')
        self.active_spiders = []

    def load_spider(self, spider_name):
        if spider_name not in SPIDERS:
            raise ValueError(f"未注册的爬虫: {spider_name}")
        
        # 拆分类路径和配置路径
        class_path, config_path = SPIDERS[spider_name]
        module_path, class_name = class_path.rsplit('.', 1)
        
        # 动态导入并返回配置好的爬虫类
        module = __import__(module_path, fromlist=[class_name])
        spider_class = getattr(module, class_name)
        return spider_class, config_path  # 返回类引用和配置路径

    def start_crawling(self, spider_class, config_path):  # 修改方法签名
        spider = spider_class(config_path)  # 传递配置路径
        self.active_spiders.append(spider)
        
        # 添加实际爬取逻辑
        from utils.downloader import PageDownloader
        downloader = PageDownloader()
        
        # 从爬虫配置获取起始URL
        start_url = spider.config.get('start_urls', ['https://www.ndrc.gov.cn'])[0]
        
        # 处理列表页
        list_html = downloader.fetch(start_url, headers=spider.headers)
        if list_html:
            # 调用爬虫的解析方法
            if hasattr(spider, 'parse_list'):
                # 模拟Scrapy的response对象
                from scrapy.http import HtmlResponse
                response = HtmlResponse(url=start_url, body=list_html, encoding='utf-8')
                
                # 处理列表页返回的结果
                parse_results = spider.parse_list(response)
                
                # 检查返回类型
                if hasattr(parse_results, '__iter__') and not isinstance(parse_results, dict):
                    for result in parse_results:
                        # 如果是Request对象
                        if hasattr(result, 'url'):
                            # 处理详情页请求
                            detail_html = downloader.fetch(result.url, headers=spider.headers)
                            if detail_html:
                                detail_response = HtmlResponse(url=result.url, body=detail_html, encoding='utf-8')
                                spider.parse_detail(detail_response)
                        # 如果是字典类型，说明已经是解析好的数据
                        elif isinstance(result, dict):
                            self.logger.info(f"已获取解析好的数据: {result.get('name', '未知')}")
                        else:
                            self.logger.warning(f"未知的返回类型: {type(result)}")
    # 在CrawlerEngine类中添加新方法
    # 在CrawlerEngine类中修改start_crawling_with_url方法
    
    def start_crawling_with_url(self, spider_name, url, section_name=None):
        """使用指定URL启动爬虫"""
        self.logger.info(f"启动爬虫: {spider_name} - {url}")
        
        try:
            # 动态导入爬虫类
            try:
                # 先尝试从SPIDERS字典中加载
                spider_class, config_path = self.load_spider(spider_name)
            except (ValueError, KeyError) as e:
                self.logger.warning(f"从SPIDERS字典加载爬虫失败: {str(e)}，尝试直接导入")
                # 如果在SPIDERS中找不到，尝试直接导入
                module_name = f"spiders.{spider_name}"
                if spider_name.endswith('_spider'):
                    module_name = f"spiders.{spider_name}"
                else:
                    module_name = f"spiders.{spider_name}_spider"
                    
                try:
                    module = importlib.import_module(module_name)
                    # 获取爬虫类名（通常是蛇形命名转驼峰命名）
                    class_name = ''.join(word.capitalize() for word in spider_name.split('_'))
                    if not class_name.endswith('Spider'):
                        class_name += 'Spider'
                    spider_class = getattr(module, class_name)
                    config_path = f"config/spiders/{spider_name.replace('_spider', '')}.yaml"
                except (ImportError, AttributeError) as e:
                    self.logger.error(f"无法导入爬虫: {spider_name} - {str(e)}")
                    return False
            
            # 创建爬虫实例
            spider = spider_class(config_path)
            
            # 执行爬取
            return self._execute_crawl(spider, url, section_name)
            
        except Exception as e:
            self.logger.error(f"启动爬虫失败: {spider_name} - {url} - {str(e)}")
            return False
    
    def _execute_crawl(self, spider, url, section_name=None):
        """执行爬虫爬取任务"""
        try:
            # 设置当前栏目
            if hasattr(spider, 'current_section') and section_name:
                spider.current_section = section_name
            
            # 启动爬虫
            result = spider.start_requests(start_urls=[url])
            return True
        except Exception as e:
            self.logger.error(f"执行爬虫任务失败: {str(e)}")