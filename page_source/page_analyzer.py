import requests
from lxml import html, etree
import argparse
import sys
import os
from urllib.parse import urlparse
import urllib3
import ssl
import re
import time  # 添加time模块导入，用于Selenium方法

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建自定义SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 定义保存源码的目录
SOURCE_DIR = r"D:\86135\Desktop\poli\3\page_source"

def get_url_filename(url):
    """将URL转换为合法的文件名"""
    # 移除协议部分
    url = re.sub(r'^https?://', '', url)
    # 替换非法字符
    url = re.sub(r'[\\/*?:"<>|]', '_', url)
    # 替换其他可能导致问题的字符
    url = re.sub(r'[&=+,;]', '_', url)
    # 限制长度
    if len(url) > 100:
        url = url[:100]
    return f"{url}.html"

def get_page_structure(url, depth=2, max_children=5):
    """获取网页结构并以树形方式展示"""
    try:
        # 添加请求头模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        
        # 使用session来应用自定义SSL上下文
        session = requests.Session()
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
        
        # 发送请求获取页面内容，禁用SSL验证
        response = session.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        
        # 自动检测编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        # 保存HTML源码到文件
        filename = get_url_filename(url)
        # 确保目录存在
        os.makedirs(SOURCE_DIR, exist_ok=True)
        filepath = os.path.join(SOURCE_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"成功保存网页源码到: {os.path.abspath(filepath)}")
        
        return True
    
    except Exception as e:
        print(f"错误: {str(e)}")
        # 尝试使用备用方法1
        try:
            print("尝试使用备用方法1...")
            import urllib.request
            
            # 创建自定义的opener
            context = ssl._create_unverified_context()
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
            urllib.request.install_opener(opener)
            
            # 添加请求头
            req = urllib.request.Request(url, headers=headers)
            
            # 发送请求
            with urllib.request.urlopen(req, timeout=15) as response:
                html_content = response.read().decode(response.info().get_param('charset') or 'utf-8')
            
            # 保存HTML源码到文件
            filename = get_url_filename(url)
            # 确保目录存在
            os.makedirs(SOURCE_DIR, exist_ok=True)
            filepath = os.path.join(SOURCE_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"成功保存网页源码到: {os.path.abspath(filepath)}")
            
            return True
        except Exception as e2:
            print(f"备用方法1也失败: {str(e2)}")
            
            # 尝试使用备用方法2 (Selenium)
            try:
                print("尝试使用备用方法2 (Selenium)...")
                
                # 检查是否已安装selenium
                try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    from selenium.webdriver.chrome.service import Service
                    from webdriver_manager.chrome import ChromeDriverManager
                except ImportError:
                    print("请先安装selenium和webdriver_manager: pip install selenium webdriver-manager")
                    return False
                
                # 配置Chrome选项
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # 无头模式
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--ignore-certificate-errors")  # 忽略证书错误
                chrome_options.add_argument("--ignore-ssl-errors")  # 忽略SSL错误
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                # 初始化WebDriver
                print("正在初始化WebDriver...")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                
                try:
                    # 访问URL
                    print(f"正在访问 {url}...")
                    driver.get(url)
                    
                    # 等待页面加载
                    time.sleep(5)
                    
                    # 获取页面内容
                    html_content = driver.page_source
                    
                    # 保存HTML源码到文件
                    filename = get_url_filename(url)
                    # 确保目录存在
                    os.makedirs(SOURCE_DIR, exist_ok=True)
                    filepath = os.path.join(SOURCE_DIR, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"成功保存网页源码到: {os.path.abspath(filepath)}")
                    
                    return True
                finally:
                    # 关闭浏览器
                    driver.quit()
                    
            except Exception as e3:
                print(f"备用方法2也失败: {str(e3)}")
                
                # 尝试使用备用方法3 (curl命令行)
                try:
                    print("尝试使用备用方法3 (curl命令行)...")
                    import subprocess
                    
                    # 使用curl命令获取页面内容
                    filename = get_url_filename(url)
                    # 确保目录存在
                    os.makedirs(SOURCE_DIR, exist_ok=True)
                    filepath = os.path.join(SOURCE_DIR, filename)
                    
                    # 构建curl命令
                    curl_cmd = [
                        "curl",
                        "-k",  # 忽略SSL证书验证
                        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                        "-o", filepath,
                        url
                    ]
                    
                    # 执行curl命令
                    print(f"执行命令: {' '.join(curl_cmd)}")
                    result = subprocess.run(curl_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"成功保存网页源码到: {os.path.abspath(filepath)}")
                        return True
                    else:
                        print(f"curl命令执行失败: {result.stderr}")
                        return False
                        
                except Exception as e4:
                    print(f"备用方法3也失败: {str(e4)}")
                    print("\n所有方法均失败，无法获取页面内容。")
                    print("建议手动访问该网站，保存页面源码后进行分析。")
                    return False

def main():
    parser = argparse.ArgumentParser(description="网页源码保存工具")
    parser.add_argument('url', help='要保存源码的网页URL')
    
    if len(sys.argv) == 1:
        # 如果没有参数，进入交互模式
        url = input("请输入要保存源码的网页URL: ")
        get_page_structure(url)
    else:
        args = parser.parse_args()
        get_page_structure(args.url)

if __name__ == "__main__":
    main()