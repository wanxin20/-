import os
import time
import hashlib
import threading
import requests
import logging
import json
import csv
import pandas as pd
import functools  # 添加这一行
from datetime import datetime, timedelta
from urllib.parse import urlparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils.validator import WebPageValidator
from utils.anti_spider import get_random_ua, get_proxy, random_delay
from core.crawler import CrawlerEngine
from core.scheduler import TaskScheduler
from utils.logger import setup_logger

class LinkPoolHandler(FileSystemEventHandler):
    """监听链接库文件变化的处理器"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        self.logger = setup_logger('LinkPoolHandler')
    
    def on_modified(self, event):
        """当链接库文件被修改时触发"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        self.logger.info(f"检测到链接库文件变化: {file_path}")
        
        # 从文件名提取网站名称
        filename = os.path.basename(file_path)
        site_name = os.path.splitext(filename)[0]
        
        # 通知监测器重新加载并检查该网站
        self.monitor.reload_site(site_name)
        self.monitor.check_site_update(site_name)

class PolicyMonitor:
    """政策网站监测器"""
    
    def __init__(self, link_pool_dir='data/link_pool', check_interval=300, verify_ssl=True):
        self.logger = setup_logger('PolicyMonitor')
        self.link_pool_dir = link_pool_dir
        self.default_check_interval = check_interval
        self.sites = {}
        self.validator = WebPageValidator()
        self.crawler_engine = CrawlerEngine()
        self.scheduler = TaskScheduler(self)
        self.running = False
        self.observer = None
        self.verify_ssl = verify_ssl  # 添加SSL验证控制
        
        # 创建一个自定义会话对象，用于处理特殊网站
        self.custom_session = self._create_custom_session()
        
        # 确保链接库目录存在
        os.makedirs(link_pool_dir, exist_ok=True)
        
        # 加载所有站点配置
        self.load_all_sites()
    
    def _create_custom_session(self):
        """创建一个自定义的requests会话对象，用于处理特殊网站"""
        session = requests.Session()
        
        # 配置更宽松的SSL设置
        from requests.packages.urllib3.util.ssl_ import create_urllib3_context
        context = create_urllib3_context()
        context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=5, pool_connections=10, pool_maxsize=10))
        
        # 设置默认超时时间
        session.request = functools.partial(session.request, timeout=30)
        
        # 设置默认请求头
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        return session
    
    def _check_section_update(self, site_name, section):
        """检查站点特定栏目的更新"""
        url = section.get('url')
        section_name = section.get('name', '未命名栏目')
        if not url:
            return False
        
        try:
            # 准备请求头
            headers = {
                'User-Agent': get_random_ua(),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            # 添加条件请求头
            if section.get('last_modified'):
                headers['If-Modified-Since'] = section['last_modified']
            if section.get('etag'):
                headers['If-None-Match'] = section['etag']
            
            # 获取代理
            proxies = get_proxy() if self.validator.should_use_proxy(url) else None
            
            # 特殊网站处理
            use_custom_session = False
            if 'sz.gov.cn' in url or 'wanxin20.github.io' in url:
                use_custom_session = True
                self.logger.info(f"使用自定义会话处理特殊网站: {url}")
            
            # 发送HEAD请求检查更新，使用verify_ssl参数
            # 添加重试机制
            max_retries = 5  # 增加重试次数
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if use_custom_session:
                        # 使用自定义会话
                        response = self.custom_session.head(
                            url, 
                            headers=headers, 
                            proxies=proxies, 
                            allow_redirects=True, 
                            verify=False  # 禁用SSL验证
                        )
                    else:
                        # 使用标准请求
                        response = requests.head(
                            url, 
                            headers=headers, 
                            proxies=proxies, 
                            timeout=15, 
                            allow_redirects=True, 
                            verify=False  # 禁用SSL验证
                        )
                    break  # 请求成功，跳出循环
                except (requests.exceptions.ConnectionError, requests.exceptions.SSLError) as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise  # 重试次数用完，抛出异常
                    self.logger.warning(f"请求失败，正在重试({retry_count}/{max_retries}): {site_name} - {section_name} ({url}) - {str(e)}")
                    time.sleep(2 * retry_count)  # 指数退避，等待时间随重试次数增加
            
            # 更新下次检查时间
            section['next_check'] = datetime.now().timestamp() + section.get('check_interval', self.default_check_interval)
            
            # 处理响应
            if response.status_code == 304:
                self.logger.info(f"[未更新] {site_name} - {section_name} ({url})")
                return False
            
            # 如果服务器返回200，需要进一步验证内容是否变化
            if response.status_code == 200:
                # 保存响应头信息
                if 'Last-Modified' in response.headers:
                    section['last_modified'] = response.headers['Last-Modified']
                if 'ETag' in response.headers:
                    section['etag'] = response.headers['ETag']
                
                # 获取完整内容并验证哈希
                content_changed = self._verify_content_change(url, section)
                
                if content_changed:
                    self.logger.info(f"[内容更新] {site_name} - {section_name} ({url})")
                    self._trigger_crawler(site_name, url, section_name)
                    self._update_site_status(site_name)
                    return True
                else:
                    self.logger.info(f"[内容未变] {site_name} - {section_name} ({url})")
                    return False
            
            self.logger.warning(f"[检查异常] {site_name} - {section_name} ({url}) - HTTP状态码: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求异常: {site_name} - {section_name} ({url}) - {str(e)}")
            # 请求失败时使用指数退避策略
            backoff = min(section.get('check_interval', self.default_check_interval) * 2, 86400)  # 最长一天
            section['next_check'] = datetime.now().timestamp() + backoff
            return False
        except Exception as e:
            self.logger.error(f"检查更新异常: {site_name} - {section_name} ({url}) - {str(e)}")
            return False
    def _check_site_update_direct(self, site_name, site_data):
        """检查单链接站点的更新"""
        url = site_data.get('url')
        if not url:
            return False
        
        self.logger.info(f"检查更新: {site_name} ({url})")
        
        try:
            # 准备请求头
            headers = {
                'User-Agent': get_random_ua(),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            # 添加条件请求头
            if site_data.get('last_modified'):
                headers['If-Modified-Since'] = site_data['last_modified']
            if site_data.get('etag'):
                headers['If-None-Match'] = site_data['etag']
            
            # 获取代理(如果启用)
            proxies = get_proxy() if self.validator.should_use_proxy(url) else None
            
            # 发送HEAD请求检查更新
            response = requests.head(url, headers=headers, proxies=proxies, 
                                    timeout=15, allow_redirects=True, verify=self.verify_ssl)
            
            # 更新下次检查时间
            site_data['next_check'] = datetime.now().timestamp() + site_data.get('check_interval', self.default_check_interval)
            
            # 处理响应
            if response.status_code == 304:
                self.logger.info(f"[未更新] {site_name} ({url})")
                return False
            
            # 如果服务器返回200，需要进一步验证内容是否变化
            if response.status_code == 200:
                # 保存响应头信息
                if 'Last-Modified' in response.headers:
                    site_data['last_modified'] = response.headers['Last-Modified']
                if 'ETag' in response.headers:
                    site_data['etag'] = response.headers['ETag']
                
                # 获取完整内容并验证哈希
                content_changed = self._verify_content_change(url, site_data)
                
                if content_changed:
                    self.logger.info(f"[内容更新] {site_name} ({url})")
                    self._trigger_crawler(site_name, url)
                    self._update_site_status(site_name)
                    return True
                else:
                    self.logger.info(f"[内容未变] {site_name} ({url})")
                    return False
            
            self.logger.warning(f"[检查异常] {site_name} ({url}) - HTTP状态码: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求异常: {site_name} ({url}) - {str(e)}")
            # 请求失败时使用指数退避策略
            backoff = min(site_data.get('check_interval', self.default_check_interval) * 2, 86400)  # 最长一天
            site_data['next_check'] = datetime.now().timestamp() + backoff
            return False
        except Exception as e:
            self.logger.error(f"检查更新异常: {site_name} ({url}) - {str(e)}")
            return False
    
    def _verify_content_change(self, url, data, session=None):
        """验证内容是否发生变化"""
        try:
            # 准备请求头
            headers = {
                'User-Agent': get_random_ua(),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            # 获取代理(如果启用)
            proxies = get_proxy() if self.validator.should_use_proxy(url) else None
            
            # 获取完整内容
            if session:
                # 使用提供的会话对象
                response = session.get(url, headers=headers, proxies=proxies, timeout=30)
            else:
                # 使用默认请求
                response = requests.get(url, headers=headers, proxies=proxies, 
                                       timeout=30, verify=False)
            
            if response.status_code != 200:
                self.logger.warning(f"获取内容失败: {url} - HTTP状态码: {response.status_code}")
                return False
            
            # 尝试检测编码
            response.encoding = response.apparent_encoding
            content = response.text
            
            # 计算内容哈希
            xpath = data.get('content_xpath', None)  # 可以在配置中指定要监测的内容区域
            new_hash = self.validator.calculate_content_hash(content, xpath)
            
            if not new_hash:
                self.logger.warning(f"计算内容哈希失败: {url}")
                return False
            
            # 比较哈希值
            old_hash = data.get('content_hash')
            if not old_hash:
                # 首次检查，保存哈希值
                data['content_hash'] = new_hash
                return False
            
            # 更新哈希值
            data['content_hash'] = new_hash
            
            # 如果哈希值不同，说明内容已更新
            return old_hash != new_hash
            
        except Exception as e:
            self.logger.error(f"验证内容变化失败: {url} - {str(e)}")
            return False
    
    def _trigger_crawler(self, site_name, url, section_name=None):
        """触发爬虫执行"""
        try:
            # 获取爬虫配置
            if site_name not in self.sites:
                self.logger.warning(f"未找到站点配置: {site_name}")
                return False
            
            site_data = self.sites[site_name]
            
            # 确定爬虫名称
            spider_name = None
            if 'sections' in site_data and section_name:
                # 多栏目格式，查找对应栏目的爬虫
                for section in site_data['sections']:
                    if section.get('name') == section_name:
                        spider_name = section.get('spider', f"{site_name}_spider")
                        break
            else:
                # 单链接格式
                spider_name = site_data.get('spider', f"{site_name}_spider")
            
            if not spider_name:
                self.logger.warning(f"未找到爬虫名称: {site_name} - {section_name}")
                return False
            
            # 使用调度器执行爬虫任务
            self.logger.info(f"触发爬虫: {spider_name} - {url}")
            
            # 异步执行爬虫
            self.scheduler.execute_task(
                self.crawler_engine.start_crawling_with_url,
                spider_name,
                url,
                section_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"触发爬虫失败: {site_name} - {url} - {str(e)}")
            return False
    
    def _update_site_status(self, site_name):
        """更新站点状态到链接库文件"""
        try:
            file_path = self._get_site_file_path(site_name)
            if not file_path:
                self.logger.warning(f"未找到站点链接库文件: {site_name}")
                return False
            
            site_data = self.sites.get(site_name)
            if not site_data:
                return False
            
            # 根据文件类型保存
            if file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 转换时间戳为ISO格式
                    data_to_save = self._prepare_site_data_for_save(site_data)
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            elif file_path.endswith('.csv'):
                # CSV格式保存
                if 'sections' in site_data:
                    sections = site_data['sections']
                    df = pd.DataFrame([{
                        '名称': section.get('name', ''),
                        '链接': section.get('url', ''),
                        '优先级': section.get('priority', 5),
                        '上次爬取时间': datetime.fromtimestamp(section.get('last_crawled', 0)).strftime('%Y-%m-%d %H:%M:%S') if section.get('last_crawled') else None,
                        '爬取频率': self._seconds_to_frequency(section.get('check_interval', self.default_check_interval))
                    } for section in sections])
                    
                    df.to_csv(file_path, index=False, encoding='utf-8')
            
            self.logger.info(f"更新站点状态成功: {site_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新站点状态失败: {site_name} - {str(e)}")
            return False
    
    def _prepare_site_data_for_save(self, site_data):
        """准备站点数据用于保存"""
        # 深拷贝避免修改原始数据
        import copy
        data = copy.deepcopy(site_data)
        
        # 转换时间戳
        if 'next_check' in data:
            del data['next_check']  # 不需要保存下次检查时间
        
        # 处理多栏目格式
        if 'sections' in data:
            for section in data['sections']:
                if 'next_check' in section:
                    del section['next_check']
                if section.get('last_crawled'):
                    section['last_crawled'] = datetime.fromtimestamp(section['last_crawled']).isoformat()
        
        return data
    
    def _seconds_to_frequency(self, seconds):
        """将秒数转换为频率字符串"""
        if seconds <= 3600:
            return 'hourly'
        elif seconds <= 86400:
            return 'daily'
        elif seconds <= 604800:
            return 'weekly'
        else:
            return 'monthly'
    
    def _get_site_file_path(self, site_name):
        """获取站点配置文件路径"""
        # 尝试JSON格式
        json_path = os.path.join(self.link_pool_dir, f"{site_name}.json")
        if os.path.exists(json_path):
            return json_path
            
        # 尝试CSV格式
        csv_path = os.path.join(self.link_pool_dir, f"{site_name}.csv")
        if os.path.exists(csv_path):
            return csv_path
            
        return None
    
    def start(self):
        """启动监测服务"""
        if self.running:
            self.logger.warning("监测服务已在运行中")
            return
            
        self.running = True
        self.logger.info("启动监测服务...")
        
        # 启动调度器
        self.scheduler.set_monitor(self)
        self.scheduler.start()
        
        # 启动文件监听
        self.observer = Observer()
        self.observer.schedule(LinkPoolHandler(self), self.link_pool_dir, recursive=False)
        self.observer.start()
        
        self.logger.info("监测服务已启动")
    
    def stop(self):
        """停止监测服务"""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("停止监测服务...")
        
        # 停止调度器
        if hasattr(self.scheduler, 'stop'):
            self.scheduler.stop()
        
        # 停止文件监听
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
        
        self.logger.info("监测服务已停止")

    def load_all_sites(self):
        """加载所有站点配置"""
        self.logger.info("加载所有站点配置...")
        
        try:
            # 获取链接库目录下的所有文件
            files = os.listdir(self.link_pool_dir)
            
            for file in files:
                # 跳过非数据文件
                if not (file.endswith('.json') or file.endswith('.csv')):
                    continue
                
                # 从文件名提取站点名称
                site_name = os.path.splitext(file)[0]
                
                # 加载站点配置
                self.reload_site(site_name)
            
            self.logger.info(f"成功加载 {len(self.sites)} 个站点配置")
            
        except Exception as e:
            self.logger.error(f"加载站点配置失败: {str(e)}")
    def reload_site(self, site_name):
        """重新加载指定站点配置"""
        try:
            # 尝试加载JSON文件
            file_path = os.path.join(self.link_pool_dir, f"{site_name}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    site_data = json.load(f)
                    
                    # 初始化下次检查时间
                    if 'sections' in site_data:
                        for section in site_data['sections']:
                            if 'next_check' not in section:
                                section['next_check'] = datetime.now().timestamp()
                    elif 'policy_sections' in site_data:
                        # 兼容旧格式
                        for section in site_data['policy_sections']:
                            if 'next_check' not in section:
                                section['next_check'] = datetime.now().timestamp()
                    else:
                        if 'next_check' not in site_data:
                            site_data['next_check'] = datetime.now().timestamp()
                    
                    # 保存站点配置
                    self.sites[site_name] = site_data
                    self.logger.info(f"已加载站点配置: {site_name}")
                    return True
            
            # 尝试加载CSV文件
            file_path = os.path.join(self.link_pool_dir, f"{site_name}.csv")
            if os.path.exists(file_path):
                # 读取CSV文件
                df = pd.read_csv(file_path)
                
                # 输出CSV文件内容，用于调试
                self.logger.info(f"读取到的CSV文件内容: {df.to_dict('records')}")
                
                # 转换为字典格式
                site_data = {
                    'name': site_name,
                    'sections': []
                }
                
                # 处理CSV中的每一行
                for _, row in df.iterrows():
                    # 检查列名并适配
                    if 'section_name' in df.columns:
                        name_col = 'section_name'
                    elif '名称' in df.columns:
                        name_col = '名称'
                    else:
                        name_col = df.columns[0]  # 使用第一列作为名称列
                    
                    if 'url' in df.columns:
                        url_col = 'url'
                    elif '链接' in df.columns:
                        url_col = '链接'
                    else:
                        url_col = df.columns[1]  # 使用第二列作为URL列
                    
                    if 'priority' in df.columns:
                        priority_col = 'priority'
                    elif '优先级' in df.columns:
                        priority_col = '优先级'
                    else:
                        priority_col = None
                    
                    if 'last_crawled' in df.columns:
                        last_crawled_col = 'last_crawled'
                    elif '上次爬取时间' in df.columns:
                        last_crawled_col = '上次爬取时间'
                    else:
                        last_crawled_col = None
                    
                    if 'check_interval' in df.columns:
                        check_interval_col = 'check_interval'
                    elif '爬取频率' in df.columns:
                        check_interval_col = '爬取频率'
                    else:
                        check_interval_col = None
                    
                    # 确保优先级被正确读取
                    priority = 5  # 默认中等优先级
                    if priority_col and priority_col in df.columns:
                        try:
                            priority_value = row[priority_col]
                            if not pd.isna(priority_value):
                                priority = int(float(priority_value))
                                self.logger.info(f"读取到栏目优先级: {site_name} - {row.get(name_col, '')} - 优先级: {priority}")
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"优先级格式错误: {site_name} - {row.get(name_col, '')} - 值: {row[priority_col]} - 错误: {str(e)}")
                    
                    # 处理检查间隔
                    check_interval = self.default_check_interval
                    if check_interval_col and check_interval_col in df.columns:
                        try:
                            interval_value = row[check_interval_col]
                            if not pd.isna(interval_value):
                                if isinstance(interval_value, (int, float)):
                                    check_interval = int(interval_value)
                                elif interval_value.lower() == 'daily':
                                    check_interval = 86400  # 一天的秒数
                                elif interval_value.lower() == 'weekly':
                                    check_interval = 604800  # 一周的秒数
                                elif interval_value.lower() == 'monthly':
                                    check_interval = 2592000  # 30天的秒数
                        except (ValueError, TypeError, AttributeError) as e:
                            self.logger.warning(f"检查间隔格式错误: {site_name} - {row.get(name_col, '')} - 值: {row[check_interval_col]} - 错误: {str(e)}")
                    
                    # 创建栏目配置
                    section = {
                        'name': row.get(name_col, ''),
                        'url': row.get(url_col, ''),
                        'priority': priority,
                        'next_check': datetime.now().timestamp(),
                        'check_interval': check_interval
                    }
                    
                    site_data['sections'].append(section)
                
                # 保存站点配置
                self.sites[site_name] = site_data
                
                # 添加调试日志，输出所有栏目的优先级
                for section in site_data['sections']:
                    self.logger.info(f"已加载栏目配置: {site_name} - {section['name']} - 优先级: {section['priority']}")
                
                self.logger.info(f"已加载站点配置: {site_name}")
                return True
            
            self.logger.warning(f"未找到站点配置文件: {site_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"加载站点配置失败: {site_name} - {str(e)}")
            return False

    def check_high_priority_sites(self):
        """检查高优先级站点更新"""
        self.logger.info("开始检查高优先级站点更新...")
        
        now = datetime.now().timestamp()
        checked_sites = 0
        updated_sites = 0
        
        # 添加调试日志，输出所有站点的优先级
        for site_name, site_data in self.sites.items():
            if 'sections' in site_data:
                for section in site_data['sections']:
                    section_priority = section.get('priority', 5)
                    self.logger.debug(f"站点栏目优先级: {site_name} - {section.get('name', '')} - 优先级: {section_priority}")
        
        for site_name, site_data in self.sites.items():
            # 检查站点优先级
            priority = site_data.get('priority', 5)  # 默认中等优先级
            if priority >= 8:  # 高优先级
                self.logger.info(f"检查高优先级站点: {site_name}")
                checked_sites += 1
                if self.check_site_update(site_name):
                    updated_sites += 1
            
            # 检查是否有到期需要检查的栏目
            if 'sections' in site_data:
                for section in site_data['sections']:
                    if section.get('next_check', 0) <= now:
                        section_priority = section.get('priority', priority)
                        # 添加更详细的日志
                        self.logger.debug(f"检查栏目优先级: {site_name} - {section.get('name', '')} - 优先级: {section_priority}")
                        if section_priority >= 8:
                            section_name = section.get('name', '')
                            self.logger.info(f"检查高优先级栏目: {site_name} - {section_name}")
                            checked_sites += 1
                            if self._check_section_update(site_name, section):
                                updated_sites += 1
                        else:
                            self.logger.debug(f"跳过低优先级栏目: {site_name} - {section.get('name', '')} - 优先级: {section_priority}")
            
            # 检查policy_sections字段（兼容旧格式）
            if 'policy_sections' in site_data:
                for section in site_data['policy_sections']:
                    if section.get('next_check', 0) <= now:
                        section_priority = section.get('priority', priority)
                        if section_priority >= 8:
                            section_name = section.get('name', '')
                            self.logger.info(f"检查高优先级栏目(旧格式): {site_name} - {section_name}")
                            checked_sites += 1
                            if self._check_section_update(site_name, section):
                                updated_sites += 1
        
        self.logger.info(f"完成高优先级站点检查: 共检查 {checked_sites} 个站点/栏目, 发现 {updated_sites} 个更新")
    
    def check_all_sites(self):
        """检查所有站点更新"""
        self.logger.info("开始检查所有站点更新...")
        
        checked_sites = 0
        updated_sites = 0
        
        for site_name, site_data in self.sites.items():
            self.logger.info(f"检查站点: {site_name}")
            checked_sites += 1
            if self.check_site_update(site_name):
                updated_sites += 1
            
        self.logger.info(f"完成所有站点检查: 共检查 {checked_sites} 个站点, 发现 {updated_sites} 个更新")
    
    def check_site_update(self, site_name):
        """检查指定站点更新"""
        if site_name not in self.sites:
            self.logger.warning(f"未找到站点配置: {site_name}")
            return False
            
        site_data = self.sites[site_name]
        self.logger.info(f"检查站点更新: {site_name}")
        
        try:
            # 检查是否为多栏目格式
            if 'sections' in site_data:
                # 多栏目格式
                sections = site_data['sections']
                for section in sections:
                    section_name = section.get('name', '')
                    self.logger.info(f"检查更新: {site_name} - {section_name} ({section.get('url', '')})")
                    self._check_section_update(site_name, section)
            # 检查旧格式的policy_sections
            elif 'policy_sections' in site_data:
                # 旧格式多栏目
                sections = site_data['policy_sections']
                for section in sections:
                    section_name = section.get('name', '')
                    self.logger.info(f"检查更新(旧格式): {site_name} - {section_name} ({section.get('url', '')})")
                    self._check_section_update(site_name, section)
            else:
                # 单链接格式
                self._check_site_update_direct(site_name, site_data)
                
            return True
            
        except Exception as e:
            self.logger.error(f"检查站点更新异常: {site_name} - {str(e)}")
            
            