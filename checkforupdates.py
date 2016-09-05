import sys
import config
from scraper.scraper import Scraper, check_and_email_updates

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


if __name__ == '__main__':
    import scraper
    email = sys.argv[1]
    password = sys.argv[2]
    urls = open(sys.argv[3]).read().strip().split('\n')

    user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.57 " +
            "Safari/537.36")
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = user_agent

    driver = webdriver.PhantomJS(
        executable_path=config.phantomjs_bin,
        desired_capabilities=dcap)

    # driver = webdriver.Chrome()

    try:
        check_and_email_updates(email, password, urls, driver)
    finally:
        driver.quit()
