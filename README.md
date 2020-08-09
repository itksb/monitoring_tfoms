## Description

Script for monitoring changes in the content of links of a given page of the tfoms site.
When launched, the script loads all links on the specified page of the site. For each link, the script requests the http content headers for those links. A digital signature is created based on the http headers. After that, the script checks for the existence of its database file. If not, then the script simply writes the resulting database to a file. The next time you run the script, digital signatures of links will be generated again. The script will compare the old and new digital signatures. If there is a difference, then the content of the links has changed, the script sends a notification via the Telegram bot.

## Run example

Run script without params to see help:
```
./cron.py
```

With params:
```
/usr/bin/python3 /home/user/site_tfoms_monitoring/cron.py -u https://SITE_DOMAIN/page/resheniya_komissii -s class=\"page\" -e class=\"footer__metrika\" -v 3 -d "SITE_DOMAIN" -t TELEGRAM_BOT_TOKEN -i TELEGRAM_BOT_CHAT_ID  -logfile /home/user/site_tfoms_monitoring/cron.log -dbfile /home/site/site_tfoms_monitoring/cron.db  
```
