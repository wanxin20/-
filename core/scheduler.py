import time
import logging
import threading
import schedule
from datetime import datetime, timedelta

class TaskScheduler:
    """任务调度器：管理监测任务的执行频率和优先级"""
    
    def __init__(self, monitor=None):
        self.logger = logging.getLogger('TaskScheduler')
        self.monitor = monitor
        self.running = False
        self.scheduler_thread = None
        self.max_concurrent_tasks = 3  # 最大并发任务数
        self.active_tasks = 0  # 当前活动任务数
        self.task_lock = threading.Lock()  # 用于同步任务计数
    
    def set_monitor(self, monitor):
        """设置监测器实例"""
        self.monitor = monitor
    
    def start(self):
        """启动调度器"""
        if self.running:
            self.logger.warning("调度器已在运行中")
            return
        
        if not self.monitor:
            self.logger.error("未设置监测器实例，无法启动调度器")
            return
        
        self.running = True
        self.logger.info("启动任务调度器...")
        
        # 启动调度线程
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        self.logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
            
        self.running = False
        
        # 等待调度线程结束
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度循环，定期检查所有站点更新"""
        self.logger.info("启动调度循环...")
        
        # 每小时执行一次全量检查
        schedule.every().hour.do(self._check_all_sites)
        
        # 每分钟检查一次高优先级站点
        schedule.every().minute.do(self._check_high_priority_sites)
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"调度循环异常: {str(e)}")
                time.sleep(30)  # 出错后等待较长时间
    
    def _check_all_sites(self):
        """检查所有站点"""
        self.logger.info("执行全量站点检查...")
        if self.monitor:
            self.monitor.check_all_sites()
    
    def _check_high_priority_sites(self):
        """检查高优先级站点"""
        self.logger.info("执行高优先级站点检查...")
        if self.monitor:
            self.monitor.check_high_priority_sites()
    
    def execute_task(self, task_func, *args, **kwargs):
        """执行任务，控制并发数"""
        # 如果当前活动任务数已达到最大值，则等待
        while self.active_tasks >= self.max_concurrent_tasks:
            time.sleep(0.5)
        
        # 增加活动任务计数
        with self.task_lock:
            self.active_tasks += 1
        
        # 创建线程执行任务
        def task_wrapper():
            try:
                task_func(*args, **kwargs)
            finally:
                # 减少活动任务计数
                with self.task_lock:
                    self.active_tasks -= 1
        
        thread = threading.Thread(target=task_wrapper)
        thread.daemon = True
        thread.start()
        
        return thread