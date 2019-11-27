from django.db.models import Count
from django.conf import settings
from common.public import gr_code, getACodeImage
from common.execute import get_total_values
from common.except_check import change_info_logic
from django.core.cache import cache

from django.utils import timezone
import os, time, json, logging, threading
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .tasks import delete_logs, run_plan, stop_locust
from django.http import StreamingHttpResponse
from base.models import Project, Sign, Environment, Interface, Case, Plan, Report, LocustReport
from accounts.models import BlogUser as User
# from django.contrib.auth.models import User  # django自带user
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.db.models import Q  # 与或非 查询
from common.execute import Test_execute, get_user, is_superuser  # 执行接口
from djcelery.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from datetime import timedelta, datetime
from common.swagger import AnalysisJson
from django.shortcuts import render_to_response
# from base.page_cache import page_cache  # redis缓存
from common.public import DrawPie, paginator, pagination_data
from common.error_code import ErrorCode
from common.except_check import project_info_logic, sign_info_logic, env_info_logic, interface_info_logic, \
    format_params, \
    case_info_logic, plan_info_logic, header_value_error  # 自定义异常逻辑
from django.views.generic import ListView

# import paramiko
# from stat import S_ISDIR as isdir
# from common import readConfig

log = logging.getLogger('log')  # 初始化log
logs_path = os.path.join(os.getcwd(), 'logs')  # 拼接删除目录完整路径
start_time = ''  # 执行测试计划开始时间
totalTime = ''  # 执行测试计划运行时间
now_time = ''  # 饼图命名区分
class_name = ''  # 执行测试类


