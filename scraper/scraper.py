import arrow
import dropbox
import json
import pprint
import re
import requests
import sys
import time

import config
from bs4 import BeautifulSoup

dbx = dropbox.client.DropboxClient(config.dropbox_token)
pp = pprint.PrettyPrinter(indent=4)

def check_and_email_updates(email, password, urls, driver):
    s = Scraper(driver)
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

class Scraper:

    def __init__(self, driver):
        self.driver = driver

    def login(self, username, password):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7',
        }

        # resp = requests.get('https://www.linkedin.com/uas/login', headers=headers)
        self.driver.get('https://www.linkedin.com/uas/login')
        # cookies = dict(resp.cookies)
        # print cookies

        # doc = BeautifulSoup(self.driver.page_source(), 'html.parser')
        # source_alias = doc.select('input[name=sourceAlias]')[0]['value']
        # login_csrf_param = doc.select('input[name=loginCsrfParam]')[0]['value']

        self.driver.find_element_by_id('session_key-login').send_keys(username)
        self.driver.find_element_by_id('session_password-login').send_keys(password)
        self.driver.find_element_by_css_selector('#login input[type=submit]').click()
        print 'xxx'
        time.sleep(10)

        # data = {
        #     'session_key': username,
        #     'session_password': password,
        #     'isJsEnabled': 'false',
        #     'loginCsrfParam': login_csrf_param,
        #     'sourceAlias': source_alias,
        #     'submit': 'Sign in',
        # }
        # headers = {
        #     "X-IsAJAXForm": "1",
        # }
        # resp = requests.post('https://www.linkedin.com/uas/login-submit', data=data, headers=headers, cookies=cookies)
        # cookies.update(dict(resp.cookies))
        # self.cookies = cookies

    def check(self, urls):
        updated = []
        for i, url in enumerate(urls):
            print '.',
            # resp = requests.get(url, cookies=self.cookies)
            self.driver.get(url)
            print url
            m = re.search(r'activities/(.*?)\+', url)
            if m:
                ss_name = 'screens/screen-%s-%s.png' % (
                    m.group(1), arrow.utcnow().format('YYYY-MM-DD'))
                self.driver.save_screenshot(ss_name)
                f = open(ss_name, 'rb')
                resp = dbx.put_file(ss_name, f)
                print 'uploaded', resp
            # doc = BeautifulSoup(resp.text.encode('utf-8'), 'html.parser')
            # print self.driver.page_source
            doc = BeautifulSoup(self.driver.page_source, 'html.parser')
            feed = doc.select('#ozfeed-templates/recent-activities-content')
            if len(feed) == 0:
                continue

            blob = str(feed[0]) \
                   .replace('<code id="ozfeed-templates/recent-activities-content" style="display: none;"><!--', '') \
                   .replace('--></code>', '')
            data = json.loads(blob)
            if self.check_blocks(data['feed']['updates']['blocks']):
                # self.screenshot(url)
                self.driver.save_screenshot('screen-%s.png' % url)
                u = (self.name_from_url(url), url)
                updated.append(u)
        return updated

    def screenshot(self, url):
        pp.pprint(self.cookies)
        self.driver.delete_all_cookies()
        self.driver.get('https://www.linkedin.com')
        for k, v in self.cookies.iteritems():
            m = re.match(r'"(.*)"', v)
            if m:
                v = m.group(1)
            c = {'name': k, 'value': v, 'domain': 'www.linkedin.com'}
            print c
            self.driver.add_cookie(c)
        self.driver.get(url)
        self.driver.save_screenshot('text.png')
        print 'ss', url, self.cookies

    def check_blocks(self, blocks):
        for block in blocks:
            if block.get('template', '') == 'update':
                timestamp = self.get_update_timestamp(block)
                if re.match('\d+h', timestamp):
                    return True

    def get_update_timestamp(self, block):
        for sub_block in block.get('blocks', []):
            if sub_block.get('template', '') == 'header':
                for header_block in sub_block.get('blocks', []):
                    if header_block.get('template', '') == 'meta':
                        return header_block['timeAgo']
        return ''

    def name_from_url(self, url):
        m = re.search('activities/(.*?)\+', url)
        if not m:
            return 'Unknown Name',
        return m.group(1).replace('-', ' ').title()
