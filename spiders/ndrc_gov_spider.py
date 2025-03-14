import os
import sys
# 添加项目根目录到Python路径（需要覆盖三级目录）
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import scrapy
from spiders.base_spider import BaseSpider

class NdrcGovSpider(BaseSpider):
    name = "ndrc_gov_spider"
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 1
    }

    def parse_list(self, response):
        links = response.xpath(self.config['list_rules']['policy_links']).extract()
        next_page = response.xpath(self.config['list_rules']['next_page']).extract_first()
        
        for link in links:
            yield scrapy.Request(
                url=self._absolute_url(response.url, link),
                callback=self.parse_detail
            )
        
        if next_page:
            yield scrapy.Request(
                url=self._absolute_url(response.url, next_page),
                callback=self.parse_list
            )

    def parse_detail(self, response):
        # 获取栏目名称 - 从request.meta获取
        section_name = None
        if response.request and hasattr(response.request, 'meta'):
            section_name = response.request.meta.get('section_name')
        
        # 如果无法从request.meta获取，则使用spider的current_section
        if not section_name and hasattr(self, 'current_section'):
            section_name = self.current_section
        
        item = {
            'title': response.xpath('normalize-space(//meta[@name="ArticleTitle"]/@content)').get() or response.xpath('normalize-space(//h1)').get(),
            'content': '\n'.join([p.strip() for p in response.xpath('//div[@class="TRS_Editor"]//text()').getall() if p.strip()]),
            'source_url': response.url,
            'publish_date': response.xpath('//meta[@name="PubDate"]/@content').get() or response.xpath('//div[contains(text(), "发布日期")]/following-sibling::div/text()').re_first(r'\d{4}-\d{2}-\d{2}'),
            'section_name': section_name  # 添加栏目信息
        }
        
        if item['title'] and item['content']:
            self.db.save_policy(item)
        else:
            self.logger.warning(f"无效内容页面: {response.url}")