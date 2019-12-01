"""
Django settings for DjangoBlog project.

Generated by 'django-admin startproject' using Django 1.10.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""
import sys
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'n9ceqv38)#&mwuat@(mjb_p%em$e8$qyr#fw9ot!=ba6lijx-6'

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
DEBUG = False
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

# ALLOWED_HOSTS = []
ALLOWED_HOSTS = ['*', '127.0.0.1', '39.105.136.231', 'example.com']
# Application definition


SITE_ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.abspath(os.path.join(SITE_ROOT, '../'))

INSTALLED_APPS = [
    # 'django.contrib.admin',
    'simpleui',
    # 'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'mdeditor',
    'haystack',
    'blog',
    'accounts',
    'comments',
    'oauth',
    'servermanager',
    'owntracks',
    'compressor',

    'base',
    'guest',
    'mocks',
    'djcelery',
    'bootstrap3'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'blog.middleware.OnlineMiddleware'
]

ROOT_URLCONF = 'DjangoBlog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blog.context_processors.seo_processor'
            ],
        },
    },
]

WSGI_APPLICATION = 'DjangoBlog.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'blog',
        # 'USER': os.environ.get('DJANGO_MYSQL_USER'),
        'USER': "blog",
        # 'PASSWORD': os.environ.get('DJANGO_MYSQL_PASSWORD'),
        'PASSWORD': "123456",
        # 'HOST': os.environ.get('DJANGO_MYSQL_HOST'),
        'HOST': "127.0.0.1",
        'PORT': 3306,
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/


HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'DjangoBlog.whoosh_cn_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
    },
}
# Automatically update searching index
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
# Allow user login with username and password
AUTHENTICATION_BACKENDS = ['accounts.user_login_backend.EmailOrUsernameModelBackend']

# STATIC_ROOT = os.path.join(SITE_ROOT, 'collectedstatic')
STATIC_ROOT = '/www/static/static/'

STATIC_URL = '/static/'
STATICFILES = os.path.join(BASE_DIR, 'static')

AUTH_USER_MODEL = 'accounts.BlogUser'
LOGIN_URL = '/login/'

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_TIME_FORMAT = '%Y-%m-%d'

# bootstrap color styles
BOOTSTRAP_COLOR_TYPES = [
    'default', 'primary', 'success', 'info', 'warning', 'danger'
]

# paginate
PAGINATE_BY = 10
# http cache timeout
CACHE_CONTROL_MAX_AGE = 2592000
# cache setting  使用Memcached缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'KEY_PREFIX': 'django_test' if TESTING else 'djangoblog',
        'TIMEOUT': 60 * 60 * 10
    },
    'locmemcache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 10800,
        'LOCATION': 'unique-snowflake',
    }
}

SITE_ID = 1
BAIDU_NOTIFY_URL = "http://data.zz.baidu.com/urls?site=https://www.lylinux.net&token=1uAOGrMsUm5syDGn"

# Emial:
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# EMAIL_USE_TLS = True
EMAIL_USE_SSL = True

EMAIL_HOST = 'smtp.qq.com'
EMAIL_PORT = 465
# EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_USER')
EMAIL_HOST_USER = "954274592@qq.com"
# EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_PASSWORD')
EMAIL_HOST_PASSWORD = "hlymvkoqcukvbdif"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
# SERVER_EMAIL = os.environ.get('DJANGO_EMAIL_USER')
SERVER_EMAIL = "lixiaofeng"
# Setting debug=false did NOT handle except email notifications
ADMINS = [('admin', 'admin@admin.com')]
# WX ADMIN password(Two times md5)
WXADMIN = '995F03AC401D6CABABAEF756FC4D43C7'

# log
import time

cur_path = os.path.dirname(os.path.realpath(__file__))  # log_path是存放日志的路径
log_path = os.path.join(os.path.dirname(cur_path), 'logs')
if not os.path.exists(log_path): os.mkdir(log_path)  # 如果不存在这个logs文件夹，就自动创建一个

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        # 日志格式
        'standard': {
            'format': '[%(asctime)s] [%(filename)s:%(lineno)d] [%(module)s:%(funcName)s] '
                      '[%(levelname)s]- %(message)s'},
        'simple': {  # 简单格式
            'format': '%(levelname)s %(message)s'
        },
    },
    # 过滤
    'filters': {
    },
    # 定义具体处理日志的方式
    'handlers': {
        # 默认记录所有日志
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'all-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码
        },
        # 输出错误日志
        'error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'error-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码
        },
        # 控制台输出
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        # 输出info日志
        'info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'info-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',  # 设置默认编码
        },
    },
    # 配置用哪几种 handlers 来处理日志
    'loggers': {
        # 类型 为 django 处理所有类型的日志， 默认调用
        'django': {
            'handlers': ['default', 'console'],
            'level': 'INFO',
            'propagate': False
        },
        # log 调用时需要当作参数传入
        'log': {
            'handlers': ['error', 'info', 'console', 'default'],
            'level': 'INFO',
            'propagate': True
        },
    }
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other
    'compressor.finders.CompressorFinder',
)
COMPRESS_ENABLED = True
# COMPRESS_OFFLINE = True


COMPRESS_CSS_FILTERS = [
    # creates absolute urls from relative ones
    'compressor.filters.css_default.CssAbsoluteFilter',
    # css minimizer
    'compressor.filters.cssmin.CSSMinFilter'
]
COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.JSMinFilter'
]

MEDIA_ROOT = os.path.join(SITE_ROOT, 'media')
if not os.path.exists(MEDIA_ROOT):
    os.mkdir(MEDIA_ROOT)
MEDIA_URL = '/media/'

# 定时任务
# import djcelery
#
# djcelery.setup_loader()
# BROKER_URL = 'redis://127.0.0.1:6379/0'
# # broker_pool_limit=None
# # BROKER_POOL_LIMIT=None
# CELERY_IMPORTS = ('base.tasks')
# CELERY_TIMEZONE = 'Asia/Shanghai'
# CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
# CELERY_ENABLE_UTC = False
# DJANGO_CELERY_BEAT_TZ_AWARE = False

# simpleui 设置
SIMPLEUI_STATIC_OFFLINE = True  # 访问静态文件
# SIMPLEUI_HOME_PAGE = 'http://39.105.136.231'
# SIMPLEUI_HOME_TITLE = 'EasyTest-后台管理'
SIMPLEUI_HOME_ICON = 'fa fa-user'

SIMPLEUI_CONFIG = {
    'system_keep': False,
    'menus': [
        {
            'app': ' accounts',
            'name': '账户管理',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': '用户',
                # 'icon': 'fa fa-user',
                'url': 'accounts/bloguser/'
            }]
        },
        {
            'app': ' base',
            'name': '测试平台',
            # 'icon': 'fas fa-user-shield',
            'models': [
                {
                    'name': '项目管理',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/project/'
                },
                {
                    'name': '测试环境',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/environment/'
                },
                {
                    'name': '接口管理',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/interface/'
                },
                {
                    'name': '测试用例',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/case/'
                },
                {
                    'name': '测试计划',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/plan/'
                },
                {
                    'name': '签名管理',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/sign/'
                },
                {
                    'name': '测试报告',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/report/'
                }, {
                    'name': '发布会',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/event/'
                }, {
                    'name': '发布会嘉宾',
                    # 'icon': 'fa fa-product-hunt fa-fw',
                    'url': 'base/guest/'
                },
            ]
        },
        {
            'app': ' blog',
            'name': '博客管理',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': '侧边栏',
                # 'icon': 'fa fa-user',
                'url': 'blog/sidebar/'
            }, {
                'name': '分类',
                # 'icon': 'fa fa-user',
                'url': 'blog/category/'
            }, {
                'name': '友情链接',
                # 'icon': 'fa fa-user',
                'url': 'blog/links/'
            }, {
                'name': '文章管理',
                # 'icon': 'fa fa-user',
                'url': 'blog/article/'
            }, {
                'name': '标签管理',
                # 'icon': 'fa fa-user',
                'url': 'blog/tag/'
            }, {
                'name': '网站配置',
                # 'icon': 'fa fa-user',
                'url': 'blog/blogsettings/'
            },
            ]
        },
        {
            'app': 'comments',
            'name': '评论管理',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': '评论管理',
                # 'icon': 'fa fa-user',
                'url': 'comments/comment/'
            }]
        },
        # {
        #     'app': 'djcelery',
        #     'name': '定时任务',
        #     'icon': 'fas fa-user-shield',
        #     'models': [{
        #         'name': 'Crontabs',
        #         'icon': 'fa fa-user',
        #         'url': 'djcelery/crontabschedule/'
        #     }, {
        #         'name': 'Intervals',
        #         'icon': 'fa fa-user',
        #         'url': 'djcelery/intervalschedule/'
        #     }, {
        #         'name': 'Periodic tasks',
        #         'icon': 'fa fa-user',
        #         'url': 'djcelery/periodictask/'
        #     }, {
        #         'name': ' Periodic taskss',
        #         'icon': 'fa fa-user',
        #         'url': 'djcelery/periodictasks/'
        #     }, {
        #         'name': 'Workers',
        #         'icon': 'fa fa-user',
        #         'url': 'djcelery/workerstate/'
        #     },
        #     ]
        # },
        {
            'app': ' oauth',
            'name': 'oauth配置',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': 'Oauth用户',
                # 'icon': 'fa fa-user',
                'url': 'oauth/oauthuser/'
            }, {
                'name': 'Oauth配置',
                # 'icon': 'fa fa-user',
                'url': 'oauth/oauthconfig/'
            },
            ]
        },
        {
            'app': ' owntracks',
            'name': 'Owntracks',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': 'OwnTrackLogs',
                # 'icon': 'fa fa-user',
                'url': 'owntracks/owntracklog/'
            }]
        },
        {
            'app': ' servermanager',
            'name': '服务器管理',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': ' 命令',
                # 'icon': 'fa fa-user',
                'url': 'servermanager/commands/'
            }, {
                'name': ' 邮件发送log',
                # 'icon': 'fa fa-user',
                'url': 'servermanager/emailsendlog/'
            },
            ]
        },
        {
            'app': 'sites',
            'name': '站点管理',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': '站点管理',
                # 'icon': 'fa fa-user',
                'url': 'sites/site/'
            }]
        },
        {
            'app': 'admin',
            'name': '日志管理',
            # 'icon': 'fas fa-user-shield',
            'models': [{
                'name': '日志管理',
                # 'icon': 'fa fa-user',
                'url': 'admin/logentry/'
            }]
        },
    ]
}
