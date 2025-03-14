import re
import hashlib
import logging
from bs4 import BeautifulSoup
from lxml import html
import requests
from urllib.parse import urlparse

class WebPageValidator:
    """网页结构验证器：用于判断页面是否发生变化"""
    
    def __init__(self):
        self.logger = logging.getLogger('WebPageValidator')
    
    def calculate_content_hash(self, content, xpath=None):
        """计算内容哈希值
        
        Args:
            content: HTML内容
            xpath: 可选，指定要计算哈希的内容区域XPath
            
        Returns:
            str: 内容的MD5哈希值
        """
        try:
            if xpath:
                # 如果提供了XPath，只计算特定区域的哈希
                tree = html.fromstring(content)
                elements = tree.xpath(xpath)
                if elements:
                    # 将所有匹配元素的文本内容连接起来
                    content_text = ' '.join([elem.text_content().strip() for elem in elements if elem.text_content()])
                else:
                    content_text = content
            else:
                # 否则计算整个页面的哈希，但去除一些动态内容
                soup = BeautifulSoup(content, 'lxml')
                
                # 移除脚本、样式和注释
                for script in soup(['script', 'style']):
                    script.extract()
                
                # 获取文本内容
                content_text = soup.get_text()
                
                # 规范化空白字符
                content_text = re.sub(r'\s+', ' ', content_text).strip()
            
            # 计算MD5哈希
            return hashlib.md5(content_text.encode('utf-8')).hexdigest()
            
        except Exception as e:
            self.logger.error(f"计算内容哈希失败: {str(e)}")
            return None
    
    def compare_dom_structure(self, old_content, new_content, key_elements):
        """比较两个页面的DOM结构是否发生变化
        
        Args:
            old_content: 旧的HTML内容
            new_content: 新的HTML内容
            key_elements: 关键元素的XPath列表
            
        Returns:
            bool: 如果结构发生变化返回True，否则返回False
        """
        try:
            old_tree = html.fromstring(old_content)
            new_tree = html.fromstring(new_content)
            
            for xpath in key_elements:
                old_elements = old_tree.xpath(xpath)
                new_elements = new_tree.xpath(xpath)
                
                # 检查元素数量是否变化
                if len(old_elements) != len(new_elements):
                    return True
                
                # 检查元素内容是否变化
                for i in range(len(old_elements)):
                    if old_elements[i].text_content() != new_elements[i].text_content():
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"比较DOM结构失败: {str(e)}")
            return True  # 出错时保守地认为结构已变化
    
    def should_use_proxy(self, url):
        """判断是否应该使用代理
        
        Args:
            url: 目标URL
            
        Returns:
            bool: 如果应该使用代理返回True，否则返回False
        """
        # 这里可以根据URL或其他条件决定是否使用代理
        # 例如，某些政府网站可能需要代理，而其他网站不需要
        domain = urlparse(url).netloc
        
        # 示例：对某些域名使用代理
        proxy_domains = [
            'www.gov.cn',
            'zwgk.mct.gov.cn'
        ]
        
        return domain in proxy_domains
        
    def get_site_validation_rules(self, url):
        """获取网站的验证规则
        
        Args:
            url: 目标URL
            
        Returns:
            dict: 包含验证规则的字典
        """
        domain = urlparse(url).netloc
        
        # 网站验证规则
        validation_rules = {
            'www.gov.cn': {
                'content_xpath': '//div[@class="article"]',
                'key_elements': ['//div[@class="article"]/h1', '//div[@class="pages-date"]']
            },
            'www.sz.gov.cn': {
                'content_xpath': '//div[@class="news_cont_d_wrap"]',
                'key_elements': ['//div[@class="news_cont_d_title"]', '//div[@class="news_cont-tools"]']
            },
            'wanxin20.github.io': {
                'content_xpath': '//div[@class="info-container"]',
                'key_elements': ['//div[@class="person-info"]']
            }
        }
        
        # 查找匹配的规则
        for site_domain, rules in validation_rules.items():
            if site_domain in domain:
                return rules
        
        # 默认规则
        return {
            'content_xpath': None,  # 使用整个页面
            'key_elements': ['//body']
        }
        
    def validate_page_structure(self, url, html_content):
        """验证页面结构是否符合预期
        
        Args:
            url: 目标URL
            html_content: HTML内容
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        domain = urlparse(url).netloc
        
        # 网站特征规则
        site_patterns = {
            'www.gov.cn': {
                'title_pattern': r'中国政府网|中华人民共和国中央人民政府',
                'content_xpath': '//div[@class="article"]',
            },
            'www.sz.gov.cn': {
                'title_pattern': r'深圳市人民政府',
                'content_xpath': '//div[@class="news_cont_d_wrap"]',
            },
            'wanxin20.github.io': {
                'title_pattern': r'人员信息列表',
                'content_xpath': '//div[@class="info-container"]',
            }
        }
        
        # 查找匹配的网站规则
        site_rule = None
        for site_domain, rule in site_patterns.items():
            if site_domain in domain:
                site_rule = rule
                break
        
        if not site_rule:
            return True, "未找到匹配的网站规则，跳过验证"
        
        # 解析HTML
        try:
            tree = html.fromstring(html_content)
            
            # 检查标题
            title = tree.xpath('//title/text()')
            title = title[0] if title else ""
            
            if site_rule.get('title_pattern') and not re.search(site_rule['title_pattern'], title):
                return False, f"页面标题不匹配: {title}"
            
            # 检查内容区域
            if site_rule.get('content_xpath'):
                content_elements = tree.xpath(site_rule['content_xpath'])
                if not content_elements:
                    return False, f"未找到内容区域: {site_rule['content_xpath']}"
            
            return True, "页面结构验证通过"
            
        except Exception as e:
            self.logger.error(f"验证过程出错: {str(e)}")
            return False, f"验证过程出错: {str(e)}"