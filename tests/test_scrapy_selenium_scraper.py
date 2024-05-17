import unittest
from unittest.mock import MagicMock
from scrapy.http import HtmlResponse
from scrapy.item import Item, Field
from scrapers.scrapy_selenium_scraper import ScrapySeleniumScraper

SAMPLE_BODY = '<html><body><h1>Hello, world!</h1></body></html>'

class TestItem(Item):
    heading = Field()

class TestScrapySeleniumScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = ScrapySeleniumScraper()
        self.mock_response = HtmlResponse(url='http://test.com', body=SAMPLE_BODY, encoding='utf-8')

    def test_get_webpage(self):
        result = self.scraper.get_webpage(SAMPLE_BODY)
        self.assertTrue('<h1>Hello, world!</h1>' in str(result))

    def test_get_elements(self):
        result = self.scraper.get_webpage(SAMPLE_BODY)
        elements = self.scraper.get_elements('//h1//text()', result)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].get(), 'Hello, world!')

    def test_parse(self):
        self.scraper.html = SAMPLE_BODY
        self.scraper.prefix = '//h1'
        self.scraper.labels = ['heading']
        self.scraper.xpath_suffixes = ['']
        self.scraper.create_class = MagicMock(return_value=TestItem)
        items = list(self.scraper.parse(self.mock_response))
        self.assertEqual(len(items), 1)
        self.assertIn('heading', items[0])

if __name__ == "__main__":
    unittest.main()
