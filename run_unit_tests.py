import unittest

# Run all the unit tests in the tests directory

loader = unittest.TestLoader()
test_suite = loader.discover('tests')

test_runner = unittest.runner.TextTestRunner()
test_runner.run(test_suite)