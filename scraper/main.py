import requests
import sys
import re

from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

urls = [
    'https://www.linkedin.com/pulse/activities/pedro-guillen+0_2E0C4BV52ZKrg1nxciJbNy?trk=prof-0-sb-rcnt-act-link',
    'https://www.linkedin.com/pulse/activities/alexander-tsyplikhin+0_3AW1foubal_idUUnLhA-AS?trk=prof-0-sb-rcnt-act-link',
]

user_agent = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) " +
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36"
)
dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = user_agent

def check_and_email_updates(email, password, urls):
    print 'hello'
    s = Scraper()
    s.login(email, password)
    updated = s.check(urls)
    text = ''
    html = ''
    if len(updated):
        for u in updated:
            name = u[0]
            url = u[1]
            text += 'Update for %s, URL: %s\n' % (name, url)
            html += '<p>Update for <a href="%s">%s</a></p>' % (url, name)
    else:
        text = 'No updates for today'
        html = 'No updates for today'
    print 'sending email', text
    resp = requests.post(
        config.mailgun_api_base_url + '/messages',
        auth=('api', config.mailgun_api_key),
        data={
            'from': 'linkedin-updater@' + config.mailgun_domain,
            'to': email,
            'subject': '%s LinkedIn updates for today' % len(updated),
            'text': text,
            'html': html,
        })
    print resp

class PhantomScraper:

    def __init__(self):
        self.driver = webdriver.PhantomJS('bin/phantomjs-2.1.1-macosx/bin/phantomjs', desired_capabilities=dcap)
        # self.driver = webself.driver.PhantomJS('bin/phantomjs-2.1.1-linux-x86_64/bin/phantomjs')

    def login(self, email, password):
        self.driver.set_window_size(1120, 550)
        self.driver.get('https://www.linkedin.com/')
        self.driver.find_element_by_id('login-email').send_keys(email)
        self.driver.find_element_by_id('login-password').send_keys(password)
        self.driver.find_element_by_css_selector('input[name=submit]').submit()

    def check(self, urls):
        updated = []
        for url in urls:
            # print url
            self.driver.get(url)
            doc = BeautifulSoup(self.driver.page_source.encode('utf-8'), 'html.parser')
            for el in self.driver.find_elements_by_css_selector('.timestamp'):
                ts = el
                is_comment = False
                while True:
                    try:
                        el = el.find_element_by_xpath('..')
                    except selenium.common.exceptions.InvalidSelectorException:
                        break
                    if 'comment' in el.get_attribute('class').encode('utf-8'):
                        is_comment = True
                        break
                if is_comment:
                    continue
                ts_str = ts.get_attribute('innerHTML')
                print ts_str
                if re.search('\d+h', ts_str):
                    updated.append(url)
                    break
        return updated


if __name__ == '__main__':
    s = PhantomScraper()
    s.login(sys.argv[1], sys.argv[2])
    print s.check(urls)
