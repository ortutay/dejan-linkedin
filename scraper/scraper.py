import arrow
import dropbox
import json
import os
import pprint
import re
import requests
import sys
import time

import config
from bs4 import BeautifulSoup

dbx = dropbox.client.DropboxClient(config.dropbox_token)
pp = pprint.PrettyPrinter(indent=4)

def check_and_email_updates(email, password, urls, visit_urls, driver, config):
    s = Scraper(driver, config)
    s.login(email, password)
    results = s.check(urls)
    updated = results['updated']
    top_likes = results['top_likes']
    top_comments = results['top_comments']
    ss_files = results['ss_files']
    s.visit(visit_urls)
    text = ''
    html = ''
    if len(updated):
        for u in updated:
            name = u[0]
            url = u[1]
            html += '<p>Update for <a href="%s">%s</a></p>\n' % (url, name)
    else:
        html = '<p>No updates for today</p>'

    html += '\n<br/><br/>Top %s likes for last %s days:<br/>%s' % (
        config.like_count_send_top,
        config.like_count_days,
        '\n<br/>'.join([('- %s %s' % (x[0], x[1])) for x in top_likes]))

    html += '\n<br/><br/>Top %s comments for last %s days:<br/>%s' % (
        config.comment_count_send_top,
        config.comment_count_days,
        '\n<br/>'.join([('- %s %s' % (x[0], x[1])) for x in top_comments]))

    print 'sending email', html
    resp = requests.post(
        config.mailgun_api_base_url + '/messages',
        auth=('api', config.mailgun_api_key),
        # files=ss_files[:config.max_screenshots],
        data={
            'from': 'linkedin-updater@' + config.mailgun_domain,
            'to': email,
            'subject': '%s LinkedIn updates for today' % len(updated),
            'html': html,
        })
    print resp

class Scraper:

    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        if not os.path.exists('screens'):
            os.mkdir('screens')

    def login(self, username, password):
        self.driver.get('https://www.linkedin.com/uas/login')
        self.driver.find_element_by_id('session_key-login').send_keys(username)
        self.driver.find_element_by_id('session_password-login').send_keys(password)
        self.driver.find_element_by_css_selector('#login input[type=submit]').click()
        time.sleep(3)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7',
        }
        resp = requests.get('https://www.linkedin.com/uas/login', headers=headers)
        print resp
        cookies = dict(resp.cookies)
        doc = BeautifulSoup(resp.text, 'html.parser')
        source_alias = doc.select('input[name=sourceAlias]')[0]['value']
        login_csrf_param = doc.select('input[name=loginCsrfParam]')[0]['value']
        data = {
            'session_key': username,
            'session_password': password,
            'isJsEnabled': 'false',
            'loginCsrfParam': login_csrf_param,
            'sourceAlias': source_alias,
            'submit': 'Sign in',
        }
        headers = {
            "X-IsAJAXForm": "1",
        }
        resp = requests.post('https://www.linkedin.com/uas/login-submit', data=data, headers=headers, cookies=cookies)
        cookies.update(dict(resp.cookies))
        self.cookies = cookies

    def check(self, urls):
        updated = []
        like_counts = []
        comment_counts = []
        ss_files = []
        for i, url in enumerate(urls):
            print '.', url

            resp = requests.get(url, cookies=self.cookies)
            doc = BeautifulSoup(resp.text.encode('utf-8'), 'html.parser')

            m = re.search(r'activities/(.*?)\+', url)
            ss_name = None
            if m:
                self.driver.get(url)
                ss_name = 'screens/screen-%s-%s.png' % (
                    m.group(1), arrow.utcnow().format('YYYY-MM-DD'))
                self.driver.save_screenshot(ss_name)
            feed = doc.select('#ozfeed-templates/recent-activities-content')
            blob = str(feed[0]) \
                   .replace('<code id="ozfeed-templates/recent-activities-content" style="display: none;"><!--', '') \
                   .replace('--></code>', '')
            data = json.loads(blob)
            blocks = data['feed']['updates']['blocks']
            if self.check_blocks(blocks):
                u = (self.name_from_url(url), url)
                updated.append(u)

                if ss_name:
                    f = open(ss_name, 'rb')
                    if config.save_screenshots_in_dropbox:
                        resp = dbx.put_file(ss_name, f)
                    if config.send_screenshots_in_email:
                        f = ('inline', f)
                        ss_files.append(f)

            likes = self.most_liked_count(blocks)
            like_counts.append((likes, url))

            comments = self.most_commented_count(blocks)
            print 'got comments', comments
            comment_counts.append((comments, url))

        def sort_key(l):
            try:
                return -l[0]
            except:
                return 0
        like_counts.sort(key=sort_key)
        comment_counts.sort(key=sort_key)

        print 'like counts'
        pp.pprint(like_counts)
        print 'comment counts'
        pp.pprint(comment_counts)

        return {
            'updated': updated,
            'top_likes': like_counts[:config.like_count_send_top],
            'top_comments': comment_counts[:config.comment_count_send_top],
            'ss_files': ss_files,
        }

    def most_liked_count(self, blocks):
        likes = 0
        for block in blocks:
            if block.get('template', '') == 'update':
                timestamp = self.get_update_timestamp(block)
                print 'likes', likes
                block_likes = 0
                m = re.match('(\d+)d', timestamp)
                if ((m and int(m.group(1)) < config.like_count_days)
                    or re.match('\d+h', timestamp)):
                    block_likes = self.get_num_likes(block)
                likes = max(likes, block_likes)
        return likes

    def most_commented_count(self, blocks):
        comments = 0
        for block in blocks:
            if block.get('template', '') == 'update':
                timestamp = self.get_update_timestamp(block)
                print 'comments', comments
                block_comments = 0
                m = re.match('(\d+)d', timestamp)
                if ((m and int(m.group(1)) < config.comment_count_days)
                    or re.match('\d+h', timestamp)):
                    block_comments = self.get_num_comments(block)
                comments = max(comments, block_comments)
        return comments

    def check_blocks(self, blocks):
        for block in blocks:
            if block.get('template', '') == 'update':
                timestamp = self.get_update_timestamp(block)
                if re.match('\d+d', timestamp):
                    return True

    def get_update_timestamp(self, block):
        for sub_block in block.get('blocks', []):
            if sub_block.get('template', '') == 'header':
                for header_block in sub_block.get('blocks', []):
                    if header_block.get('template', '') == 'meta':
                        return header_block['timeAgo']
        return ''

    def get_num_likes(self, block):
        for sub_block in block.get('blocks', []):
            if sub_block.get('template', '') == 'social&dsh;summary/likes&dsh;social&dsh;summary':
                return int(sub_block['total'])
        return 0

    def get_num_comments(self, block):
        for sub_block in block.get('blocks', []):
            if sub_block.get('template', '') == 'social&dsh;summary/comments&dsh;social&dsh;summary':
                return int(sub_block['total'])
        return 0

    def name_from_url(self, url):
        m = re.search('activities/(.*?)\+', url)
        if not m:
            return 'Unknown Name',
        return m.group(1).replace('-', ' ').title()

    def visit(self, urls):
        for url in urls:
            self.driver.get(url)
