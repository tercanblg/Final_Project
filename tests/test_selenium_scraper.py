import unittest
from unittest.mock import patch, MagicMock
from selenium.webdriver.remote.webelement import WebElement
from scrapers.selenium_scraper import SeleniumScraper

class TestSeleniumScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = SeleniumScraper()
        patcher = patch('selenium.webdriver.Chrome')
        self.addCleanup(patcher.stop)
        self.mock_driver = patcher.start()

    def test_get_driver(self):
        self.scraper.get_driver(headless=True)

        # Verify that the Chrome driver was called
        self.mock_driver.assert_called_once()

    def test_get_webpage(self):
        self.scraper.get_webpage('http://test.com')

        # Verify that get() was called with the url
        self.mock_driver.return_value.get.assert_called_once_with('http://test.com')

    @patch('selenium.webdriver.support.wait.WebDriverWait')
    def test_get_elements(self, mock_wait):
        # Mock returned elements
        mock_element = MagicMock(spec=WebElement)
        self.mock_driver.find_elements.return_value = [mock_element]

        # Mock WebDriverWait
        mock_wait.return_value.until.return_value = mock_element

        self.scraper.get_elements('//input', self.mock_driver)

        # Verify that the method correctly called the webdriver
        self.mock_driver.find_elements.assert_called_once()

    def test_close_webpage(self):
        self.scraper.close_webpage(self.mock_driver)
        self.mock_driver.quit.assert_called_once()

    def test_remove_text_from_xpath(self):
        xpath = '//div[@class="test"]//text()'
        result = self.scraper.remove_text_from_xpath(xpath)
        self.assertEqual(result, '//div[@class="test"]')

    def test_check_for_captcha(self):
        # Case 1: CAPTCHA present
        captcha_element = WebElement(self.mock_driver, "test_id")
        self.mock_driver.find_elements.return_value = [captcha_element]
        self.assertTrue(self.scraper.check_for_captcha(self.mock_driver))

        # Case 2: CAPTCHA not present
        self.mock_driver.find_elements.return_value = []
        self.assertFalse(self.scraper.check_for_captcha(self.mock_driver))

if __name__ == '__main__':
    unittest.main()
