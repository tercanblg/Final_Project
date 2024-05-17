import unittest
from scrapers.scraper import Scraper

class MockedScraper(Scraper):
    def get_webpage(self, url):
        pass

    def get_elements(self, xpath, obj, text=None):
        pass


class TestScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = MockedScraper()

    def test_create_class(self):
        fields = ['field1', 'field2', 'field3']
        new_class = self.scraper.create_class(fields)
        instance = new_class()
        self.assertTrue('field1' in instance.fields)
        self.assertTrue('field2' in instance.fields)
        self.assertTrue('field3' in instance.fields)

    def test_save_file(self):
        import os
        import pandas as pd
        dataframe = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        filename = 'test_file.csv'
        self.scraper.save_file(dataframe, filename, False)
        self.assertTrue(os.path.exists(filename))
        os.remove(filename)  # cleanup after the test

    def test_merge_dicts(self):
        dicts = [{'key1': ['value1'], 'key2': ['value2']}, {'key1': ['value3'], 'key2': ['value4']}, {'key1': ['value5'], 'key2': ['value6']}]
        merged = self.scraper.merge_dicts(dicts)
        expected = {'key1': ['value1', 'value3', 'value5'], 'key2': ['value2', 'value4', 'value6']}
        self.assertDictEqual(merged, expected)

    def test_clean_text(self):
        original_text = "\r\n This is \t a test \n text.  "
        expected_text = "This is a test text."
        self.assertEqual(self.scraper.clean_text(original_text), expected_text)


if __name__ == "__main__":
    unittest.main()
