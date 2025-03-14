# 在文件顶部添加
import urllib3
# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import os
import sys
# 修复路径设置（确保包含项目根目录）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from core.crawler import CrawlerEngine
from utils.link_manager import LinkPoolManager

def main():
    parser = argparse.ArgumentParser(description="政策爬虫控制台")
    parser.add_argument('--spider', help='通过注册名称指定爬虫')
    parser.add_argument('--url', help='直接指定目标URL')
    parser.add_argument('--site', help='指定要爬取的网站(使用链接库)')
    args = parser.parse_args()

    engine = CrawlerEngine()
    
    if args.spider:
        # 使用注册的爬虫
        spider_class, config_path = engine.load_spider(args.spider)
        engine.start_crawling(spider_class, config_path)
    elif args.url:
        # 实现URL自动识别逻辑
        pass
    elif args.site:
        # 使用链接库爬取指定网站
        link_manager = LinkPoolManager()
        links = link_manager.get_site_links(args.site)
        
        if not links:
            print(f"错误: 未找到网站 '{args.site}' 的链接库或链接库为空")
            return
        
        # 根据网站名称确定使用哪个爬虫
        if "ndrc" in args.site.lower() or "发改委" in args.site:
            spider_name = "ndrc_gov_spider"
        # 删除深圳政府网站的判断
        # elif "sz" in args.site.lower() or "深圳" in args.site:
        #     spider_name = "sz_gov_spider"
        elif "wanxin" in args.site.lower() or "万信" in args.site:
            spider_name = "wanxin_info_spider"
        elif "gov" in args.site.lower() or "政府" in args.site:
            spider_name = "gov_cn_spider"
        else:
            print(f"错误: 无法确定网站 '{args.site}' 使用的爬虫")
            return
        
        # 加载并启动爬虫
        spider_class, config_path = engine.load_spider(spider_name)
        
        # 对于每个链接启动爬虫
        for link in links:
            engine.start_crawling_with_url(
                spider_class, 
                config_path, 
                link.get('url', ''), 
                link.get('name', '')
            )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()