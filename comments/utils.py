#!/usr/bin/env python
# encoding: utf-8


"""
@version: ??
@author: liangliangyy
@license: MIT Licence 
@contact: liangliangyy@gmail.com
@site: https://www.lylinux.net/
@software: PyCharm
@file: utils.py
@time: 2018/10/8 10:24 PM
"""

from DjangoBlog.utils import send_email
from DjangoBlog.utils import get_current_site
from django.conf import settings
import logging

logger = logging.getLogger("log")


def send_comment_email(comment):
    site = get_current_site().domain

    if settings.DEBUG:
        site = '127.0.0.1:8000'
    subject = '感谢您发表的评论'
    article_url = "http://{site}{path}".format(site=site, path=comment.article.get_absolute_url())
    html_content = """
                   <p>非常感谢您在本站发表评论</p>
                   您可以访问
                   <a href="%s" rel="bookmark">%s</a>
                   来查看您的评论，
                   再次感谢您！
                   <br />
                   如果上面链接无法打开，请将此链接复制至浏览器。
                   %s
                   """ % (article_url, comment.article.title, article_url)
    tomail = comment.author.email
    send_email([tomail], subject, html_content)
    try:
        if comment.parent_comment:
            html_content = """
                    您在 <a href="%s" rel="bookmark">%s</a> 的评论 <br/> %s <br/> 收到回复啦.快去看看吧
                    <br/>
                    如果上面链接无法打开，请将此链接复制至浏览器。
                    %s
                    """ % (article_url, comment.article.title, comment.parent_comment.body, article_url)
            tomail = comment.parent_comment.author.email
            send_email([tomail], subject, html_content)
    except Exception as e:
        logger.error(e)
