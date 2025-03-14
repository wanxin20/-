# 爬虫注册中心 - 统一使用SPIDERS字典
SPIDERS = {
    "ndrc_gov_spider": (
        "spiders.ndrc_gov_spider.NdrcGovSpider", 
        "config/spiders/ndrc_gov.yaml"
    ),
    # 添加万信人员信息爬虫
    "wanxin_info_spider": (
        "spiders.wanxin_info_spider.WanxinInfoSpider",
        "config/spiders/wanxin_info.yaml"
    )
    # 其他爬虫保持相同格式
}

