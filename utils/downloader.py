import requests
from utils.logger import setup_logger
import urllib3
import ssl

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PageDownloader:
    def __init__(self):
        self.logger = setup_logger('PageDownloader')
        
        # 创建自定义SSL上下文
        self.session = requests.Session()
        # 为会话全局禁用SSL验证
        self.session.verify = False
        
        # 创建更宽松的SSL适配器
        try:
            # 创建自定义SSL上下文
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            # 设置更宽松的密码套件
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
            
            # 创建适配器并挂载到会话
            adapter = requests.adapters.HTTPAdapter()
            self.session.mount('https://', adapter)
        except Exception as e:
            self.logger.warning(f"配置SSL适配器失败: {str(e)}")
    
    def fetch(self, url, headers=None, timeout=30):
        """下载页面内容"""
        try:
            # 使用session进行请求，而不是直接使用requests.get
            response = self.session.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response.content
            else:
                self.logger.error(f"下载失败 {url} - 状态码: {response.status_code}")
        except Exception as e:
            self.logger.error(f"下载失败 {url} - {str(e)}")
        return None