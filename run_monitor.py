import os
import sys
import time
import argparse
import logging
import urllib3
from utils.logger import setup_logger
from core.monitor import PolicyMonitor
from utils.anti_spider import proxy_manager

def main():
    """监测服务主入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="政策监测服务")
    parser.add_argument('--link-pool', default='data/link_pool', help='链接库目录路径')
    parser.add_argument('--interval', type=int, default=300, help='默认检查间隔(秒)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                        help='日志级别')
    # 添加代理和SSL验证相关参数
    parser.add_argument('--disable-proxy', action='store_true', help='禁用代理服务器')
    parser.add_argument('--disable-ssl-verify', action='store_true', help='禁用SSL证书验证')
    parser.add_argument('--disable-ssl-warnings', action='store_true', help='禁用SSL警告信息')
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger('MonitorService')
    
    # 根据命令行参数设置日志级别
    log_level = getattr(logging, args.log_level)
    logger.setLevel(log_level)
    
    # 设置代理状态
    proxy_manager.set_enabled(not args.disable_proxy)
    
    # 禁用SSL警告
    if args.disable_ssl_warnings:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    logger.info("启动政策监测服务...")
    
    try:
        # 创建并启动监测器
        monitor = PolicyMonitor(
            link_pool_dir=args.link_pool,
            check_interval=args.interval,
            verify_ssl=not args.disable_ssl_verify
        )
        
        # 添加以下代码，强制重新加载sz_gov配置
        logger.info("强制重新加载sz_gov站点配置...")
        monitor.reload_site('sz_gov')
        
        # 输出加载后的优先级信息
        if 'sz_gov' in monitor.sites:
            site_data = monitor.sites['sz_gov']
            if 'sections' in site_data:
                for section in site_data['sections']:
                    logger.info(f"sz_gov站点优先级信息: {section.get('name', '')} - 优先级: {section.get('priority', '未设置')}")
        
        monitor.start()
        
        # 保持主线程运行
        logger.info("监测服务已启动，按Ctrl+C停止...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭服务...")
        if 'monitor' in locals():
            monitor.stop()
        logger.info("服务已停止")
    except Exception as e:
        logger.error(f"服务运行异常: {str(e)}")
        if 'monitor' in locals():
            monitor.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()