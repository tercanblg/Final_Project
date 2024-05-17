import unittest
from scrapy.http import Request
from scrapers.middlewares import NoInternetMiddleware

class TestNoInternetMiddleware(unittest.TestCase):
    def setUp(self):
        self.middleware = NoInternetMiddleware()
        self.mock_request = Request(url='http://test.com')

    def test_process_request(self):
        expected_response = '<html><body><h1>Sample response</h1></body></html>'
        result = self.middleware.process_request(self.mock_request, spider=None)
        self.assertEqual(result.body.decode('utf-8'), expected_response)

if __name__ == "__main__":
    unittest.main()
