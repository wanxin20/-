import json
import re
from urllib.parse import urljoin
from lxml import html
from spiders.base_spider import BaseSpider
from scrapy.http import Request, HtmlResponse
from datetime import datetime
import requests

class WanxinInfoSpider(BaseSpider):
    """万信人员信息网站爬虫"""
    def __init__(self, config_path):
        super().__init__(config_path)
        self.name = "wanxin_info_spider"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.current_section = None
        # 修正网站URL
        self.start_urls = ["https://wanxin20.github.io/ceshi/"]
    
    # 添加start_requests方法
    def start_requests(self, start_urls=None):
        """爬虫入口方法，处理请求"""
        self.logger.info(f"开始爬取万信人员信息")
        
        if not start_urls:
            start_urls = self.start_urls
        
        results = []
        for url in start_urls:
            try:
                self.logger.info(f"爬取URL: {url}")
                # 创建自定义会话
                session = requests.Session()
                # 设置代理（如果需要）
                if hasattr(self.config, 'get') and self.config.get('proxy'):
                    session.proxies = {
                        'http': self.config['proxy'],
                        'https': self.config['proxy']
                    }
                
                # 发送请求
                response = session.get(
                    url, 
                    headers=self.headers,
                    verify=False,
                    timeout=30
                )
                response.raise_for_status()
                
                # 创建Scrapy风格的Response对象
                html_response = HtmlResponse(
                    url=url,
                    body=response.content,
                    encoding='utf-8'
                )
                
                # 解析页面
                page_results = self.parse_list(html_response)
                results.extend(page_results)
                
            except Exception as e:
                self.logger.error(f"爬取URL失败: {url} - {str(e)}")
        
        return results

    # 确保parse_list和parse_detail方法正确实现
    def parse_list(self, response):
        """解析列表页，直接提取人员信息"""
        self.logger.info(f"正在解析人员列表页: {response.url}")
        
        try:
            # 获取所有人员信息项
            person_items = response.xpath(self.config['list_rules']['person_items'])
            self.logger.info(f"找到 {len(person_items)} 条人员信息")
            
            # 由于这是单页面网站，我们直接在这里解析详情
            results = []
            for person in person_items:
                # 直接解析每个人员信息
                detail_rules = self.config['detail_rules']
                
                name = person.xpath(detail_rules['name']).get('').strip()
                age = person.xpath(detail_rules['age']).get('').strip()
                position = person.xpath(detail_rules['position']).get('').strip()
                department = person.xpath(detail_rules['department']).get('').strip()
                
                person_info = {
                    'name': name,
                    'age': age,
                    'position': position,
                    'department': department,
                    'source_url': response.url,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                results.append(person_info)
            
            # 保存结果
            for person_data in results:
                self._save_person_data(person_data)
                
            return results
        except Exception as e:
            self.logger.error(f"解析人员列表页失败: {str(e)}")
            return []
    
    def parse_detail(self, response):
        """解析人员详情信息"""
        try:
            # 尝试从meta中获取person_html
            person_html = response.meta.get('person_html', '')
        except AttributeError:
            # 如果response没有meta属性，则尝试直接从response中提取人员信息
            self.logger.warning("Response没有meta属性，尝试直接从页面提取人员信息")
            person_items = response.xpath(self.config['list_rules']['person_items'])
            if not person_items:
                self.logger.error("未找到人员信息项")
                return
            
            # 处理每个人员信息项
            results = []
            for person in person_items:
                # 直接使用当前person元素进行解析
                detail_rules = self.config['detail_rules']
                
                name = person.xpath(detail_rules['name']).get('').strip()
                age = person.xpath(detail_rules['age']).get('').strip()
                position = person.xpath(detail_rules['position']).get('').strip()
                department = person.xpath(detail_rules['department']).get('').strip()
                
                # 构建结构化数据
                person_data = {
                    'name': name,
                    'age': age,
                    'position': position,
                    'department': department,
                    'source_url': response.url,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                self.logger.info(f"成功解析人员信息: {name} - {position} - {department}")
                
                # 保存数据
                self._save_person_data(person_data)
                results.append(person_data)
            
            return results
            
        if not person_html:
            self.logger.error("未找到人员HTML数据")
            return
        
        # 原有的处理逻辑保持不变
        # 将HTML字符串解析为lxml元素
        person_element = html.fromstring(person_html)
        
        # 使用XPath提取信息
        detail_rules = self.config['detail_rules']
        
        name = self._extract_text(person_element, detail_rules['name'])
        age = self._extract_text(person_element, detail_rules['age'])
        position = self._extract_text(person_element, detail_rules['position'])
        department = self._extract_text(person_element, detail_rules['department'])
        
        # 构建结构化数据
        person_data = {
            'name': name,
            'age': age,
            'position': position,
            'department': department,
            'source_url': response.url,
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.logger.info(f"成功解析人员信息: {name} - {position} - {department}")
        
        # 保存数据
        self._save_person_data(person_data)
        
        return person_data

    def _extract_text(self, element, xpath):
        """从元素中提取文本"""
        result = element.xpath(xpath)
        return result[0].strip() if result else ""

    def _save_person_data(self, data):
        """保存人员数据"""
        try:
            # 使用数据库客户端保存
            collection = "wanxin_personnel"
            # 检查db对象是否有save_document方法，如果没有则尝试使用其他方法
            if hasattr(self.db, 'save_document'):
                self.db.save_document(collection, data)
            elif hasattr(self.db, 'insert_one'):
                self.db.insert_one(collection, data)
            else:
                self.logger.warning("数据库客户端没有合适的保存方法，仅保存到文件")
        except Exception as e:
            self.logger.error(f"保存到数据库失败: {str(e)}")
        
        # 同时保存到JSON文件
        import os
        
        # 确保目录存在
        save_dir = os.path.join('data', 'policy_data', 'wanxin_info', 
                               datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成文件名
        filename = f"{data['name']}_{data['department']}.json"
        file_path = os.path.join(save_dir, filename)
        
        # 保存JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"已保存人员数据到文件: {file_path}")