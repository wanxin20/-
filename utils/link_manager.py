import os
import json
import csv
from datetime import datetime
import pandas as pd
from utils.logger import setup_logger

class LinkPoolManager:
    def __init__(self, base_path='data/link_pool'):
        self.logger = setup_logger('LinkPoolManager')
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        
    # 在现有代码中添加深圳政府网站的处理逻辑
    def get_site_links(self, site_name):
        """获取指定网站的链接列表"""
        file_path = self._get_file_path(site_name)
        if not os.path.exists(file_path):
            self.logger.error(f"链接库文件不存在: {file_path}")
            return []
            
        if file_path.endswith('.json'):
            return self._read_json_links(file_path)
        elif file_path.endswith('.csv'):
            return self._read_csv_links(file_path)
        else:
            self.logger.error(f"不支持的链接库文件格式: {file_path}")
            return []
    
    def update_crawl_time(self, site_name, url=None):
        """更新指定网站或URL的爬取时间"""
        file_path = self._get_file_path(site_name)
        if not os.path.exists(file_path):
            self.logger.error(f"链接库文件不存在: {file_path}")
            return False
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if file_path.endswith('.json'):
            return self._update_json_crawl_time(file_path, url, current_time)
        elif file_path.endswith('.csv'):
            return self._update_csv_crawl_time(file_path, url, current_time)
        else:
            self.logger.error(f"不支持的链接库文件格式: {file_path}")
            return False
    
    def _get_file_path(self, site_name):
        """获取链接库文件路径"""
        # 先尝试直接匹配文件名
        for ext in ['.json', '.csv']:
            file_path = os.path.join(self.base_path, f"{site_name}{ext}")
            if os.path.exists(file_path):
                return file_path
        
        # 如果没有直接匹配，尝试模糊匹配
        for filename in os.listdir(self.base_path):
            if site_name.lower() in filename.lower():
                return os.path.join(self.base_path, filename)
        
        # 默认返回JSON格式路径
        return os.path.join(self.base_path, f"{site_name}.json")
    
    def _read_json_links(self, file_path):
        """读取JSON格式的链接库"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            links = []
            if 'policy_sections' in data:
                for section in data['policy_sections']:
                    links.append({
                        'name': section.get('name', ''),
                        'url': section.get('url', ''),
                        'priority': section.get('priority', 99),
                        'last_crawled': section.get('last_crawled'),
                        'crawl_frequency': section.get('crawl_frequency', data.get('crawl_frequency', 'daily'))
                    })
            return links
        except Exception as e:
            self.logger.error(f"读取JSON链接库失败: {str(e)}")
            return []
    
    def _read_csv_links(self, file_path):
        """读取CSV格式的链接库"""
        try:
            links = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    links.append({
                        'name': row.get('名称', ''),
                        'url': row.get('链接', ''),
                        'priority': int(row.get('优先级', 99)),
                        'last_crawled': row.get('上次爬取时间'),
                        'crawl_frequency': row.get('爬取频率', 'daily')
                    })
            return links
        except Exception as e:
            self.logger.error(f"读取CSV链接库失败: {str(e)}")
            return []
    
    def _update_json_crawl_time(self, file_path, url, current_time):
        """更新JSON格式链接库的爬取时间"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if url is None:
                # 更新整个网站的爬取时间
                data['last_crawled'] = current_time
            else:
                # 更新特定URL的爬取时间
                for section in data.get('policy_sections', []):
                    if section.get('url') == url:
                        section['last_crawled'] = current_time
                        break
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"更新JSON链接库爬取时间失败: {str(e)}")
            return False
    
    def _update_csv_crawl_time(self, file_path, url, current_time):
        """更新CSV格式链接库的爬取时间"""
        try:
            df = pd.read_csv(file_path)
            
            if url is None:
                # 更新整个网站的爬取时间
                df['上次爬取时间'] = current_time
            else:
                # 更新特定URL的爬取时间
                df.loc[df['链接'] == url, '上次爬取时间'] = current_time
            
            df.to_csv(file_path, index=False, encoding='utf-8')
            
            return True
        except Exception as e:
            self.logger.error(f"更新CSV链接库爬取时间失败: {str(e)}")
            return False