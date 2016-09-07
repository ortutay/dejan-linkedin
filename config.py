import os

key = "g7JX0zelzNbkO1xyuBui2lxiZbiDmntc"
redis_url = os.environ.get('REDIS_URL') or 'localhost'

mailgun_api_key = 'key-2db4800076d7e1b935235be20c7cc7fe'
mailgun_api_base_url = 'https://api.mailgun.net/v3/sandboxf1fb529c436147c69553809529747ca0.mailgun.org'
mailgun_domain = 'sandboxf1fb529c436147c69553809529747ca0.mailgun.org'

# phantomjs_bin = 'bin/phantomjs/phantomjs-2.1.1-windows/bin/phantomjs.exe'
phantomjs_bin = 'bin/phantomjs/phantomjs-2.1.1-macosx/bin/phantomjs'

dropbox_token = 'dyyVaY6ILToAAAAAAAAoYOjpDpx4nSeEPvuRHcGRbkG-2gMeeQEX8Cjg4RYqSqPp'

like_count_days = 3
like_count_send_top = 3
max_screenshots = 10

save_screenshots_in_dropbox = False
send_screenshots_in_email = False
