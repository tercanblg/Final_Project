from . scraper import Scraper
from selenium.common.exceptions import TimeoutException, WebDriverException
from latest_user_agents import get_random_user_agent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import scrapy
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor
from multiprocessing import Process, Queue
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from utils.manager.password_manager import get_login_info
from . scrapy_selenium_scraper import ScrapySeleniumScraper
from exceptions.scraper_exceptions import ScraperStoppedException
import time
from utils.manager.process_manager import ProcessStatus
import logging
import os
import html
import random

TIMEOUT = random.uniform(4,6)
XPATH_USERNAME = '//input[@type="text"]|//input[@type="email"]'
XPATH_PASSWORD = '//input[@type="password"]'
logger = logging.getLogger(__name__)

class SeleniumScraper(Scraper):

    def get_driver(self, headless=True):
        options = Options()

        # Avoid sending information to the server to indicate the use of an automated browser.

        # Adding argument to disable the AutomationControlled flag 
        options.add_argument("--disable-blink-features=AutomationControlled")
        # Exclude the collection of enable-automation switches 
        options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
        # Turn-off userAutomationExtension 
        options.add_experimental_option("useAutomationExtension", False) 

        if headless:
            options.add_argument("--headless")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Changing the property of the navigator value for webdriver to undefined 
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        logger.info("Driver created")

        return driver
    
    def get_webpage(self, url, headless=True):
        driver = self.get_driver(headless)
        user_agent = get_random_user_agent()
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})
        driver.get(url)
        logger.info(f"Webpage {url} opened")
        return driver

    def get_elements(self, xpath, obj, text=None):
        xpath = self.remove_text_from_xpath(xpath)
        try:
            WebDriverWait(obj, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, xpath)))
            elements = obj.find_elements(By.XPATH, xpath)
            if text:
                WebDriverWait(obj, TIMEOUT).until(lambda driver: any(text in html.unescape(element.text) for element in elements))
                elements = [html.unescape(element.text) for element in elements]
            return elements
        except TimeoutException:
            logger.warning(f"Elements not found for xpath: {xpath}")
            return None
    
    def close_webpage(self, obj):
        obj.quit()

    def before_scrape(self, url, labels, selected_text, xpaths, pagination_xpath, file_name, signal_manager, row, html, stop, interaction, max_pages=1, append=False):
        self.update_progress("1%", stop, signal_manager, row)
        if pagination_xpath:
            obj = self.get_webpage(url)
            self.update_progress("2%", stop, signal_manager, row)
            obj = self.check_elements(stop, signal_manager, row, xpaths, selected_text, url, obj, interaction)
            if obj is None:
                return
        
        self.update_progress("10%", stop, signal_manager, row)

        full_xpaths = {}
        for xpath in xpaths:
            if ' | ' in xpath:
                full_xpaths[xpath] = xpath.split(' | ')
            else:
                full_xpaths[xpath] = [xpath]

        full_xpaths_list = [xpath for xpath_list in full_xpaths.values() for xpath in xpath_list]

        general_xpaths = [self.generalise_xpath(xpath) for xpath in full_xpaths_list]
        prefix = self.get_common_xpath(general_xpaths)
        # Generate the suffixes
        suffixes = self.get_suffixes(prefix, general_xpaths)
        
        # Associate original XPath with suffixes
        original_xpath_to_suffixes = {}
        for original, split_xpaths in full_xpaths.items():
            original_xpath_to_suffixes[original] = [suffixes[full_xpaths_list.index(split_xpath)] for split_xpath in split_xpaths]
        
        # Reconstruct the xpaths with suffixes
        xpath_suffixes = [" | .".join(suffixes) for suffixes in original_xpath_to_suffixes.values()]

        pages = 0
        next_page = True
        results = []
        actual_percentage = 10
        increment = 10/max_pages if max_pages and max_pages != float('inf') else 0.5

        # Clean the pagination xpath in case it has blank lines
        pagination_xpaths = []
        is_list = False
        if pagination_xpath and "\n" in pagination_xpath:
            pagination_xpaths = pagination_xpath.split("\n")
            pagination_xpaths = [xpath for xpath in pagination_xpaths if xpath.strip()]
            if len(pagination_xpaths) == 1:            
                pagination_xpath = pagination_xpaths[0]
                pagination_xpaths = []
            else:
                is_list = True

        scrape = True
        while next_page and pages < max_pages:
            actual_html = ""
            if not pagination_xpath:
                actual_html = html
            else:
                actual_percentage += increment
                self.update_progress(f"{int(actual_percentage)}%", stop, signal_manager, row)
                self.infinite_scroll(obj)
                actual_percentage += increment * 2
                self.update_progress(f"{int(actual_percentage)}%", stop, signal_manager, row)
                actual_html = obj.page_source
            
            # Scrape the page
            if scrape:
                dictionary = self.scrape(actual_html, prefix, labels, xpath_suffixes)
            scrape = True

            actual_percentage += increment * 2
            self.update_progress(f"{int(actual_percentage)}%", stop, signal_manager, row)
            results.append(dictionary)

            if pagination_xpath and pagination_xpath != "fake" and pages + 1 < max_pages:
                pagination_xpaths = []
                if "\n" in pagination_xpath:
                    pagination_xpaths = pagination_xpath.split("\n")
                    pagination_xpaths = [xpath for xpath in pagination_xpaths if xpath.strip()]
                    pagination_xpath = pagination_xpaths[0]

                try:
                    WebDriverWait(obj, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, pagination_xpath)))
                    next_element = obj.find_element(By.XPATH, pagination_xpath)
                    if next_element.tag_name == "a":
                        obj.execute_script("arguments[0].click();", next_element)
                    else:
                        next_element.click()
                    actual_percentage += increment * 2
                    self.update_progress(f"{int(actual_percentage)}%", stop, signal_manager, row)
                    if pagination_xpaths:
                        pagination_xpath = "\n".join(pagination_xpaths[1:])
                    elif is_list:
                        next_page = False
                except Exception:
                    logger.error("Error: Pagination button not found")
                    if pagination_xpaths:
                        pagination_xpath = "\n".join(pagination_xpaths[1:])
                        # don't scrape again the same page
                        scrape = False
                    else:
                        next_page = False
            else:
                next_page = False
            pages+=1
            actual_percentage += increment
            self.update_progress(f"{int(actual_percentage)}%", stop, signal_manager, row)

        if pagination_xpath:
            self.close_webpage(obj)

        self.after_scrape(results, labels, selected_text, file_name, row, signal_manager, stop, append)

    def after_scrape(self, results, labels, selected_text, file_name, row, signal_manager, stop, append):
        self.update_progress("91%", stop, signal_manager, row)
        dict_results = self.merge_list_dicts(results)
        self.update_progress("92%", stop, signal_manager, row)
        if len(dict_results) > 0:
            try:
                for label,text in zip(labels, selected_text):
                    elements = dict_results[label]
                    elements = self.clean_list(elements)
                    text = self.clean_text(text)
                    dict_results[label] = elements
                
                self.update_progress("95%", stop, signal_manager, row)
                df = self.dict_to_df(dict_results)
                self.update_progress("96%", stop, signal_manager, row)

                if df is not None and file_name is not None:
                    self.save_file(df, file_name, append)
                    signal_manager.process_signal.emit(row, str(ProcessStatus.FINISHED.value), file_name)
            except Exception as e:
                logger.error(f"Error: No elements found. {e}")
                signal_manager.process_signal.emit(row, str(ProcessStatus.ERROR.value), "")
        else:
            logger.error("Error: No elements found")
            signal_manager.process_signal.emit(row, str(ProcessStatus.ERROR.value), "")



    def run_scraper(self, q, html, prefix, labels, xpath_suffixes):
        try:
            runner = CrawlerRunner()
            deferred = runner.crawl(ScrapySeleniumScraper, start_urls=["http://localhost:8000"], html=html, prefix=prefix, labels=labels, xpath_suffixes=xpath_suffixes)
            deferred.addBoth(lambda _: reactor.stop())

            spider = next(iter(runner.crawlers)).spider

            def collect_items(item):
                dictionary = dict(item)
                q.put(dictionary)

            spider.crawler.signals.connect(collect_items, signal=scrapy.signals.item_scraped)

            reactor.run()

            q.put(None)

        except Exception as e:
            logger.error(f"Error: {e}")
            q.put(None)
    
    def scrape(self, html, prefix, labels, xpath_suffixes):
        q = Queue()
        p = Process(target=self.run_scraper, args=(q,html,prefix,labels,xpath_suffixes))

        results = []
        p.start()
        data = q.get()
        if data:
            data = dict(data)
        while data:
            results.append(data)
            data = q.get()
            if data:
                data = dict(data)
        p.join()

        return results
        

    def remove_text_from_xpath(self, xpath):
        if xpath.endswith("//text()"):
            xpath = xpath[:-8]
        return xpath
    
    def find_login_input(self, obj, xpath):
        try:
            login_input = WebDriverWait(obj, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return login_input != None
        except Exception:
            logger.error("Error: Couldn't find the email or username input.")

    def fill_input(self, obj, xpath, text):
        try:
            login_input = WebDriverWait(obj, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            if login_input:
                login_input.send_keys(text)
                logger.info("Login input filled")
                return True
            else:
                logger.warning("Error: Login input not found")
                return False
        except Exception:
            logger.error("Error: Login input not filled")
            return False
    
    def login_using_stored_credentials(self, driver, url, stop, signal_manager, row, interaction, login_info=None):
        try:
            login_url = url
            if login_info:
                login_url = login_info["url"]
            driver.get(login_url)

            # Find and fill in the email or username input
            
            driver = self.require_user_interaction(driver, login_url, stop, signal_manager, row, interaction)

            if self.find_login_input(driver, XPATH_USERNAME) and login_info:
                    self.fill_input(driver, XPATH_USERNAME, login_info["username"])
                    self.fill_input(driver, XPATH_PASSWORD, login_info["password"])

            if interaction:
                # Wait for the user to login
                interaction.wait()
                interaction.clear()
                self.check_selenium_driver(driver, signal_manager, row)

                cookies = driver.get_cookies()

            else:
                while True:
                    try:
                        cookies = driver.get_cookies()
                        time.sleep(0.1)
                    except WebDriverException:
                        # The driver is no longer active
                        break

            driver.quit()            
            driver = self.get_webpage(url)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Warning: Error adding cookie: {e}")
            driver.get(url)
            return driver

        except Exception:
            logger.error("Error: Couldn't find the email or username input or the password input.")
            return None

    def check_for_captcha(self, obj):
        # Look for CAPTCHA in iframes
        iframes = self.get_elements("//iframe[@title='reCAPTCHA']", obj)
        if iframes is not None and len(iframes) > 0:
            return True
        return False
    
    def _check_elements(self, xpaths, selected_text, obj):
        for xpath, text in zip(xpaths, selected_text):
            text = self.clean_text(text)
            elements = self.get_elements(self.generalise_xpath(xpath), obj, text)
            if elements is None or len(elements) == 0:
                return False
        return True
    
    def require_user_interaction(self, obj, url, stop, signal_manager, row, interaction, captcha=False):
        # Save cookies
        cookies = obj.get_cookies()

        # Quit the headless driver
        obj.quit()

        self.update_progress(str(ProcessStatus.REQUIRES_INTERACTION.value), stop, signal_manager, row)
        # Wait for the user to open the Selenium window
        if interaction:
            interaction.wait()
            interaction.clear()

        # Start a new driver without headless mode
        obj = self.get_webpage(url, headless=False)

        if captcha:
            # Add the cookies to the new driver
            for cookie in cookies:
                try:
                    obj.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Warning: Error adding cookie: {e}")

        # Refresh to apply the cookies
        obj.refresh()

        return obj
    
    def check_selenium_driver(self, obj, signal_manager, row):
        try:
            obj.title
        except WebDriverException:
            signal_manager.process_signal.emit(row, str(ProcessStatus.ERROR.value), "")
            logger.error("Scraper closed accidentally by the user")
            raise ScraperStoppedException("Scraper closed accidentally by the user")
    
    def check_elements(self, stop, signal_manager, row, xpaths, selected_text, url, obj, interaction):
        found = False
        if self._check_elements(xpaths, selected_text, obj):
            found = True
            logger.info(f"Elements found with the selected text: {selected_text}")
        else:
            if self.check_for_captcha(obj):
                self.update_progress("3%", stop, signal_manager, row)
                logger.info("CAPTCHA found")
                
                obj = self.require_user_interaction(obj, url, stop, signal_manager, row, interaction, True)

                if self.check_for_captcha(obj):
                    logger.info("Waiting for the user to solve the CAPTCHA")
                    if interaction:
                        interaction.wait()
                        interaction.clear()
                        self.check_selenium_driver(obj, signal_manager, row)
                    else:
                        while True:
                            try:
                                html = obj.page_source
                                time.sleep(0.1)
                            except WebDriverException:
                                # The driver is no longer active
                                # Write the page source to a file
                                try:
                                    with open("temp.html", "w", encoding='utf-8') as f:
                                        f.write(html)
                                    obj.quit()

                                    # Start a new driver without headless mode
                                    obj = self.get_driver()
                                    obj.get(f"file:///{os.getcwd()}/temp.html")
                                    os.remove("temp.html")
                                except Exception as e:
                                    logger.warning(f"Warning: Error opening the temporary file with the page source: {e}")
                                    obj = None
                                found = True # It's not possible to continue interacting with the driver in this case
                                break

        
        self.update_progress("5%", stop, signal_manager, row)

        # Check if login is required
        if not found and not self._check_elements(xpaths, selected_text, obj):
            self.update_progress("6%", stop, signal_manager, row)
            obj = self.login_using_stored_credentials(obj, url, stop, signal_manager, row, interaction, get_login_info(url))
            if obj:
                self.update_progress("7%", stop, signal_manager, row)
                for xpath, text in zip(xpaths, selected_text):
                    text = self.clean_text(text)
                    elements = self.get_elements(self.generalise_xpath(xpath), obj, text)
                    if elements is not None and len(elements) > 0:
                        elements = self.clean_list(elements)
                        elements = self.find_text_in_data(elements, text)
                        if elements is None:
                            logger.error("Error: Text selected by the user not found in elements")
                            return None
        return obj
    
    def update_progress(self, progress, stop, signal_manager, row):
        if stop and stop.value:
            signal_manager.process_signal.emit(row, str(ProcessStatus.STOPPED.value), "")
            logger.info("Scraper stopped by the user")
            raise ScraperStoppedException("Scraper stopped by the user")
        signal_manager.process_signal.emit(row, progress, "")

    def infinite_scroll(self, obj):
        get_height_js = 'return document.body.scrollHeight'

        # get initial page height
        last_height = obj.execute_script(get_height_js)

        # scroll down to the bottom of the page
        obj.execute_script('window.scrollTo(0, document.body.scrollHeight);')

        # wait for the page to load new content
        time.sleep(2)

        new_height = obj.execute_script(get_height_js)

        # compare with the old page height
        while new_height != last_height: # # if heights are different it means more content was loaded
            
            last_height = new_height
            obj.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(2)
            new_height = obj.execute_script(get_height_js)
