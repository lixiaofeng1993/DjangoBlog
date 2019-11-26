from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required  # 验证用户是否登录的装饰器
from django.db.models import Q  # 与或非 查询
from common.public import paginator  # 分页封装，每页显示10条
from base.models import Event, Guest
from common.execute import get_user
import logging

log = logging.getLogger('log')  # 初始化log


def index(request):
    return render(request, 'sign/login.html')


# 发布会管理
@login_required
def event_manage(request):
    # username = request.COOKIES.get('user', '')  # 读取cookie
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        HttpResponseRedirect('/login/')
    else:
        username = request.session.get('user', '')  # 读取session
        event_list = Event.objects.all()
        page = request.GET.get('page')
        contacts = paginator(event_list, page)
        return render(request, 'sign/event_manage.html', {'user': username, 'events': contacts})


# 发布会搜索
@login_required
def search_name(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return render(request, 'user/login_action.html')
    else:
        username = request.session.get('user', '')
        search_name = request.GET.get('name', '')
        event_list = Event.objects.filter(name__contains=search_name)  # 包含
        page = request.GET.get('page')
        contacts = paginator(event_list, page)
        return render(request, 'sign/event_manage.html',
                      {'user': username, 'events': contacts, 'search_name': search_name})


# 嘉宾管理
@login_required
def guest_manage(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return render(request, 'user/login_action.html')
    else:
        username = request.session.get('user', '')
        guest_list = Guest.objects.all()
        page = request.GET.get('page')
        contacts = paginator(guest_list, page)
        return render(request, 'sign/guest_manage.html', {'user': username, 'guests': contacts})


# 嘉宾搜索
@login_required
def search_guest(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return render(request, 'user/login_action.html')
    else:
        username = request.session.get('user', '')
        search_guest = request.GET.get('name', '')
        guest_list = Guest.objects.filter(Q(phone__contains=search_guest) | Q(realname__contains=search_guest))  # Q 与或非
        if not guest_list:  # 增加 发布会名称 查询 联表查询
            guest_list = []
            event_list = Event.objects.filter(name__contains=search_guest)
            for event_id in event_list:
                guest = Guest.objects.filter(event_id=event_id)
                guest_list.extend(guest)  # extend() 只能接收 list，且把这个 list 中的每个元素添加到原 list 中
        page = request.GET.get('page')
        contacts = paginator(guest_list, page)
        return render(request, 'sign/guest_manage.html',
                      {'user': username, 'guests': contacts, 'search_guest': search_guest})


# 签到
@login_required
def sign_index(request, eid):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return render(request, 'user/login_action.html')
    else:
        event = get_object_or_404(Event, id=eid)  # 如果查询不存在，返回404异常
        return render(request, 'sign/sign_index.html', {'event': event})


# 处理签到操作
@login_required
def sign_index_action(request, eid):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return render(request, 'user/login_action.html')
    else:
        event = get_object_or_404(Event, id=eid)
        phone = request.POST.get('phone', '')
        result = Guest.objects.filter(phone=phone)
        if not result:
            return render(request, 'sign/sign_index.html', {'event': event, 'hint': 'phone error.'})
        result = Guest.objects.filter(phone=phone, event_id=eid)
        if not result:
            return render(request, 'sign/sign_index.html', {'event': event, 'hint': 'event id or phone error.'})
        result = Guest.objects.get(phone=phone, event_id=eid)
        if result.sign:
            return render(request, 'sign/sign_index.html', {'event': event, 'hint': 'user has sign in.'})
        else:
            Guest.objects.filter(phone=phone, event_id=eid).update(sign='1')
            return render(request, 'sign/sign_index.html',
                          {'event': event, 'hint': 'sign in success!', 'guest': result})


def delete_all(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return render(request, 'user/login_action.html')
    else:
        Event.objects.all().delete()
        Guest.objects.all().delete()
        log.info('默认服务==>  用户 {} ，清空测试数据完成！'.format(user_id))
    return HttpResponseRedirect('/api/event_manage/')
