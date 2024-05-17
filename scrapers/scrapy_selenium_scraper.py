from . scraper import Scraper
import scrapy
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from scrapers.middlewares import DOWNLOADER_MIDDLEWARES
import random

TIMEOUT = random.uniform(4,6)

class ScrapySeleniumScraper(Scraper, scrapy.Spider):
    name = "ScrapySeleniumScraper"

    custom_settings = {
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'LOG_FORMATTER': 'scrapy.logformatter.LogFormatter',
        'DOWNLOADER_MIDDLEWARES': DOWNLOADER_MIDDLEWARES,
    }

    def __init__(self, stop=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop = stop
        self.set_logs("scrapy_selenium_scraper")
    
    def get_webpage(self, html):
        return Selector(text=html)

    def get_elements(self, xpath, obj, _=None):
        return obj.xpath(xpath)

    def parse(self, response):
        obj = self.get_webpage(self.html)
        elements = self.get_elements(self.prefix, obj)

        for elem in elements:
            item = ItemLoader(self.create_class(self.labels)(), elem)
            for label,xpath in zip(self.labels, self.xpath_suffixes):
                item.add_xpath(label, '.'+xpath)
                if item.load_item() and label not in item.load_item():
                    item.add_value(label, "")

            if item.load_item():
                yield item.load_item()
