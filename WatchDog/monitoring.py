#!/usr/bin/env python
# coding:utf-8

#do not forget to start jupyter server instead of jupyter lab with param --config=/path/config*.py

from os import getcwd as osGetcwd, mkdir as osMkdir
from os.path import exists as osPathExists, join as osPathJoin
from time import sleep
from requests import post as requestPost, get as requestGet, Session as requestsSession
from requests.exceptions import ConnectionError as requestsExceptionsConnectionError
from flask import Flask, render_template, redirect

# for jupyter server doc convert
from nbconvert import HTMLExporter
from nbformat import from_dict as nbformatFrom_dict
html_exporter = HTMLExporter()

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.Helpers.os_helpers import launch_JUPYTER_server
from trading.TeleRemote.tele_trading import start_arbitre


APP_NAME = "monitoring"
PARENT_DIR = "WatchDog"

web_template_folder = osPathJoin(osGetcwd(), "common", PARENT_DIR, "templates")
web_static_folder = osPathJoin(osGetcwd(), "common", PARENT_DIR, "static")
app = Flask(APP_NAME, template_folder=web_template_folder, static_folder=web_static_folder)
config = Config(name=APP_NAME)



##############################################################################################################################################################################################
# main applications

# arbitre
@app.route('/arbitre', methods=['GET', 'POST'])
def receive_template():
    html_default_file = "default_arbitre.html"
    name = "arbitre" ; html_file = "{0}.html".format(name)
    try: 
        response = requestPost('http://{0}:{1}/get-template'.format(config.parser[name.upper()]["{0}_SERVER".format(name.upper())], config.parser[name.upper()]["{0}_PORT".format(name.upper())]))
    except requestsExceptionsConnectionError:
        return render_template(html_default_file, username="to monitoring")
    doesTemplateExist(html_file=html_file, template_string=response.text)
    return render_template(html_file, username="to monitoring")

@app.route('/start_arbitre', methods=['GET', 'POST'])
def run_arbitre():
    name = "arbitre"
    _ = start_arbitre()
    nb_retry = 0
    while nb_retry < 15:
        try:
            response = requestPost('http://{0}:{1}/get-template'.format(config.parser[name.upper()]["{0}_SERVER".format(name.upper())],config.  parser[name.upper()]["{0}_PORT".format(name.upper())]))
            break
        except:
            pass
        sleep(1)
        nb_retry+=1
    return redirect('/arbitre')


##############################################################################################################################################################################################
# Jupyter

JP_BASEURL = "http://127.0.0.1:8888/api/contents"
JP_token = '?token=5ee52cce8fe5b31f1e329650f51f55546dd64f83aece933e'

def jupyterAutoLogin():
    def wrapJupyterAutoLogin(f):
        global JP_session 
        if JP_session == None: 
            global _xsrf 
            login_url = "{0}/api/login".format(JP_BASEURL)
            JP_session = requestsSession() 
            response = JP_session.post(url=login_url, data={'username': 'webdev', 
                                                            'password': '@Toto.con123@Jup'})        
        def wrappedJupyterAutoLogin(*args, **kwargs):
            return f(*args, **kwargs)
        return wrappedJupyterAutoLogin
    return wrapJupyterAutoLogin

def jupyterTry(redirect_from):
    def wrapJupyterTry(f):
        def wrappedJupyterTry(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except requestsExceptionsConnectionError:
                return start_jupyter(redirect_from=redirect_from)
        return wrappedJupyterTry
    return wrapJupyterTry


@app.route('/MonteCarlo', methods=['GET', 'POST'])
@jupyterTry('/MonteCarlo')
def JP_MonteCarlo():
    name = "MonteCarlo" ; html_file = "{0}.html".format(name)
    response = requestGet('{0}/finished/MonteCarlo.ipynb{1}'.format(JP_BASEURL, JP_token))
    notebook = nbformatFrom_dict(response.json())
    (body, resources) = html_exporter.from_notebook_node(notebook['content'])
    doesTemplateExist(html_file=html_file, template_string=body)
    return render_template(html_file, username="to monitoring")

def start_jupyter(redirect_from):
    _ = launch_JUPYTER_server(jp_env=config.JP_ENV, jp_server=config.JP_SERVER, jp_port=config.JP_PORT)
    nb_retry = 0
    while nb_retry < 15:
        try:
            response = requestPost('http://{0}:{1}'.format(config.JP_SERVER,config.JP_PORT))
            break
        except:
            pass
        sleep(1)
        nb_retry+=1
    return redirect(redirect_from)


##############################################################################################################################################################################################
# Django

DJ_BASEURL = "https://vps688741.ovh"
#DJ_BASEURL = "http://127.0.0.1:8000"
DJ_session = None
csrf_token = None

def djangoAutoLogin(DJ_url):
    def wrapDjangoAutoLogin(f):
        global DJ_session 
        if DJ_session == None: 
            global csrf_token 
            login_url="{0}/accounts/login/?next='{1}'".format(DJ_BASEURL, DJ_url) ; userName= :)  ; passWord=  :)
            DJ_session = requestsSession()
            try:      
                response = DJ_session.get(url=login_url)
                csrf_token = response.cookies.get('csrftoken')
                DJ_session.headers['Referer'] = login_url
                DJ_session.headers['X-CSRFToken'] = csrf_token
                login_data = {'username': userName, 'password': passWord, 'csrfmiddlewaretoken': csrf_token,}
                response = DJ_session.post(login_url, data=login_data)
            except:
                # no internet
                pass      
        def wrappedDjangoAutoLogin(*args, **kwargs):
            return f(*args, **kwargs)
        return wrappedDjangoAutoLogin
    return wrapDjangoAutoLogin

@app.route('/test')
@djangoAutoLogin(DJ_url='{0}/HireMe/'.format(DJ_BASEURL))
def test():
    name = "HireMe" ; html_file = "{0}.html".format(name)
    html_page = DJ_session.get('{0}/hireMe/'.format(DJ_BASEURL))
    doesTemplateExist(html_file=html_file, template_string=html_page)
    return render_template(html_file, username="to monitoring")

@app.route('/logout')
def logout():
    _ = DJ_session.get('{0}/account/logout/'.format(DJ_BASEURL))
    return redirect('/')


##############################################################################################################################################################################################
# Main

def doesTemplateExist(html_file, template_string):
    if not osPathExists(web_template_folder):
        osMkdir("templates")
    with open(osPathJoin(web_template_folder, html_file), 'w') as template:
        template.writelines("{% extends 'base.html' %}\n")
        template.writelines("{% block mycontent %}\n")
        template.writelines(template_string)
        template.writelines("\n{% endblock mycontent %}")

#web app
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('base.html', username="to monitoring")

@app.route('/redirect_main', methods=['GET', 'POST'])
def redirect_main():
    redirect('/')

def run_monitoring():
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run()
    return app



#================================================================
if __name__ == "__main__":
    current_app = run_monitoring()
