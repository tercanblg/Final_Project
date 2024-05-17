from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.loader import ItemLoader
from .scraper import Scraper
from scrapy.crawler import CrawlerRunner
import scrapy
from twisted.internet import reactor
from multiprocessing import Process, Queue
import logging
from scrapers.middlewares import DOWNLOADER_MIDDLEWARES

logger = logging.getLogger(__name__)

class ScrapyScraper(Scraper, Spider):
    name = "ScrapyScraper"

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36',
        'CONCURRENT_REQUESTS': 32,
        'DOWNLOAD_DELAY': 0.5,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.5,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 16,
        'AUTOTHROTTLE_MAX_DELAY': 5.0,
        'AUTOTHROTTLE_DEBUG': True,
        'CLOSESPIDER_ITEMCOUNT': 5,
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'LOG_FORMATTER': 'scrapy.logformatter.LogFormatter',
        'DOWNLOADER_MIDDLEWARES': DOWNLOADER_MIDDLEWARES,
    }

    def get_webpage(self, response):
        return Selector(response)

    def get_elements(self, xpath, obj, _=None):
        return obj.xpath(xpath)

    def parse(self, response):
        obj = Selector(text=self.html)

        full_xpaths = {}
        for xpath in self.xpaths:
            if ' | ' in xpath:
                full_xpaths[xpath] = xpath.split(' | ')
            else:
                full_xpaths[xpath] = [xpath]

        full_xpaths_list = [xpath for xpath_list in full_xpaths.values() for xpath in xpath_list]
        
        general_xpaths = [self.generalise_xpath(xpath) for xpath in full_xpaths_list]
        prefix = self.get_common_xpath(general_xpaths)
        elements = self.get_elements(prefix, obj)
        
        # Generate the suffixes
        suffixes = self.get_suffixes(prefix, general_xpaths)
        
        # Associate original XPath with suffixes
        original_xpath_to_suffixes = {}
        for original, split_xpaths in full_xpaths.items():
            original_xpath_to_suffixes[original] = [suffixes[full_xpaths_list.index(split_xpath)] for split_xpath in split_xpaths]
        
        # Reconstruct the xpaths with suffixes
        xpath_suffixes = [" | .".join(suffixes) for suffixes in original_xpath_to_suffixes.values()]

        if elements is None or len(elements) == 0:
            logger.error("Error: No elements found")

        count = 0
        node = {label: "" for label in self.labels}
        for elem in elements:
            item = ItemLoader(self.create_class(self.labels)(), elem)
            for label,xpath in zip(self.labels, xpath_suffixes):

                item.add_xpath(label, '.'+xpath)
                if item.load_item() and label not in item.load_item():
                    item.add_value(label, "")

                if count == 0 and item.load_item():
                    if xpath.endswith('//text()'):
                        new_xpath = xpath[:-8]

                    parent_html = elem.xpath('.' + new_xpath).get()
                    target_html = elem.xpath('.' + new_xpath + '/node()').get()
                    if parent_html and target_html:
                        outer_html = parent_html.replace(target_html, "")
                        node[label] = outer_html

                if count > 0 and not item.load_item():
                    if xpath.endswith('//text()'):
                        new_xpath = xpath[:-8]

                    parent_html = elem.xpath('.' + new_xpath).get()
                    target_html = elem.xpath('.' + new_xpath + '/node()').get()
                    if not target_html:
                        target_html = ""
                    if parent_html:
                        outer_html = parent_html.replace(target_html, "")
                        if outer_html == node[label]:
                            item.add_value(label, "")

            if item.load_item():
                count+=1
                yield item.load_item()
            
            if self.max_items and count == self.max_items:
                break
    
    def run_scraper(self, q, url, labels, xpaths, html, max_items):
        self.set_logs("scrapy_scraper")

        try:
            runner = CrawlerRunner()

            deferred = runner.crawl(ScrapyScraper, start_urls=['http://localhost:8000'], url=url, labels=labels, xpaths=xpaths, html=html, max_items=max_items)
            deferred.addBoth(lambda _: reactor.stop())

            spider = next(iter(runner.crawlers)).spider
            results = []

            def collect_items(item):
                results.append(item)

            spider.crawler.signals.connect(collect_items, signal=scrapy.signals.item_scraped)

            reactor.run()
            dict_results = self.merge_dicts(results)

            if len(dict_results) > 0:
                for label in labels:
                    elements = dict_results[label]
                    elements = self.clean_list(elements)
                    dict_results[label] = elements
            
            q.put(dict_results)
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
            q.put(e)

    def scrape(self, url, labels, xpaths, html, max_items=None):
        q = Queue()
        p = Process(target=self.run_scraper, args=(q,url,labels,xpaths,html,max_items,))

        p.start()
        result = q.get()
        p.join()

        return(result)
