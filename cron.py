#!/usr/bin/env python3

# ttfoms site page monitoring script
# Sergey Kochetkov <ksb@itksb.com>
#  Usage example:
#  /usr/bin/python3 cron.py \
# -u https://ttfoms.em70.ru/page/resheniya_komissii_po_razrabotke_territorialnoy_programmy_oms_v_tomskoy_oblasti \
# -s class=\"page\" -e class=\"footer__metrika\" \
# -v 3 -d "ttfoms.em70.ru" -t telegram-bot-token -i -bot-chat-id \
# -logfile `pwd`/cron.log \
# -dbfile `pwd`/cron.db
# crontab example:
# 0 * * * *    /usr/bin/python3 /home/ksb/WebProjects/site_tfoms_monitoring/cron.py -u https://ttfoms.em70.ru/page/resheniya_komissii_po_razrabotke_territorialnoy_programmy_oms_v_tomskoy_oblasti -s class=\"page\" -e class=\"footer__metrika\" -v 3 -d "ttfoms.em70.ru" -t TELEGRAM_BOT_TOKEN -i TELEGRAM_CHAT_ID  -logfile /home/ksb/WebProjects/site_tfoms_monitoring/cron.log -dbfile /home/ksb/WebProjects/site_tfoms_monitoring/cron.db  

import sys
import logging
from logging import critical, error, info, warning, debug
import argparse

import requests
import re
import json
import os.path

class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values

    Author: https://stackoverflow.com/users/10293/hughdbrown
    
    Sample output:
    >>> a = {'a': 1, 'b': 1, 'c': 0}
    >>> b = {'a': 1, 'b': 2, 'd': 0}
    >>> d = DictDiffer(b, a)
    >>> print "Added:", d.added()
    Added: set(['d'])
    >>> print "Removed:", d.removed()
    Removed: set(['c'])
    >>> print "Changed:", d.changed()
    Changed: set(['b'])
    >>> print "Unchanged:", d.unchanged()
    Unchanged: set(['a'])
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)
    def added(self):
        return self.set_current - self.intersect 
    def removed(self):
        return self.set_past - self.intersect 
    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])



def retreive_html_page(url, fromHtmlStr, toHtmlStr):
    r"""Scraps url link addresses from the 
    specified url
    :param url: URL.
    :param fromHtmlStr: start search from
    :param toHtmlStr: end search 
    :return: list
    """
    debug('url=%s, fromHtmlStr=%s, toHtmlStr=%s' % (url, fromHtmlStr, toHtmlStr))

    result = ""

    if not url.strip():
        error("url param should not be empty")
    req = requests.get(url)
    html = req.text
    if not html:
        info("Retreived html page is empty")
        return result

    firstOccurancePos = html.index(fromHtmlStr)
    if firstOccurancePos < 0 :
        info("%s was not found in the site page html" % (fromHtmlStr))
        return result
    html = html[firstOccurancePos:]
    endOccurancePos = html.index(toHtmlStr)
    if endOccurancePos < 0 :
        info("%s was not found in the site page html" % (endOccurancePos))
        return result
    html = html[:endOccurancePos]    
    result = html
    return result

