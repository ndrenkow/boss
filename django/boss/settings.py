"""
Django settings for boss project.

Generated by 'django-admin startproject' using Django 1.8.7.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

USE_LOCAL = os.environ.get('USING_DJANGO_TESTRUNNER') is not None
if not USE_LOCAL:
    # Vault connection setup
    import bossutils

    vault = bossutils.vault.Vault()
    config = bossutils.configuration.BossConfig()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
if not USE_LOCAL:
    SECRET_KEY = vault.read('secret/endpoint/django', 'secret_key')
else:
    SECRET_KEY = 'cki+nch2)9b_xatlg1n-!(db07ctl#*qh8j-jr)0h!0+c0nbkr'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'bosscore',
    'bossspatialdb',
    'rest_framework_swagger',
    'guardian'
]

# Add django_jenkins if running on a Jenkins server.
if USE_LOCAL:
    INSTALLED_APPS.insert(0, 'django_jenkins')

# Calculate test coverage for apps listed here.
PROJECT_APPS = [
    'bosscore',
    'bossspatialdb',
]

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pylint',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'boss.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'boss.wsgi.application'

if USE_LOCAL:
    db_default_name = 'microns'
    db_default_user = 'root'
    db_default_password = 'MICrONS'
    db_default_host = '127.0.0.1'
    db_default_port = 3306
else:
    db_default_name = vault.read('secret/endpoint/django/db', 'name')
    db_default_user = vault.read('secret/endpoint/django/db', 'user')
    db_default_password = vault.read('secret/endpoint/django/db', 'password')
    db_default_host = config['aws']['db']
    db_default_port = vault.read('secret/endpoint/django/db', 'port')


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

USE_SQLITE = os.environ.get('USE_SQLITE') is not None
if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(str(Path(__file__).parents[2]), 'testdb.db'),
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }
else:
    # Using Amazon RDS
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': db_default_name,
            'USER': db_default_user,
            'PASSWORD': db_default_password,
            'HOST': db_default_host,
            'PORT': db_default_port,

        }
    }


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/static/'

if not USE_LOCAL:
    # Setup the AWS manager for boto3 session pooling as Vault issued AWS creds
    from bossutils.aws import *
    aws_mngr = get_aws_manager()

ANONYMOUS_USER_NAME = None
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend', # this is default
    'guardian.backends.ObjectPermissionBackend',
]

if not USE_LOCAL:
    # Restrict djangooidc so it is not used during unit tests
    INSTALLED_APPS.append("djangooidc")
    AUTHENTICATION_BACKENDS.insert(1, 'djangooidc.backends.OpenIdConnectBackend')

    # bypass the djangooidc provided page and go directly to the keycloak page
    LOGIN_URL = "/openid/openid/KeyCloak"

    OIDC_DEFAULT_BEHAVIOUR = {
        'response_type': 'code',
        'scope': ['openid', 'profile', 'email'],
    }

    public_uri = vault.read('secret/endpoint/auth', 'public_uri')
    OIDC_PROVIDERS = {
        'KeyCloak': {
            'srv_discovery_url': vault.read('secret/endpoint/auth', 'url'),
            'behaviour': OIDC_DEFAULT_BEHAVIOUR,
            'client_registration': {
                'client_id': vault.read('secret/endpoint/auth', 'client_id'),
                'redirect_uris': [public_uri + '/openid/callback/login/'],
                'post_logout_redirect_uris': [public_uri + '/openid/callback/logout/'],
            },
        }
    }

# Django rest framework versioning  and permission requirements
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        #'rest_framework.permissions.DjangoModelPermissions'
    )

}
# Version that unit tests are being run against
BOSS_VERSION = 'v0.3'

