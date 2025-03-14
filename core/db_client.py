import re
import json
import os
from datetime import datetime
import urllib.parse
from utils.link_manager import LinkPoolManager

class DBClient:
    def __init__(self, storage_type='file', base_path='data/policy_data'):
        self.storage_type = storage_type
        self.base_path = base_path
        self.db_type = 'default'
        os.makedirs(base_path, exist_ok=True)
        # 初始化链接管理器
        self.link_manager = LinkPoolManager()
        # 缓存URL与栏目名称的映射
        self.url_section_cache = {}

    def save_policy(self, data):
        if self.storage_type == 'file':
            self._save_to_file(data)
        
    def _save_to_file(self, data):
        # 修复文件名生成逻辑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data.get('publish_date', 'nodate')}_{timestamp}.json"
        
        # 清理文件名中的非法字符
        filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
        
        # 获取栏目名称
        source_url = data.get('source_url', '')
        section_name = data.get('section_name')  # 优先使用传入的栏目名称
        
        if not section_name:
            # 如果没有传入栏目名称，则尝试从URL确定
            section_name = self._get_section_name(source_url)
        
        # 构建保存路径
        save_path = os.path.join(self.base_path, self.db_type, section_name, str(datetime.today().date()))
        os.makedirs(save_path, exist_ok=True)
        
        with open(os.path.join(save_path, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_section_name(self, url):
        """根据URL动态确定政策栏目名称"""
        # 先检查缓存
        if url in self.url_section_cache:
            return self.url_section_cache[url]
        
        # 解析URL路径
        path = urllib.parse.urlparse(url).path
        
        # 从所有已知的链接库中查找匹配
        for site_name in self._get_all_site_names():
            links = self.link_manager.get_site_links(site_name)
            for link in links:
                link_url = link.get('url', '')
                link_path = urllib.parse.urlparse(link_url).path
                
                # 如果URL路径包含链接路径，则认为属于该栏目
                if link_path and link_path in path:
                    section_name = link.get('name', '未知栏目')
                    # 缓存结果
                    self.url_section_cache[url] = section_name
                    return section_name
        
        # 如果没有匹配的栏目，使用URL的最后一级目录名
        parts = [p for p in path.split('/') if p]
        if parts:
            section_name = parts[-1]
            self.url_section_cache[url] = section_name
            return section_name
        
        # 默认返回"其他"
        return "其他"
    
    def _get_all_site_names(self):
        """获取所有已知的网站名称"""
        # 获取链接库目录下的所有文件
        link_pool_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'link_pool')
        if not os.path.exists(link_pool_dir):
            return []
            
        site_names = []
        for filename in os.listdir(link_pool_dir):
            if filename.endswith('.json') or filename.endswith('.csv'):
                site_names.append(os.path.splitext(filename)[0])
        
        return site_names