def extract_links_from_html(html):
    links = []
    regex = r"(?:href=\")([^\s:]+)\""
    matches = re.finditer(regex, html, re.IGNORECASE)

    for matchNum, match in enumerate(matches, start=1):
        debug ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))

        for groupNum in range(0, len(match.groups())):
            groupNum = groupNum + 1        
            debug ("Group {groupNum} found at {start}-{end}: {group}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))
            links.append(match.group(groupNum))

    return tuple(links)


def retreive_resources_digest_dict_by_links(links):
    
    res_dict = {}
    for link in links:
        req = requests.head(link)
        if 'content-length' in req.headers:
            content_length = req.headers['content-length'] 
        else:
            content_length = ''
        if 'last-modified' in req.headers:
            last_modified = req.headers['last-modified']
        else: 
            last_modified = ''
        digest = "{content_length}{last_modified}".format(content_length=content_length, last_modified=last_modified ) 
        if digest:
            res_dict[link] = hash(digest)
        
    return res_dict


def normalize_link_urls(links_tuple, site_domain, http_schema = "https"):
    result = []
    for link in links_tuple:
        if link:
            if ((link.find(site_domain) == -1 ) and ( link.find(http_schema) == -1) ) :
                link = link.strip("/")
                link = "{http_schema}://{site_domain}/{link}".format(http_schema=http_schema, site_domain=site_domain, link=link)
                result.append(link)
        else:
            error("link %s is empty"%(link))
    return result

def retreive_prev_digests_if_exists(filepath="cron.db"):
    result_dict = {}
    if os.path.isfile(filepath):
        with open('cron.db', 'r') as file:
            result_dict = json.load(file)
    return result_dict

def is_diff_calculation_needed (filepath="cron.db"):
    return os.path.isfile(filepath)

def create_notification_msg (diffObject):
    result = ''
    if len(diffObject.added()) > 0:
        result = "Добавлены: %s . " % (", ".join( diffObject.added()))
    if len(diffObject.changed()) > 0:
        result += "Изменены: %s ." % (", ".join( diffObject.changed()))
    if len(diffObject.removed()) > 0:
        result += "Удалены: %s ." % (", ".join( diffObject.removed()))    
    
    return result


def telegram_bot_sendtext(bot_token, bot_chatID, bot_message):
    url = "https://api.telegram.org/bot{bot_token}/sendMessage".format(bot_token=bot_token)
    data = {'chat_id': bot_chatID, 'text': bot_message}
    response = requests.post(url, data)
    return response.json()


def parse_arguments():
    """Read arguments from a command line."""
    parser = argparse.ArgumentParser(description='Arguments get parsed via --commands')
    parser.add_argument('-v', metavar='verbosity', type=int, default=2,
        help='Verbosity of logging: 0 -critical, 1- error, 2 -warning, 3 -info, 4 -debug')
    parser.add_argument('-u', metavar='url', type=str, required=True, help='Url of the site page for monitoring changes')    
    parser.add_argument('-s', metavar='startFromHtml', type=str, required=True, help='Start from html part')    
    parser.add_argument('-e', metavar='endHtml', type=str, required=True, help='End html part')
    parser.add_argument('-d', metavar='domain', type=str, required=True, help="Site domain")    
    parser.add_argument('-t', metavar='bot_token', type=str, required=True, help="Telegram bot token")    
    parser.add_argument('-i', metavar='bot_chatID', type=str, required=True, help="Telegram bot chat ID")  
    parser.add_argument(
        '-logfile', metavar='logfilepath', type=str, default='', 
        required=False, help="Path to file where write the log."
    )   
    parser.add_argument(
        '-dbfile', metavar='dbfilepath', type=str, 
        required=True, help="Path to the db file."
    )   
    
    args = parser.parse_args()
    return args


def main():
    verbose = {0: logging.CRITICAL, 1: logging.ERROR, 2: logging.WARNING, 3: logging.INFO, 4: logging.DEBUG}
    if args.logfile:
        logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=verbose[args.v], filename=args.logfile)
    else:
        logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=verbose[args.v], stream=sys.stdout)
    
    
    warning("Старт мониторинга изменений страницы сайта Фонда")

    html_page = retreive_html_page(args.u, args.s, args.e)
    links_tuple = extract_links_from_html(html_page)
    links_normalized = normalize_link_urls(links_tuple, args.d)
    
    resources_link_digests = retreive_resources_digest_dict_by_links(links_normalized)
    # with open('cron2.db', 'r') as file:
    #     resources_link_digests = json.loads(file.read())
    

    message = ""
    if is_diff_calculation_needed(args.dbfile):
        prev_link_digests = retreive_prev_digests_if_exists(args.dbfile)
        diffObject = DictDiffer( resources_link_digests, prev_link_digests)
        message = create_notification_msg(diffObject)
        debug("Сообщение: %s" % message)
    else:
        warning("База мониторинга пустая. Это первый запуск?")
        telegram_bot_sendtext(args.t, args.i, "База мониторинга пустая. Возможно первый запуск?") 

    if (message):
        warning("Сообщение: " + message) 
        telegram_bot_sendtext(args.t, args.i, message) 
    else:
        warning("Изменений нет")  

    try:
        with open(args.dbfile, 'w') as file:
            file.write(json.dumps(resources_link_digests, sort_keys=True, indent=4))                 
    except:
        error("Ошибка записи в файл")
        info(telegram_bot_sendtext(args.t, args.i, "Мониторинг страницы \"Решения комиссии...\" Ошибка при сохранении базы") )
    

    warning("Конец программы")
    return 0
    

if __name__ == "__main__":
    args = parse_arguments()
    main()