from django.shortcuts import render
from common.execute import get_user, is_superuser
from .models import Api
from base.models import Project
from common.common import insert_mock_data, update_mock_data
from common.response import VALID, INVALID, EMPTY, NUMBER
from common.validator import domain_server
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
import json, re, logging

log = logging.getLogger('log')  # 初始化log


def mock_api(request):
    user_id = request.session.get('user_id', '')
    if not get_user(user_id):
        request.session['login_from'] = '/base/plan/'
        HttpResponseRedirect('/login/')
    else:
        patt = re.compile('\d+')
        if request.method == 'POST':
            data = eval(request.body.decode('utf-8'))
            msg = insert_mock_data(**data)
            msg = json.dumps(msg)
            return HttpResponse(msg)
        elif request.method == "DELETE":
            id = patt.findall(request.get_full_path())[0]
            Api.objects.filter(id=int(id)).delete()
            msg = json.dumps(VALID)
            return HttpResponse(msg)
        elif request.method == 'PUT':
            id = patt.findall(request.get_full_path())[0]
            data = eval(request.body.decode('utf-8'))
            msg = update_mock_data(id, **json.loads(data))
            msg = json.dumps(msg)
            return HttpResponse(msg)
        else:
            prj_list = is_superuser(user_id)
            api_name = request.GET.get('api_name', '')
            if api_name:
                api_info = Api.objects.filter(name__contains=api_name)
            else:
                api_info = Api.objects.all()
            api_list = []
            for api in api_info:
                if api in api_list:
                    pass
                else:
                    api_list.append(api.project_id)
            api_prj_list = Project.objects.filter(prj_id__in=api_list)
            info = {
                'prj_list': prj_list,
                'api_info': api_info,
                'api_prj_list': api_prj_list
            }
            return render(request, 'mocks/index.html', info)


def dispatch_request(request):
    """
    mock view logic
    :param path: request url for mock server
    :return: response msg that use default or custom defined
    """
    m = Api.objects.filter(url=request.path.replace('/mocks', '')).filter(method=request.method)
    if not m:
        EMPTY['msg'] = EMPTY['msg'].format(url=request.path, method=request.method)
        return HttpResponse(json.dumps(EMPTY))
    if len(m) > 1:
        NUMBER['msg'] = NUMBER['msg'].format(url=request.path, method=request.method)
        return HttpResponse(json.dumps(NUMBER))
    body = json.loads(m[0].body)
    log.info('请求mock接口：{},{}'.format(request.path, request.method))
    return HttpResponse(domain_server(request, **body))