# 项目列表
# @page_cache(5)
@method_decorator(login_required, name='dispatch')
class ProjectIndex(ListView):
    model = Project
    template_name = 'base/project/index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(ProjectIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        superuser = User.objects.get(id=user_id).is_superuser
        if superuser:
            return Project.objects.all().order_by('-prj_id')
        else:
            return Project.objects.filter(user_id=user_id).order_by('-prj_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def project_add(request):
    """
    增加项目
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return HttpResponseRedirect('/login/')
    else:
        sign_list = Sign.objects.all()  # 所有签名
        if request.method == 'POST':
            prj_name = request.POST['prj_name'].strip()

            msg = project_info_logic(prj_name)
            if msg != 'ok':  # 判断输入框
                log.error('project add error：{}'.format(msg))
                info = {'error': msg, "sign_list": sign_list}
                return render(request, 'base/project/add.html', info)
            else:
                description = request.POST['description']
                sign_id = request.POST['sign']
                sign = Sign.objects.get(sign_id=sign_id)
                user = User.objects.get(id=user_id)
                prj = Project(prj_name=prj_name, description=description, sign=sign, user=user)
                prj.save()
                log.info('add project   {}  success. project info: {} // {} '.format(prj_name, description, sign))
                return HttpResponseRedirect("/base/project/")
        elif request.method == 'GET':
            info = {"sign_list": sign_list}
            return render(request, "base/project/add.html", info)


def project_update(request):
    """
    项目编辑
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return HttpResponseRedirect('/login/')
    else:
        sign_list = Sign.objects.all()
        if request.method == 'POST':
            prj_id = request.POST['prj_id']
            prj_name = request.POST['prj_name'].strip()

            msg = project_info_logic(prj_name, prj_id)
            if msg != 'ok':
                log.error('project update error：{}'.format(msg))
                prj = Project.objects.get(prj_id=prj_id)
                info = {'error': msg, "prj": prj, "sign_list": sign_list}
                return render(request, 'base/project/update.html', info)
            else:
                description = request.POST['description']
                sign_id = request.POST['sign_id']
                sign = Sign.objects.get(sign_id=sign_id)
                user = User.objects.get(id=user_id)
                Project.objects.filter(prj_id=prj_id).update(prj_name=prj_name, description=description, sign=sign,
                                                             user=user, update_time=timezone.now())
                log.info('edit project   {}  success. project info: {} // {} '.format(prj_name, description, sign))
                return HttpResponseRedirect("/base/project/")
        elif request.method == 'GET':
            prj_id = request.GET['prj_id']
            user_id_belong = Project.objects.get(prj_id=prj_id).user_id
            if user_id == user_id_belong:
                prj = Project.objects.get(prj_id=prj_id)
                info = {"prj": prj, "sign_list": sign_list}
                return render(request, "base/project/update.html", info)
            else:
                return render(request, "base/project/update.html", {'error': '非本人创建项目，不可以修改！'})


def project_delete(request):
    """
    删除项目
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/project/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            prj_id = request.GET['prj_id']
            Project.objects.filter(prj_id=prj_id).delete()
            log.info('用户 {} 删除项目 {} 成功.'.format(user_id, prj_id))
            return HttpResponseRedirect("base/project/")


# 签名列表
# @page_cache(5)
@method_decorator(login_required, name='dispatch')
class SignIndex(ListView):
    model = Sign
    template_name = 'base/sign/sign_index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(SignIndex, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def sign_add(request):
    """
    添加签名
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/sign/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            sign_name = request.POST['sign_name'].strip()

            msg = sign_info_logic(sign_name)
            if msg != 'ok':
                log.error('sign add error：{}'.format(msg))
                info = {'error': msg}
                return render(request, 'base/sign/sign_add.html', info)
            else:
                description = request.POST['description']
                username = request.session.get('user', '')
                sign = Sign(sign_name=sign_name, description=description, update_user=username)
                sign.save()
                log.info('add sign   {}  success.  sign info： {} '.format(sign_name, description))
                return HttpResponseRedirect("/base/sign/")
        elif request.method == 'GET':
            return render(request, "base/sign/sign_add.html")


def sign_update(request):
    """
    更新签名
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/sign/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            sign_id = request.POST['sign_id']
            sign_name = request.POST['sign_name'].strip()

            msg = sign_info_logic(sign_name, sign_id)
            if msg != 'ok':
                log.error('sign update error：{}'.format(msg))
                sign = Sign.objects.get(sign_id=sign_id)
                info = {'error': msg, "sign": sign}
                return render(request, 'base/sign/sign_update.html', info)
            else:
                description = request.POST['description']
                username = request.session.get('user', '')
                Sign.objects.filter(sign_id=sign_id).update(sign_name=sign_name, description=description,
                                                            update_time=timezone.now(), update_user=username)
                log.info('edit sign   {}  success.  sign info： {} '.format(sign_name, description))
                return HttpResponseRedirect("/base/sign/")
        elif request.method == 'GET':
            sign_id = request.GET['sign_id']
            sign = Sign.objects.get(sign_id=sign_id)
            info = {"sign": sign}
            return render(request, "base/sign/sign_update.html", info)


def sign_delete(request):
    """
    删除签名
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/sign/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            sign_id = request.GET['sign_id']
            Sign.objects.filter(sign_id=sign_id).delete()
            log.info('用户 {} 删除签名 {} 成功.'.format(user_id, sign_id))
            return HttpResponseRedirect("base/sign/")


# 测试环境列表
# @page_cache(5)
@method_decorator(login_required, name='dispatch')
class EnvIndex(ListView):
    model = Environment
    template_name = 'base/env_temp/index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(EnvIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        prj_list = is_superuser(user_id, type='list')
        return Environment.objects.filter(project_id__in=prj_list).order_by('-env_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def set_headers(request):
    """
    设置默认headers
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/env_temp/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            env_id = request.GET.get('env_id', '')
            make = request.GET.get('make', '')
            env = Environment.objects.get(env_id=env_id)
            env_name = env.env_name
            set_header = env.set_headers
            if make:
                if set_header:
                    set_header = eval(set_header)['header']
                    return JsonResponse(set_header)
                else:
                    return JsonResponse('0', safe=False)
            else:
                info = {'env_id': env_id, 'env_name': env_name, 'env_temp': set_header}
                return render(request, "base/env_temp/set_headers.html", info)
        elif request.method == 'POST':
            content = request.POST.get('content', '')

            msg = header_value_error(content)
            if msg != 'ok':
                log.error('set headers error：{}'.format(msg))
                return HttpResponse(msg)
            else:
                env_id = request.POST.get('env_id', '')
                now_time = timezone.now()
                username = request.session.get('user', '')
                Environment.objects.filter(env_id=env_id).update(set_headers=content, update_time=now_time,
                                                                 update_user=username)
                log.info('env_temp {} set headers success. headers info: {} '.format(env_id, content))
                return HttpResponseRedirect("/base/env_temp/")


def set_mock(request):
    """
    设置默认mock
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/env_temp/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            if_id = request.GET.get('if_id', '')
            make = request.GET.get('make', '')
            interface = Interface.objects.get(if_id=if_id)
            if_name = interface.if_name
            set_mock = interface.set_mock
            if make:
                if set_mock:
                    set_mock = eval(set_mock)['mock']
                    return JsonResponse(set_mock)
                else:
                    return JsonResponse('0', safe=False)
            else:
                info = {'if_id': if_id, 'if_name': if_name, 'env_temp': set_mock}
                return render(request, "base/interface/set_mock.html", info)
        elif request.method == 'POST':
            content = request.POST.get('content', '')
            if_id = request.POST.get('if_id', '')
            now_time = timezone.now()
            username = request.session.get('user', '')
            Interface.objects.filter(if_id=if_id).update(set_mock=content, update_time=now_time, update_user=username)
            log.info('interface {} set mock success. mock info: {} '.format(if_id, content))
            return HttpResponseRedirect("/base/interface/")


def env_add(request):
    """
    添加环境
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/env_temp/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            prj_list = is_superuser(user_id)
            env_name = request.POST['env_name'].strip()
            url = request.POST['url'].strip()

            msg = env_info_logic(env_name, url)
            if msg != 'ok':
                log.error('env_temp add error：{}'.format(msg))
                info = {'error': msg, "prj_list": prj_list}
                return render(request, 'base/env_temp/add.html', info)
            else:
                prj_id = request.POST['prj_id']
                project = Project.objects.get(prj_id=prj_id)
                private_key = request.POST['private_key']
                description = request.POST['description']
                is_swagger = request.POST['is_swagger']
                username = request.session.get('user', '')
                if is_swagger == '1':
                    Environment.objects.filter(is_swagger=1).update(is_swagger=0)
                env = Environment(env_name=env_name, url=url, project=project, private_key=private_key,
                                  description=description, is_swagger=is_swagger, update_user=username)
                env.save()
                log.info('add env_temp   {}  success.  env_temp info： {} // {} // {} // {} // {} '
                         .format(env_name, project, url, private_key, description, is_swagger))
                return HttpResponseRedirect("/base/env_temp/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            info = {"prj_list": prj_list}
            return render(request, "base/env_temp/add.html", info)


def env_update(request):
    """
    测试环境更新
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/env_temp/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            prj_list = is_superuser(user_id)
            env_id = request.POST['env_id']
            env_name = request.POST['env_name'].strip()
            url = request.POST['url'].strip()

            msg = env_info_logic(env_name, url, env_id)
            if msg != 'ok':
                log.error('env_temp update error：{}'.format(msg))
                env = Environment.objects.get(env_id=env_id)
                info = {'error': msg, "env_temp": env, "prj_list": prj_list}
                return render(request, 'base/env_temp/update.html', info)
            else:
                prj_id = request.POST['prj_id']
                project = Project.objects.get(prj_id=prj_id)

                private_key = request.POST['private_key']
                description = request.POST['description']
                is_swagger = request.POST['is_swagger']
                username = request.session.get('user', '')
                if is_swagger == '1':
                    Environment.objects.filter(is_swagger=1).update(is_swagger=0)
                Environment.objects.filter(env_id=env_id).update(env_name=env_name, url=url, project=project,
                                                                 private_key=private_key, description=description,
                                                                 update_time=timezone.now(), is_swagger=is_swagger,
                                                                 update_user=username)
                log.info('edit env_temp   {}  success.  env_temp info： {} // {} // {} // {} // {}'
                         .format(env_name, project, url, private_key, description, is_swagger))
                return HttpResponseRedirect("/base/env_temp/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            env_id = request.GET['env_id']
            env = Environment.objects.get(env_id=env_id)
            info = {"env_temp": env, "prj_list": prj_list}
            return render(request, "base/env_temp/update.html", info)


def env_delete(request):
    """
    删除测试环境
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/env_temp/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            env_id = request.GET['env_id']
            Environment.objects.filter(env_id=env_id).delete()
            log.info('用户 {} 删除环境 {} 成功.'.format(user_id, env_id))
            return HttpResponseRedirect("base/env_temp/")


# 接口列表
@method_decorator(login_required, name='dispatch')
class InterfaceIndex(ListView):
    model = Interface
    template_name = 'base/interface/index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(InterfaceIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        prj_list = is_superuser(user_id, type='list')
        return Interface.objects.filter(project_id__in=prj_list).order_by('-if_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def interface_copy(request):
    """
    复制interface
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            if_id = request.GET.get('if_id', '')
            interface_ = Interface.objects.get(if_id=if_id)
            if_name = interface_.if_name + 'copy'
            url = interface_.url
            method = interface_.method
            data_type = interface_.data_type
            is_sign = interface_.is_sign
            is_header = interface_.is_header
            mock = interface_.set_mock
            description = interface_.description
            request_header_param = interface_.request_header_param
            request_body_param = interface_.request_body_param
            response_header_param = interface_.response_header_param
            response_body_param = interface_.response_body_param
            project = interface_.project
            username = request.session.get('user', '')
            interface = Interface(if_name=if_name, url=url, project=project, method=method, data_type=data_type,
                                  is_sign=is_sign, description=description, request_header_param=request_header_param,
                                  request_body_param=request_body_param, response_header_param=response_header_param,
                                  response_body_param=response_body_param, is_header=is_header, update_user=username,
                                  set_mock=mock)
            interface.save()
            log.info(
                'add interface  {}  success.  interface info： {} // {} // {} // {} // {} // {} // {} // {} // {} // {} '
                    .format(if_name, project, url, method, data_type, is_sign, description, request_header_param,
                            request_body_param, response_header_param, response_body_param, is_header))
            return HttpResponseRedirect("base/interface/")


def interface_search(request):
    """
    接口搜索功能
    :param request:
    :return:
    """
    if request.method == 'POST':
        user_id = request.session.get('user_id', '')
        if get_user(user_id):
            search = request.POST.get('search', '').strip()
            if_list = []
            if not search:
                return HttpResponse('0')
            else:
                prj_list = is_superuser(user_id, type='list')
                if search in ['get', 'post', 'delete', 'put']:  # 请求方式查询
                    interface_list = Interface.objects.filter(method__contains=search).filter(project_id__in=prj_list)
                elif search in ['data', 'json']:  # 数据传输类型查询
                    interface_list = Interface.objects.filter(data_type__contains=search).filter(
                        project_id__in=prj_list)
                else:
                    try:
                        if isinstance(int(search), int):
                            if search in ['0', '1']:  # 设置header、签名查询
                                interface_list = Interface.objects.filter(
                                    Q(is_header=search) | Q(is_sign=search) | Q(if_id__exact=search) | Q(
                                        if_name__contains=search)).filter(project_id__in=prj_list)
                            else:  # ID查询
                                interface_list = Interface.objects.filter(
                                    Q(if_id__exact=search) | Q(if_name__contains=search)).filter(
                                    project_id__in=prj_list)
                    except ValueError:
                        interface_list = Interface.objects.filter(
                            Q(if_name__contains=search) | Q(project__prj_name__contains=search)).filter(
                            project_id__in=prj_list)  # 接口名称、项目名称查询
                if not interface_list:  # 查询为空
                    return HttpResponse('1')
                else:
                    for interface in interface_list:
                        interface_dict = {'if_id': str(interface.if_id), 'if_name': interface.if_name,
                                          'project': interface.project.prj_name, 'method': interface.method,
                                          'data_type': interface.data_type, 'is_sign': interface.is_sign,
                                          'description': interface.description,
                                          'response_header_param': interface.response_header_param,
                                          'update_time': str(interface.update_time).split('.')[0],
                                          'update_user': interface.update_user}
                        if_list.append(interface_dict)
                    return HttpResponse(str(if_list))
        else:
            return HttpResponse('2')


def interface_add(request):
    """
    添加接口
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/interface/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            if_name = request.POST['if_name'].strip()
            prj_id = request.POST['prj_id']
            url = request.POST['url'].strip()
            method = request.POST.get('method', '')
            data_type = request.POST['data_type']
            is_sign = request.POST.get('is_sign', '')
            is_headers = request.POST.get('is_headers', '')
            mock = request.POST.get('mock', '')
            request_header_data = request.POST['request_header_data']
            request_body_data = request.POST['request_body_data']
            # response_header_data = request.POST['response_header_data']
            # response_body_data = request.POST['response_body_data']

            msg = interface_info_logic(if_name, url, method, is_sign, data_type, is_headers, request_header_data,
                                       request_body_data)
            if msg != 'ok':
                log.error('interface add error：{}'.format(msg))
                return HttpResponse(msg)
            description = request.POST['description']
            username = request.session.get('user', '')
            if is_headers == '1':
                Interface.objects.filter(project_id=prj_id).filter(is_header=1).update(is_header=0)
            project = Project.objects.get(prj_id=prj_id)
            interface = Interface(if_name=if_name, url=url, project=project, method=method, data_type=data_type,
                                  is_sign=is_sign, description=description, request_header_param=request_header_data,
                                  request_body_param=request_body_data, is_header=is_headers, update_user=username,
                                  set_mock=mock)
            interface.save()
            log.info(
                'add interface  {}  success.  interface info： {} // {} // {} // {} // {} // {} // {} // {} //  '
                    .format(if_name, project, url, method, data_type, is_sign, description, request_header_data,
                            request_body_data, is_headers))
            return HttpResponseRedirect("/base/interface/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            info = {"prj_list": prj_list}
            return render(request, "base/interface/add.html", info)


def interface_update(request):
    """
    接口编辑
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/interface/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            if_id = request.POST['if_id']
            if_name = request.POST['if_name'].strip()
            prj_id = request.POST['prj_id']
            url = request.POST['url'].strip()
            method = request.POST.get('method', '')
            data_type = request.POST['data_type']
            is_sign = request.POST.get('is_sign', '')
            is_headers = request.POST.get('is_headers', '')
            mock = request.POST.get('mock', '')
            request_header_data_list = request.POST.get('request_header_data', [])
            request_header_data = interface_format_params(request_header_data_list)
            request_body_data_list = request.POST.get('request_body_data', [])
            request_body_data = interface_format_params(request_body_data_list)
            # response_header_data_list = request.POST.get('response_header_data', [])
            # response_header_data = interface_format_params(response_header_data_list)
            # response_body_data_list = request.POST.get('response_body_data', [])
            # response_body_data = interface_format_params(response_body_data_list)

            msg = interface_info_logic(if_name, url, method, is_sign, data_type, is_headers, request_header_data,
                                       request_body_data, if_id)
            if msg != 'ok':
                log.error('interface update error：{}'.format(msg))
                return HttpResponse(msg)
            else:
                description = request.POST['description']
                username = request.session.get('user', '')
                if is_headers == '1':
                    Interface.objects.filter(project_id=prj_id).filter(is_header=1).update(is_header=0)
                project = Project.objects.get(prj_id=prj_id)
                Interface.objects.filter(if_id=if_id).update(if_name=if_name, url=url, project=project, method=method,
                                                             data_type=data_type, is_header=is_headers,
                                                             is_sign=is_sign, description=description,
                                                             request_header_param=request_header_data,
                                                             request_body_param=request_body_data, set_mock=mock,
                                                             update_time=timezone.now(), update_user=username)
                log.info(
                    'edit interface  {}  success.  interface info： {} // {} // {} // {} // {} // {} // {} // {} // {} //  '.format(
                        if_name, project, url, method, data_type, is_sign, description, request_header_data,
                        request_body_data, is_headers))
                return HttpResponseRedirect("/base/interface/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            if_id = request.GET['if_id']
            interface = Interface.objects.get(if_id=if_id)
            request_header_param_list = interface_get_params(interface.request_header_param)
            request_body_param_list = interface_get_params(interface.request_body_param)
            # response_header_param_list = interface_get_params(interface.response_header_param)
            # response_body_param_list = interface_get_params(interface.response_body_param)
            method, is_sign, is_headers, mock = format_params(interface)
            info = {"interface": interface, 'request_header_param_list': request_header_param_list,
                    'request_body_param_list': request_body_param_list, 'method': method, 'is_sign': is_sign,
                    'is_headers': is_headers, 'mock': mock, "prj_list": prj_list}
            return render(request, "base/interface/update.html", info)


def interface_get_params(params):
    """
    解析数据库中格式化前的参数
    :param params:
    :return:
    """
    if params and params != '[]':
        param_list = []
        for i in range(len(eval(params))):
            param_list.append({"var_name": "", "var_remark": ""})
            param_list[i]['var_name'] = eval(params)[i]['var_name']
        return param_list
    else:
        return []


def interface_format_params(params_list):
    """
    格式化存入数据库中的参数
    :param params_list:
    :return:
    """
    if params_list:
        var = []
        params_list = eval(params_list)
        for i in range(len(params_list)):
            var.append({"var_name": "", "var_remark": ""})
            var[i]['var_name'] = params_list[i]['var_name']
        return json.dumps(var)
    else:
        return []


def interface_delete(request):
    """
    接口删除
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/interface/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            if_id = request.GET['if_id']
            Interface.objects.filter(if_id=if_id).delete()
            log.info('用户 {} 删除接口 {} 成功.'.format(user_id, if_id))
            return HttpResponseRedirect("base/interface/")


# 执行导入的异步线程
class BatchInterface(threading.Thread):
    def run(self):
        for key, value in self.interface.items():
            log.info(timezone.now().strftime('%Y-%m-%d %H:%M:%S') + " {} ==== BatchInterface ".format(self.getName(), ))
            if_name = value.get('name', '').strip()
            method = value.get('method', '')
            prj_list = is_superuser(self.user_id, type='list')
            tags = value.get('tags', '')
            url = value.get('url', '')
            data_type = value.get('type', '')
            headers = value.get('headers', '')
            body = value.get('body', '')
            project_id = value.get('prj_id', '')
            is_sign = 0
            is_headers = 0
            mock = '0'
            description = ''
            request_header_data = []
            request_body_data = []
            response_body_data = []
            if isinstance(headers, dict):
                for k, v in headers.items():
                    headers_data = {}
                    headers_data['var_name'] = k
                    if isinstance(v, dict):
                        v = json.dumps(v)
                    headers_data['var_remark'] = ''
                    request_header_data.append(headers_data)
            if isinstance(body, dict):
                for k, v in body.items():
                    body_data = {}
                    body_data['var_name'] = k
                    if isinstance(v, dict):
                        v = json.dumps(v)
                    body_data['var_remark'] = ''
                    request_body_data.append(body_data)
            project = Project.objects.get(prj_id=int(project_id))
            username = self.request.session.get('user', '')
            interface_list = Interface.objects.filter(if_name=if_name).filter(url=url).filter(method=method).filter(
                project_id__in=prj_list)
            if interface_list:
                for name in interface_list:
                    Interface.objects.filter(if_id=name.if_id).update(if_name=if_name, url=url, project=project,
                                                                      method=method, response_header_param=tags,
                                                                      data_type=data_type, description=description,
                                                                      request_header_param=json.dumps(
                                                                          request_header_data),
                                                                      request_body_param=json.dumps(request_body_data),
                                                                      update_time=timezone.now(), update_user=username)
                log.warning('接口名称已存在，更新接口参数中... ==> {}'.format(if_name))
            else:
                log.info('接口名称：{}， 正在批量导入中...'.format(if_name))
                interface_tbl = Interface(if_name=if_name, url=url, project=project, method=method,
                                          data_type=data_type, is_header=is_headers,
                                          is_sign=is_sign, description=description,
                                          request_header_param=json.dumps(request_header_data),
                                          request_body_param=json.dumps(request_body_data),
                                          response_header_param=tags, set_mock=mock,
                                          response_body_param=response_body_data, update_user=username)
                interface_tbl.save()

    def __init__(self, interface, request, user_id):
        threading.Thread.__init__(self)
        self.interface = interface
        self.request = request
        self.user_id = user_id
        self.setDaemon(True)  # 守护线程


def batch_index(request):
    """
    批量导入接口
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        return HttpResponse('用户未登录！')
    else:
        if request.method == 'GET':
            # Interface.objects.all().delete()  # 清空接口表
            # Case.objects.all().delete()  # 清空用例表
            # Plan.objects.all().delete()  # 清空计划表
            # Report.objects.all().delete()  # 清空报告表
            try:
                prj_list = is_superuser(user_id, type='list')
                env = Environment.objects.filter(project_id__in=prj_list).get(is_swagger=1)
                env_url = env.url
                prj_id = env.project_id
                interface = AnalysisJson(prj_id, env_url).retrieve_data()
                if interface == 'error':
                    return HttpResponse('请求swagger url 发生错误，请联系管理员！')
                elif isinstance(interface, dict):
                    log.info('项目 {} 开始批量导入...'.format(prj_id))
                    batch = BatchInterface(interface, request, user_id)
                    batch.start()
                    return HttpResponse('批量导入成功！ ==> {}'.format(prj_id))
            except Environment.DoesNotExist:
                return HttpResponse('测试环境中未设置从swagger导入！')


# 用例首页
@method_decorator(login_required, name='dispatch')
class CaseIndex(ListView):
    model = Case
    template_name = 'base/case/index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(CaseIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        prj_list = is_superuser(user_id, type='list')
        return Case.objects.filter(project_id__in=prj_list).order_by('-case_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def case_add(request):
    """
    添加用例
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            case_name = request.POST.get('case_name', '').strip()
            content = request.POST.get('content')

            msg = case_info_logic(case_name, content)
            if msg != 'ok':
                log.error('case add error：{}'.format(msg))
                return HttpResponse(msg)
            else:
                prj_id = request.POST['prj_id']
                project = Project.objects.get(prj_id=prj_id)
                description = request.POST['description']
                username = request.session.get('user', '')
                case = Case(case_name=case_name, project=project, description=description,
                            content=content, update_user=username)
                case.save()
                log.info('add case   {}  success. case info: {} // {} // {}'.format(case_name, project, description,
                                                                                    content))
                return HttpResponseRedirect("/base/case/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            info = {"prj_list": prj_list}
            return render(request, "base/case/add.html", info)


def case_update(request):
    """
    编辑用例
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            case_id = request.POST['case_id']
            case_name = request.POST.get('case_name', '').strip()
            content = request.POST.get('content')
            msg = case_info_logic(case_name, content, case_id)
            if msg != 'ok':
                log.error('case update error：{}'.format(msg))
                return HttpResponse(msg)
            else:
                prj_id = request.POST['prj_id']
                project = Project.objects.get(prj_id=prj_id)
                description = request.POST['description']
                username = request.session.get('user', '')
                Case.objects.filter(case_id=case_id).update(case_name=case_name, project=project,
                                                            description=description,
                                                            content=content, update_time=timezone.now(),
                                                            update_user=username)
                log.info('edit case   {}  success. case info: {} // {} // {}'
                         .format(case_name, project, description, content))
                return HttpResponseRedirect("/base/case/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            case_id = request.GET['case_id']
            case = Case.objects.get(case_id=case_id)
            interface = Interface.objects.filter(project_id=case.project_id).all().values()
            if_list = ''
            for i in eval(case.content):
                if_list += i['if_id'] + ','
            if eval(case.content):
                if_id = eval(case.content)[0]['if_id']  # 默认显示第一个接口名称
                if_name = eval(case.content)[0]['if_name']
            else:
                if_id = '1'
                if_name = '请选择接口'
            interface_list = []  # 返回所有接口
            for i in interface:
                interface_list.append(i)
            info = {"prj_list": prj_list, 'case': case, 'interface': interface, 'case_id': case_id,
                    'if_id': if_id, 'if_list': str(if_list), 'if_name': if_name}
            return render_to_response('base/case/update.html', info)


def case_copy(request):
    """
    复制case
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            case_id = request.GET.get('case_id', '')
            case_ = Case.objects.get(case_id=case_id)
            case_name = case_.case_name + 'copy'
            content = case_.content
            project = case_.project
            description = case_.description
            username = request.session.get('user', '')
            case = Case(case_name=case_name, project=project, description=description, update_time=timezone.now(),
                        content=content, update_user=username)
            case.save()
            log.info('copy case   {}  success. case info: {} // {} '.format(case_name, project, content))
            return HttpResponseRedirect("base/case/")


def case_search(request):
    """
    用例搜索功能
    :param request:
    :return:
    """
    if request.method == 'POST':
        user_id = request.session.get('user_id', '')
        if get_user(user_id):
            search = request.POST.get('search', '').strip()
            case_list = []
            if not search:
                return HttpResponse('0')
            else:
                case = Case.objects.filter(case_name__contains=search)

                if not case:  # 查询为空
                    return HttpResponse('1')
                else:
                    for case_ in case:
                        case_dict = {'case_id': str(case_.case_id), 'case_name': case_.case_name,
                                     'project': case_.project.prj_name, 'description': case_.description,
                                     'update_time': str(case_.update_time).split('.')[0],
                                     'update_user': case_.update_user, 'prj_id': case_.project.prj_id}
                        case_list.append(case_dict)
                    return HttpResponse(str(case_list))
        else:
            return HttpResponse('2')


def case_logs(request):
    """
    单个用例运行日志
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        superuser = User.objects.get(id=user_id).is_superuser
        if superuser:
            log_file_list = os.listdir(logs_path)
            data_list = []
            file_list = []
            now = time.strftime('%Y-%m-%d')
            for file in log_file_list:
                if 'all' in file and now in file:
                    file_list.append(file)
            if not file_list:
                yesterday = datetime.today() + timedelta(-1)
                yesterday_format = yesterday.strftime('%Y-%m-%d')
                for file in log_file_list:
                    if 'all' in file and yesterday_format in file:
                        file_list.append(file)
            try:
                file_list.sort()
                log_file = os.path.join(logs_path, file_list[0])
            except IndexError:
                for file in log_file_list:
                    if 'all' in file:
                        file_list.append(file)
                file_list.sort()
                log_file = os.path.join(logs_path, file_list[-1])
            with open(log_file, 'rb') as f:
                off = -1024 * 1024
                if f.tell() < -off:
                    data = f.readlines()
                else:
                    f.seek(off, 2)
                    data = f.readlines()
                for line in data:
                    data_list.append(line.decode())
                info = {'data': data_list, 'make': True, 'log_file': log_file}
                log.info('case_logs 查询日志文件名称 ===========================>>> {}'.format(log_file))
                return render(request, 'base/case/log.html', info)
        else:
            info = {'data': '0', 'make': True, 'log_file': ''}
            return render(request, 'base/case/log.html', info)


def case_delete(request):
    """
    删除用例
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            case_id = request.GET['case_id']
            Case.objects.filter(case_id=case_id).delete()
            log.info('用户 {} 删除用例 {} 成功.'.format(user_id, case_id))
            return HttpResponseRedirect("base/case/")


def case_run(request):
    """
    运行用例
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        return JsonResponse({'error': ErrorCode.user_not_logged_in_error})
    else:
        if request.method == 'POST':
            case_id = request.POST['case_id']
            env_id = request.POST['env_id']
            username = request.session.get('user', '')
            log.info('用户 {} 在 {} 环境 运行用例 {} .'.format(username, env_id, case_id))
            execute = Test_execute(env_id, ['1'], case_id=case_id)
            case_result = execute.test_case
            Case.objects.filter(case_id=case_id).update(update_user=username)
            return JsonResponse(case_result)


# 测试计划列表
@method_decorator(login_required, name='dispatch')
class PlanIndex(ListView):
    model = Plan
    template_name = 'base/plan/index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(PlanIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        prj_list = is_superuser(user_id, type='list')
        return Plan.objects.filter(project_id__in=prj_list).order_by('-plan_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def plan_add(request):
    """
    测试计划添加
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/plan/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            prj_list = is_superuser(user_id)
            plan_name = request.POST['plan_name'].strip()
            content = request.POST.getlist("case_id")

            msg = plan_info_logic(plan_name, content)
            if msg != 'ok':
                log.error('plan add error：{}'.format(msg))
                return render(request, 'base/plan/add.html', {'error': msg, "prj_list": prj_list})
            else:
                prj_id = request.POST['prj_id']
                project = Project.objects.get(prj_id=prj_id)
                is_locust = request.POST['is_locust']
                is_task = request.POST['is_task']
                env_id = request.POST['env_id']
                environment = Environment.objects.get(env_id=env_id)
                description = request.POST['description']
                username = request.session.get('user', '')
                if is_locust == '1':
                    Plan.objects.filter(is_locust=1).update(is_locust=0)
                if is_task == '1':
                    Plan.objects.filter(is_task=1).update(is_task=0)
                plan = Plan(plan_name=plan_name, project=project, environment=environment, description=description,
                            content=content, is_locust=is_locust, is_task=is_task, update_user=username)
                plan.save()
                log.info('add plan   {}  success. plan info: {} // {} // {} // {} //{} //{}'.
                         format(plan_name, project, environment, description, content, is_locust, is_task))
                return HttpResponseRedirect("/base/plan/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            info = {"prj_list": prj_list}
            return render(request, "base/plan/add.html", info)


def plan_update(request):
    """
    测试计划编辑
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/plan/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'POST':
            prj_list = is_superuser(user_id)
            plan_id = request.POST['plan_id']
            plan_name = request.POST['plan_name'].strip()
            content = request.POST.getlist("case_id")
            plan = Plan.objects.get(plan_id=plan_id)
            environments = Environment.objects.filter(project_id=plan.project_id).all().values()
            case_list = []
            for case_id in eval(plan.content):
                case = Case.objects.get(case_id=case_id)
                case_list.append(case)

            msg = plan_info_logic(plan_name, content, plan_id)
            if msg != 'ok':
                log.error('plan update error：{}'.format(msg))
                return render(request, 'base/plan/update.html',
                              {'error': msg, "prj_list": prj_list, 'plan': plan, 'case_list': case_list,
                               'environments': environments})
            else:
                prj_id = request.POST['prj_id']
                project = Project.objects.get(prj_id=prj_id)
                is_locust = request.POST['is_locust']
                env_id = request.POST['env_id']
                is_task = request.POST['is_task']
                environment = Environment.objects.get(env_id=env_id)
                description = request.POST['description']

                username = request.session.get('user', '')

                if is_locust == '1':
                    Plan.objects.filter(is_locust=1).update(is_locust=0)
                if is_task == '1':
                    Plan.objects.filter(is_task=1).update(is_task=0)
                Plan.objects.filter(plan_id=plan_id).update(plan_name=plan_name, project=project,
                                                            environment=environment,
                                                            description=description, content=content,
                                                            is_locust=is_locust,
                                                            is_task=is_task, update_time=timezone.now(),
                                                            update_user=username)
                log.info(
                    'edit plan   {}  success. plan info: {} // {} // {} // {}'.format(plan_name, project, environment,
                                                                                      description, content))
                return HttpResponseRedirect("/base/plan/")
        elif request.method == 'GET':
            prj_list = is_superuser(user_id)
            plan_id = request.GET['plan_id']
            plan = Plan.objects.get(plan_id=plan_id)
            environments = Environment.objects.filter(project_id=plan.project_id).all().values()
            case_list = []
            for case_id in eval(plan.content):
                try:
                    case = Case.objects.get(case_id=case_id)
                    case_list.append(case)
                except Case.DoesNotExist as e:
                    log.error('计划 {} 中的 用例 {} 已被删除！！！'.format(plan.plan_name, case_id))
                    plans = Plan.objects.all().order_by('-plan_id')
                    page = request.GET.get('page')
                    contacts = paginator(plans, page)
                    return render(request, "base/plan/index.html",
                                  {"contacts": contacts,
                                   'error': '计划 {} 中的 用例 {} 已被删除！！！'.format(plan.plan_name, case_id)})
            info = {"prj_list": prj_list, 'plan': plan, 'case_list': case_list, 'environments': environments}
            return render(request, "base/plan/update.html", info)


def plan_delete(request):
    """
    删除测试计划
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/plan/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            plan_id = request.GET['plan_id']
            Plan.objects.filter(plan_id=plan_id).delete()
            log.info('用户 {} 删除计划 {} 成功.'.format(user_id, plan_id))
            return HttpResponseRedirect("base/plan/")


def plan_run(request):
    """
    运行测试计划
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        return JsonResponse({'error': ErrorCode.user_not_logged_in_error})
    else:
        if request.method == 'POST':
            global totalTime, start_time, now_time
            begin_time = time.clock()
            start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            now_time = int(time.mktime(time.strptime(start_time, '%Y-%m-%d %H:%M:%S')))
            plan_id = request.POST.get('plan_id', '')
            run_mode = request.POST.get('run_mode', '')
            plan = Plan.objects.get(plan_id=plan_id)
            env_id = plan.environment.env_id
            case_id_list = eval(plan.content)
            case_num = len(case_id_list)
            content = []
            j = 0
            i = 0
            pass_num = 0
            fail_num = 0
            error_num = 0
            if run_mode == '1':
                execute = Test_execute(env_id, case_id_list, run_mode=run_mode, plan=plan)
                case_result = execute.test_case
                report_path = case_result['report_path']
                for records in case_result['summary']['details'][0]['records']:
                    j += 1
                    records['id'] = j
                    for data in records.get('meta_datas', {}).get('data', {}):
                        body = json.dumps(data.get('request', {}).get('body', {}), ensure_ascii=False).replace(
                            'Markup', '').replace('&#34;', '')
                        if body:
                            data['request']['body'] = body.encode('utf-8').decode('unicode_escape').encode(
                                'utf-8').decode('unicode_escape')
                if isinstance(case_result, dict):
                    content.append(case_result)
                else:
                    return HttpResponse(case_result)
                summary = case_result.get('summary', {})
                stat = summary.get('stat', {}).get('teststeps', {})
                pass_num = stat.get('successes', 0)
                fail_num = stat.get('failures', 0)
                error_num = stat.get('errors', 0)
            elif run_mode == '0':
                for case_id in case_id_list:
                    execute = Test_execute(env_id, case_id_list, run_mode, plan, case_id=case_id)
                    case_result = execute.test_case
                    if isinstance(case_result, dict):
                        content.append(case_result)
                    else:
                        return HttpResponse(case_result)
                for step in content:
                    if 'error' in step.keys():
                        log.error('plan run error：{}'.format(step['msg']))
                        return HttpResponse(step['msg'])
                    else:
                        for s in step['step_list']:
                            if s["result"] == "pass":
                                pass_num += 1
                                i += 1
                                s['id'] = i
                            if s["result"] == "fail":
                                fail_num += 1
                                i += 1
                                s['id'] = i
                            if s["result"] == "error":
                                error_num += 1
                                i += 1
                                s['id'] = i
            end_time = time.clock()
            totalTime = str(end_time - begin_time)[:6] + ' s'
            pic_name = DrawPie(pass_num, fail_num, error_num)
            report_name = plan.plan_name + "-" + str(start_time).replace(':', '-')
            username = request.session.get('user', 'lixiaofeng')
            if run_mode == '1':
                report = Report(plan=plan, report_name=report_name, content=content, case_num=case_num,
                                pass_num=pass_num, fail_num=fail_num, error_num=error_num, pic_name=pic_name,
                                totalTime=totalTime, startTime=start_time, update_user=username, make=1,
                                report_path=report_path)
            elif run_mode == '0':
                report = Report(plan=plan, report_name=report_name, content=content, case_num=case_num,
                                pass_num=pass_num, fail_num=fail_num, error_num=error_num, pic_name=pic_name,
                                totalTime=totalTime, startTime=start_time, update_user=username, make=0, report_path='')
            report.save()
            Plan.objects.filter(plan_id=plan_id).update(update_user=username, update_time=timezone.now())
            return HttpResponse(" 执行成功！")


def timing_task(request):
    """
    定时任务
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/timing_task/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            task_list = PeriodicTask.objects.all()
            task_count = PeriodicTask.objects.all().count()  # 统计数
            periodic_list = IntervalSchedule.objects.all()  # 周期任务 （如：每隔1小时执行1次）
            crontab_list = CrontabSchedule.objects.all()  # 定时任务 （如：某年月日的某时，每天的某时）
            return render(request, "base/task/task_index.html",
                          {"tasks": task_list, "taskcounts": task_count, "periodics": periodic_list,
                           "crontabs": crontab_list})
        elif request.method == 'POST':
            task_id = request.POST.get('id', '')
            if task_id:
                task = PeriodicTask.objects.filter(id=task_id)[0].task
                if 'run_plan' in task:
                    run_plan.delay()
                    return HttpResponse('用例执行中，请稍后查看报告即可,默认以 计划名称 + 时间戳命名.')
                elif 'delete_logs' in task:
                    delete_logs.delay()
                    return HttpResponse('用例执行中，稍后可在日志中查看执行记录.')
                elif 'stop_locust' in task:
                    stop_locust.delay()
                    return HttpResponse('用例执行中，稍后可在日志中查看执行记录.')
                else:
                    return HttpResponse('未定义该定时任务.{}--{}'.format(task_id, task))
            else:
                return HttpResponse('未定义该定时任务.{}'.format(task_id))


def task_logs(request):
    """
    定时任务运行日志
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/case/'
        return HttpResponseRedirect('/login/')
    else:
        superuser = User.objects.get(id=user_id).is_superuser
        if superuser:
            task_log_path = '/var/celery_logs/celery_worker_err.log'
            data_list = []
            with open(task_log_path, 'rb') as f:
                off = -1024 * 1024
                if f.tell() < -off:
                    data = f.readlines()
                else:
                    f.seek(off, 2)
                    data = f.readlines()
                for line in data:
                    data_list.append(line.decode())
                return render(request, 'base/task/log.html',
                              {'data': data_list, 'make': True, 'log_file': task_log_path})
        else:
            return render(request, 'base/task/log.html', {'data': '0', 'make': True, 'log_file': ''})


# 报告列表
@method_decorator(login_required, name='dispatch')
class ReportPage(ListView):
    model = Report
    template_name = 'base/report_page/report_page.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(ReportPage, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        self.plan_id = self.request.GET.dict().get('plan_id', '')
        user_id = self.request.session.get('user_id', '')
        if self.plan_id:
            return Report.objects.filter(plan_id=self.plan_id).order_by('-report_id')
        else:
            plan_list = []
            prj_list = is_superuser(user_id, type='list')
            plan = Plan.objects.filter(project_id__in=prj_list)
            for plan_ in plan:
                plan_list.append(plan_.plan_id)
            return Report.objects.filter(plan_id__in=plan_list).order_by('-report_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'plan_id': self.plan_id})
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def report_logs(request):
    """
    显示日志信息
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/report_page/'
        return HttpResponseRedirect('/login/')
    else:
        report_id = request.GET.get('report_id')
        try:
            report = Report.objects.get(report_id=report_id)
        except Report.DoesNotExist:
            return render(request, "base/report_page/log.html")
        else:
            report_content = eval(report.content.replace('Markup', ''))
            for case in report_content:
                global class_name
                class_name = case['class_name']
            superuser = User.objects.get(id=user_id).is_superuser
            if superuser:
                info = {"report": report, 'plan_id': report.plan_id, "report_content": report_content,
                        'class_name': class_name, 'is_superuser': superuser}
                return render(request, "base/report_page/log.html", info)
            else:
                info = {"report": report, 'plan_id': report.plan_id, "report_content": report_content,
                        'class_name': class_name, 'is_superuser': ''}
                return render(request, "base/report_page/log.html", info)


def report_index(request):
    """
    展示报告
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/report_index/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            report_id = request.GET.get('report_id', '')
            if not report_id:
                return render(request, "base/report.html")
            try:
                report = Report.objects.get(report_id=report_id)
            except Report.DoesNotExist:
                return render(request, 'base/report.html')
            plan_id = report.plan_id
            make = report.make
            case_num = report.case_num
            pass_num = report.pass_num
            fail_num = report.fail_num
            error_num = report.error_num
            report_content = eval(report.content.replace('Markup', ''))
            for case in report_content:
                global class_name
                class_name = case['class_name']
            info = {"report": report, 'plan_id': plan_id, 'case_num': case_num, "error_num": error_num,
                    'pass_num': pass_num, 'fail_num': fail_num, "report_content": report_content,
                    'img_name': str(now_time) + 'pie.png', 'class_name': class_name}
            if make:
                return render(request, "base/report_httprunner.html", info)
            else:
                return render(request, "base/report.html", info)


def report_search(request):
    """
    报告搜索
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        return HttpResponse('0')
    else:
        if request.method == 'POST':
            result = request.POST['result']
            report_id = request.POST['report_id']
            try:
                report = Report.objects.get(report_id=report_id)
            except Report.DoesNotExist:
                return render(request, "base/report.html")
            report_content = eval(report.content.replace('Markup', ''))
            if result not in ['pass', 'fail', 'error']:
                return HttpResponse(str(report_content))
            for case in report_content:
                global class_name
                class_name = case['class_name']
                step_list = case['step_list']
                case['step_list'] = []
                for step in step_list:
                    if result == step['result']:
                        case['step_list'].append(step)
                    else:
                        pass
            return HttpResponse(str(report_content))


def report_delete(request):
    """
    删除报告
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/report_page/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            report_id = request.GET['report_id']
            Report.objects.filter(report_id=report_id).delete()
            log.info('用户 {} 删除报告 {} 成功.'.format(user_id, report_id))
            return HttpResponseRedirect("base/report_page/")


def file_download(request):
    """
    下载HttpRunner报告
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/report_page/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            report_id = request.GET.get('report_id', '')
            if report_id:
                report = Report.objects.get(report_id=report_id)
                name = report.report_name[-19:]
                report_path = report.report_path
                if report_path:
                    file_name = report_path
                else:
                    report_path = os.path.join(os.getcwd(), 'reports')  # 拼接删除目录完整路径
                    file_name = os.path.join(report_path, name + '.html')
            else:
                file_name = request.GET.get("log_file", "")
            if not os.path.exists(file_name):
                log.info('文件：{} 无法下载！'.format(file_name))
                return render(request, "base/report_page/report_page.html",
                              {'error': '文件：{} 无法下载！'.format(file_name)})

            def file_iterator(file_name, chunk_size=512):
                with open(file_name, encoding='utf-8') as f:
                    while True:
                        c = f.read(chunk_size)
                        if c:
                            yield c
                        else:
                            break

            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            log.info('用户 {} 下载测试报告或日志文件：{} .'.format(user_id, file_name))
            return response


def performance_index(request):
    """
    locust页面
    :param request:
    :return:
    """
    if request.method == 'GET':
        user_id = request.session.get('user_id', '')
        if get_user(user_id):
            return render(request, 'base/performance/performance.html')
        else:
            request.session['login_from'] = '/base/performance/'
            return HttpResponseRedirect('/login/')


class StartLocust(threading.Thread):
    def __init__(self, make):
        threading.Thread.__init__(self)
        self.make = make

    def run(self):
        log.info(
            timezone.now().strftime('%Y-%m-%d %H:%M:%S') + " {} ==== StartLocust ========= {}".format(self.getName(),
                                                                                                      self.make))
        if self.make == 'master':
            p = os.base('/home/lixiaofeng/./locust_run.sh')
            log.info('====================p================={}'.format(p))
        elif self.make == 'slave':
            os.base('/home/lixiaofeng/./locust_slave_run.sh')
        elif self.make == 'stop':
            os.base('/home/lixiaofeng/./locust_stop.sh')


def start_locust(request):
    if request.method == 'GET':
        user_id = request.session.get('user_id', '')
        if get_user(user_id):
            make = request.GET.get('make')
            locust = StartLocust(make)
            locust.start()
            return HttpResponse('ok')
        else:
            request.session['login_from'] = '/base/performance/'
            return HttpResponseRedirect('/login/')


def performance_report(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/performance_report/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            import requests
            try:
                res = requests.get('http://www.easytest.xyz:8089/stats/requests')
                res = res.json()
                return render(request, 'base/performance/locust_report.html', {'info': res})
            except requests.exceptions.ConnectionError:
                locust_report = LocustReport.objects.all().order_by('-id')[:1]
                if locust_report:
                    for report in locust_report:
                        stats_list = eval(report.stats)
                        slave_list = eval(report.slaves)
                        return render(request, 'base/performance/locust_report.html',
                                      {'locust_report': locust_report, 'stats_list': stats_list,
                                       'slave_list': slave_list})
                else:
                    return render(request, 'base/performance/locust_report.html', {'error': '请先执行locust性能测试！'})
        return render(request, 'base/performance/locust_report.html', {'error': '额，数据丢失了呢！'})


def performance_real(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/performance_report/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            import requests
            try:
                res = requests.get('http://www.easytest.xyz:8089/stats/requests')
            except requests.exceptions.ConnectionError:
                return render(request, 'base/performance/locust_real.html', {'error': '未运行locust，无法获取实时数据！'})
            res = res.json()
            current_response_time_percentile_50 = res.get('current_response_time_percentile_50', '0.0')
            current_response_time_percentile_95 = res.get('current_response_time_percentile_95', '0.0')
            errors = res.get('errors', [])
            fail_ratio = res.get('fail_ratio', '0.0')
            slaves = res.get('slaves', [])
            state = res.get('state', '')
            stats = res.get('stats', [])
            total_rps = res.get('total_rps', '0.0')
            user_count = res.get('user_count', '1')
            username = User.objects.get(id=user_id).username
            locust_report = LocustReport(current_response_time_percentile_50=current_response_time_percentile_50,
                                         current_response_time_percentile_95=current_response_time_percentile_95,
                                         errors=errors, fail_ratio=fail_ratio, slaves=slaves, state=state, stats=stats,
                                         total_rps=total_rps, user_count=user_count, update_user=username)
            locust_report.save()
            log.info('用户 {} ，查看性能测试实时数据 并 写入到数据库中.'.format(user_id))
            return render(request, 'base/performance/locust_real.html', {'info': res})


def performance_history(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/performance_report/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            locust_report = LocustReport.objects.all().order_by('-id')
            stats_list = []
            for report in locust_report:
                stats = report.stats
                stats_list.append(eval(stats))
            log.info('用户 {} ，正在查看性能测试历史数据.'.format(user_id))
            return render(request, 'base/performance/locust_history.html', {'info': stats_list})


def performance_delete(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/performance_report/'
        return HttpResponseRedirect('/login/')
    else:
        if request.method == 'GET':
            LocustReport.objects.all().delete()
            log.info('用户 {} ，清空性能测试历史数据完成！'.format(user_id))
            return render(request, 'base/performance/locust_history.html')


# 用户列表
@method_decorator(login_required, name='dispatch')
class UserIndex(ListView):
    model = User
    template_name = 'base/user/user_index.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def dispatch(self, *args, **kwargs):
        return super(UserIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        return User.objects.all().order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get('paginator')
        page = context.get('page_obj')
        is_paginated = context.get('is_paginated')
        data = pagination_data(paginator, page, is_paginated)
        context.update(data)
        return context


def about_index(request):
    """
    关于我们
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if get_user(user_id):
        return render(request, 'base/about/about_us.html')

    else:
        request.session['login_from'] = '/base/about/'
        return HttpResponseRedirect('/login/')


def document(request):
    """
    关于我们
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/document_download/'
        return HttpResponseRedirect('/login/')
    else:
        document_dir = '/var/common/jenkins/workspace/EasyTest/media/'
        # document_dir = r'C:\Users\liyongfeng\Desktop\密钥'
        document_list = os.listdir(document_dir)
        file_list = []
        num = 0
        for doc in document_list:
            document_path = os.path.join(document_dir, doc)
            if os.path.isdir(document_path):
                path = os.path.join(document_dir, doc)
                media_path = os.path.join('http://www.easytest.xyz/media/', doc)
                path_list = os.listdir(path)
                path_list.sort()
                num += 1
                file_num = 0
                document_dict = {"id": num, "doc_name": doc, "file_dict": []}
                for file in path_list:
                    file_path = os.path.join(path, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        file_num += 1
                        file_dict = {"file_id": file_num, "file_name": file,
                                     "file_path": os.path.join(media_path, file),
                                     "file_size": str(size / 1024)[:4]}
                        document_dict["file_dict"].append(file_dict)
                file_list.append(document_dict)
                # log.info('-----------------------------{}'.format(file_list))
        return render(request, 'base/about/document_download.html', {"file_list": file_list})


def findata(request):
    """
    异步请求数据
    :param request:
    :return:
    """
    if request.method == 'GET':
        get_type = request.GET["type"]
        if get_type == "get_all_if_by_prj_id":
            prj_id = request.GET["prj_id"]
            # 返回字典列表
            if_list = Interface.objects.filter(project=prj_id).all().values()
            # list(if_list)将QuerySet转换成list
            return JsonResponse(list(if_list), safe=False)
        if get_type == "get_if_by_search_name":
            search_name = request.GET["search_name"]
            prj_id = request.GET["prj_id"]
            # 返回字典列表
            if_list = Interface.objects.filter(project=prj_id).filter(if_name__contains=search_name).all().values()
            # list(if_list)将QuerySet转换成list
            return JsonResponse(list(if_list), safe=False)
        if get_type == "get_if_by_if_id":
            if_id = request.GET["if_id"]
            try:
                # 查询并将结果转换为json
                interface = Interface.objects.filter(if_id=if_id).values()
                return JsonResponse(list(interface), safe=False)
            except ValueError:
                return HttpResponse('no')
        if get_type == "get_env_by_prj_id":
            prj_id = request.GET["prj_id"]
            # 查询并将结果转换为json
            env = Environment.objects.filter(project_id=prj_id).values()
            return JsonResponse(list(env), safe=False)
        if get_type == "get_case_by_case_id":  # 增加 get_case_by_case_id 类型，编辑 用例 使用
            case_id = request.GET["case_id"]
            # 查询并将结果转换为json
            case = Case.objects.filter(case_id=case_id).values()
            return JsonResponse(list(case), safe=False)
        if get_type == "get_all_case_by_prj_id":
            prj_id = request.GET["prj_id"]
            try:
                # 查询并将结果转换为json
                case = Case.objects.filter(project_id=prj_id).values()
                return JsonResponse(list(case), safe=False)
            except ValueError:
                return HttpResponse('no')
        if get_type == 'get_log':
            log_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) + '/logs'
            log_file_list = os.listdir(log_path)
            file_list = []
            data_list = []
            now = time.strftime('%Y-%m-%d')
            for file in log_file_list:
                if 'all' in file and now in file:
                    file_list.append(file)
            if not file_list:
                yesterday = datetime.today() + timedelta(-1)
                yesterday_format = yesterday.strftime('%Y-%m-%d')
                for file in log_file_list:
                    if 'all' in file and yesterday_format in file:
                        file_list.append(file)
            try:
                file_list.sort()
                log_file = os.path.join(log_path, file_list[0])
            except IndexError:
                for file in log_file_list:
                    if 'all' in file:
                        file_list.append(file)
                file_list.sort()
                log_file = os.path.join(log_path, file_list[-1])
            with open(log_file, 'r', encoding='utf-8') as f:
                off = -1024 * 1024
                if f.tell() < -off:
                    data = f.readlines()
                else:
                    f.seek(off, 2)
                    data = f.readlines()
            for i in data:
                data_list.append(i.replace('True', 'true').replace('False', 'false').replace('None', 'null'))
            log.info('get_log 查询日志文件名称 ===========================>>> {}'.format(log_file))
            return JsonResponse(data_list, safe=False)
        if get_type == 'get_task_log':
            task_log_path = '/var/celery_logs/celery_worker_err.log'
            data_list = []
            with open(task_log_path, 'r', encoding='utf-8') as f:
                off = -1024 * 1024
                if f.tell() < -off:
                    data = f.readlines()
                else:
                    f.seek(off, 2)
                    data = f.readlines()
            for i in data:
                data_list.append(i.replace('True', 'true').replace('False', 'false').replace('None', 'null'))
            return JsonResponse(data_list, safe=False)
    elif request.method == 'POST':
        get_type = request.POST.get("type", '')
        if get_type == 'analysis_request_header_json':
            request_header_json = request.POST.get('request_header_json', '')
            try:
                data = eval(
                    request_header_json.replace('false', 'False').replace('null', 'None').replace('true', 'True'))
                return JsonResponse(list(data), safe=False)
            except Exception as e:
                log.error('解析参数错误. {}'.format(e))
                return HttpResponse('no')


# ----------------------------------------------------------------------------------------------------------------------



num_list = []


# appid = 'wx506830910cbd77e9'
# appsecret = 'e0e5d5ed1d507103f73d6667eef00d7a' pages/index/detail/index?id=365&campId=12&index=1

@login_required
def index(request):
    """
    首页展示数据
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')  # 从session中获取user_id
    if not user_id:
        return HttpResponseRedirect('/login/')
    if request.method == 'POST':
        if get_user(user_id):
            url = request.POST.get('url', '')
            path = request.POST.get('path', '')
            appid = request.POST.get('appid', '')
            appsecret = request.POST.get('appsecret', '')
            if appid != '' and appsecret != '':
                if path == '':
                    path = '?from=1'
                url = {'path': path}
                qr_code_name = getACodeImage(appid, appsecret, url)
                if not qr_code_name:
                    log.info('用户 {} 生成小程序码 失败！appid、appsecret错误，未返回正确的token！')
                    return HttpResponse('2')
                else:
                    log.info('用户 {} 生成小程序码 {}-->{}'.format(user_id, qr_code_name, url))
                    return JsonResponse(str(qr_code_name), safe=False)
            elif url != '':
                qr_code_name = gr_code(url)
                log.info('用户 {} 生成二维码 {}-->{}'.format(user_id, qr_code_name, url))
                return JsonResponse(str(qr_code_name), safe=False)
            else:
                return HttpResponse('1')
        else:
            return HttpResponse('0')
    elif request.method == 'GET':
        plan_list = []
        prj_list = is_superuser(user_id, type='list')
        plan = Plan.objects.filter(project_id__in=prj_list)
        for plan_ in plan:
            plan_list.append(plan_.plan_id)
        superuser = User.objects.get(id=user_id).is_superuser
        if superuser:
            project_num = Project.objects.aggregate(Count('prj_id'))['prj_id__count']
        else:
            project_num = Project.objects.filter(user_id=user_id).aggregate(Count('prj_id'))['prj_id__count']
        env_num = Environment.objects.filter(project_id__in=prj_list).aggregate(Count('env_id'))['env_id__count']
        interface_num = Interface.objects.filter(project_id__in=prj_list).aggregate(Count('if_id'))['if_id__count']
        case_num = Case.objects.filter(project_id__in=prj_list).aggregate(Count('case_id'))['case_id__count']
        plan_num = Plan.objects.filter(project_id__in=prj_list).aggregate(Count('plan_id'))['plan_id__count']
        sign_num = Sign.objects.aggregate(Count('sign_id'))['sign_id__count']
        report_num = Report.objects.filter(plan_id__in=plan_list).aggregate(Count('report_id'))['report_id__count']
        periodic_num = PeriodicTask.objects.aggregate(Count('id'))['id__count']
        crontabSchedule_num = CrontabSchedule.objects.aggregate(Count('id'))['id__count']
        user_num = User.objects.aggregate(Count('id'))['id__count']

        total = get_total_values(user_id)

        if 'HTTP_X_FORWARDED_FOR' in request.META:  # 在线人数
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']
        online_ips = cache.get("online_ips", [])
        if online_ips:
            online_ips = list(cache.get_many(online_ips).keys())
        cache.set(ip, 0, 5 * 60)
        if ip not in online_ips:
            online_ips.append(ip)
        cache.set("online_ips", online_ips)
        log.info('同时在线人员：{}'.format(cache.get("online_ips", [])))

        info = {'project_num': project_num,
                'env_num': env_num, 'interface_num': interface_num, 'case_num': case_num,
                'plan_num': plan_num, 'total': total,
                'sign_num': sign_num, 'report_num': report_num, "online_ips": len(cache.get("online_ips", [])),
                'task_num': periodic_num + crontabSchedule_num, 'user_num': user_num}

        return render(request, "base/index.html", info)


@login_required
def index_data(request):
    """
    切换首页展示数据
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')  # 从session中获取user_id
    if not user_id:
        return HttpResponseRedirect('/login/')
    elif request.method == 'GET':
        off = request.GET.get('off', '')
        plan_list = []
        prj_list = is_superuser(user_id, type='list', off=off)
        plan = Plan.objects.filter(project_id__in=prj_list)
        for plan_ in plan:
            plan_list.append(plan_.plan_id)
        if off == '1':
            project_num = Project.objects.aggregate(Count('prj_id'))['prj_id__count']
        else:
            project_num = Project.objects.filter(user_id=user_id).aggregate(Count('prj_id'))['prj_id__count']
        env_num = Environment.objects.filter(project_id__in=prj_list).aggregate(Count('env_id'))['env_id__count']
        interface_num = Interface.objects.filter(project_id__in=prj_list).aggregate(Count('if_id'))['if_id__count']
        case_num = Case.objects.filter(project_id__in=prj_list).aggregate(Count('case_id'))['case_id__count']
        plan_num = Plan.objects.filter(project_id__in=prj_list).aggregate(Count('plan_id'))['plan_id__count']
        sign_num = Sign.objects.aggregate(Count('sign_id'))['sign_id__count']
        report_num = Report.objects.filter(plan_id__in=plan_list).aggregate(Count('report_id'))['report_id__count']
        periodic_num = PeriodicTask.objects.aggregate(Count('id'))['id__count']
        crontabSchedule_num = CrontabSchedule.objects.aggregate(Count('id'))['id__count']
        user_num = User.objects.aggregate(Count('id'))['id__count']

        info = {'project_num': project_num, 'env_num': env_num, 'interface_num': interface_num, 'case_num': case_num,
                'plan_num': plan_num, 'sign_num': sign_num, 'report_num': report_num,
                'task_num': periodic_num + crontabSchedule_num, 'user_num': user_num}

        return JsonResponse(info)


def change_password(request):
    """
    修改密码
    :param request:
    :return:
    """
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')

        msg = change_info_logic(new_password)
        if msg != 'ok':
            log.error('change password error：{}'.format(msg))
            return JsonResponse({'msg': msg})
        else:
            user_id = request.session.get('user_id', '')
            if not user_id:
                return HttpResponseRedirect('/login/')
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            log.info('用户：{} 修改密码为 {}'.format(user_id, new_password))
            return JsonResponse({'msg': 'success'})


def img_download(request):
    """
    二维码下载
    :param request:
    :return:
    """
    user_id = request.session.get('user_id', '')  # 从session中获取user_id
    if get_user(user_id):
        if request.method == 'GET':
            name = request.GET.get('log_file', '')
            name_path = os.path.join(settings.MEDIA_ROOT, name)

            def file_iterator(file_name, chunk_size=512):
                with open(file_name, 'rb') as f:
                    while True:
                        c = f.read(chunk_size)
                        if c:
                            yield c
                        else:
                            break

            response = StreamingHttpResponse(file_iterator(name_path))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(name_path)
            log.info('用户 {} 下载的二维码：{}'.format(user_id, 'http://39.105.136.231/media/{}'.format(name)))
            return response
    else:
        request.session['login_from'] = '/index/'
        return HttpResponseRedirect('/login/')
