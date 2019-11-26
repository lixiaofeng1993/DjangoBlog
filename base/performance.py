#!/user/bin/env python
# coding=utf-8
'''
# 创 建 人: 李先生
# 文 件 名: performance.py
# 说   明: 
# 创建时间: 2019/5/14 22:08
'''
import sys

sys.path.insert(0, r'/var/common/jenkins/workspace/DjangoBlog')
sys.path.insert(0, r'D:\DjangoBlog')

from locust import HttpLocust, TaskSet, task, Locust, events
from locust.clients import HttpSession
import queue, json, subprocess, os
from common.sql_parameter import get_parameters
from common.public import get_extract
from common.random_params import random_params
import logging

log = logging.getLogger('log')


class UserBehavior(TaskSet):  # 定义用户行为


    def on_start(self):
        try:
            self.if_dict_list, self.url = get_parameters()
            self.extract_dict = ''
            for if_dict in self.if_dict_list:
                if isinstance(if_dict, dict):
                    if 'error' in if_dict.keys():
                        exit()
                elif isinstance(if_dict, list):
                    for _if_dict in if_dict:
                        if 'error' in _if_dict.keys():
                            exit()
        except TypeError:
            exit()

    def teardown(self):
        log.info('结束！')

    @task(1)
    def test_request(self):
        session = HttpSession(self.url)
        for interface_ in self.if_dict_list:
            if isinstance(interface_['step_list'], list):
                for interface in interface_['step_list']:
                    if interface['method'] in ["post", "put"]:
                        if interface['data_type'] == 'json':
                            res = session.request(method=interface['method'], url=interface['url'],
                                                  json=interface['body'], headers=interface['header'])
                        elif interface['data_type'] == 'data':
                            res = session.request(method=interface['method'], url=interface['url'],
                                                  data=interface['body'], headers=interface['header'])
                    elif interface['method'] in ["get", "delete"]:
                        if interface['is_sign']:
                            if interface['sign_type'] == 4:
                                res = session.request(method=interface['method'], url=interface['url'],
                                                      params={'data': interface['body']},
                                                      headers=interface['header'])
                        else:
                            res = session.request(method=interface['method'], url=interface['url'],
                                                  params=interface['body'],
                                                  headers=interface['header'])
                    log.info(res.text)


class WebsiteUser(Locust):  # 设置性能测试;
    task_set = UserBehavior  # 指向一个定义了的用户行为类;

    min_wait = 3000  # 用户执行任务之间等待时间的下界，单位：毫秒;
    max_wait = 6000  # 用户执行任务之间等待时间的上界，单位：毫秒;


def run():
    subprocess.check_call(
        'locust -f D:\DjangoBlog\\base\performance.py --master')


if __name__ == '__main__':
    run()
