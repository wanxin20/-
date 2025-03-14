# readme.md 目录
- [1] Policy Spider 项目结构
- [2] 核心逻辑流程 → line58
- [3] 开发问题记录 → line99



## **Policy Spider 项目结构说明**

### 目录结构概览

#### 配置中心 (config/)
- `__init__.py`
- `settings.py` - 全局配置（请求头、路径等）
- **spiders/** - 爬虫规则配置文件（YAML/JSON）
  - `ndrc_gov.yaml` - 示例：发改委规则
  - `gov_cn.yaml` - 示例：中国政府网规则

#### 核心逻辑 (core/)
- `__init__.py`
- `monitor.py` - 监测服务主入口
- `crawler.py` - 爬虫调度引擎
- `db_client.py` - 数据库/文件存储接口（统一抽象层）
- `scheduler.py` - 任务调度器（定时/触发）

#### 爬虫实现 (spiders/)
- `__init__.py` - 爬虫注册入口
- `base_spider.py` - 爬虫基类（抽象接口）
- `ndrc_gov_spider.py` - 发改委爬虫（继承基类）
- `gov_cn_spider.py` - 中国政府网爬虫

#### 数据存储 (data/)
- **link_pool/** - 链接库（按网站分类）
  - `ndrc_gov.json` - 示例：发改委链接库
  - `gov_cn.csv` - 其他格式兼容
- **policy_data/** - 爬取内容库
  - `ndrc_gov/`
    - `2023-10-05/` - 按日期归档
  - `gov_cn/`

#### 工具包 (utils/)
- `logger.py` - 日志模块
- `validator.py` - 网页结构验证器
- `anti_spider.py` - 反爬策略（代理/User-Agent池）

#### 测试模块 (tests/)
- `test_spiders.py` - 爬虫单元测试
- `test_monitor.py` - 监测逻辑测试

#### 文档 (docs/)
- `spider_rules.md` - 爬虫规则编写规范

#### 根目录文件
- `requirements.txt` - 依赖库列表
- `run_monitor.py` - 监测服务启动入口
- `lci.py` - 脚本启动入口

## **核心逻辑流程**

### 1. 脚本服务信息与启动
 1. 爬虫实现文件
- 新建爬虫文件 ：在 spiders/ 目录下创建新的爬虫类文件，如 new_site_spider.py
- 需要继承 base_spider.py 中的 BaseSpider 类
- 参考现有的 sz_gov_spider.py 或 wanxin_info_spider.py 实现
 2. 爬虫配置文件
- 在 config/spiders/ 目录下创建对应的 YAML 配置文件，如 new_site.yaml
- 配置起始 URL、爬取规则、解析规则等
 3. 爬虫注册
- 修改 spiders/__init__.py ，在 SPIDERS 字典中注册新爬虫
- 格式为： 'new_site': ('spiders.new_site_spider.NewSiteSpider', 'config/spiders/new_site.yaml')
### 2. 监测服务启动：
 1. 链接库文件
- 在 data/link_pool/ 目录下创建新网站的链接库文件
- 可以是 JSON 格式（如 new_site.json ）或 CSV 格式（如 new_site.csv ）
- 包含网站各栏目的 URL、名称、优先级等信息
 2. 命令行工具
- 修改 cli.py 文件中的网站识别逻辑
- 在 main() 函数中的条件判断部分添加新网站的判断条件
- 例如： elif "new_site" in args.site.lower() or "新网站" in args.site:
 3. 可能需要的特殊处理
- 如果新网站有特殊的反爬机制，可能需要修改 utils/anti_spider.py
- 如果需要特殊的页面验证，可能需要修改 utils/validator.py

### 3.无需修改的核心文件
 1. 核心引擎文件
- core/crawler.py - 爬虫调度引擎
- core/monitor.py - 监测服务主入口
- core/scheduler.py - 任务调度器
- core/db_client.py - 数据存储接口
 2. 基础工具文件
- utils/logger.py - 日志模块
- utils/downloader.py - 页面下载器
- utils/link_manager.py - 链接管理器（已支持多种格式）
 3. 启动和配置文件
- run_monitor.py - 监测服务启动入口
- requirements.txt - 依赖库列表
- config/settings.py - 全局配置

## **开发过程要注意的问题**

1. 注意项目的可拓展性，便于运维，同时保证无需修改的核心文件每次修改时的适用性（可拓展）
2. 项目的版本如何保存，假如新版本不适用，退回到旧版本
3. 