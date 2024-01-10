#!/usr/bin/env python
# coding:utf-8

from threading import Thread
from multiprocessing import Process

# relative import
from sys import path;path.extend("..")
from common.config import Config
from common.MyLogger.my_logger import MyLogger
from common.Database.database import Database
from common.ThreadQs.thread_Qs import StarQs, SubsQ
from common.Helpers.helpers import getUnusedPort

from common.FlaskNode.flask_funcs import create_app

#Builtin Configuration Values

#DEBUG
#Whether debug mode is enabled. 
#When using flask run to start the development server, an interactive debugger will be shown for unhandled exceptions, 
#and the server will be reloaded when code changes. The debug attribute maps to this config key. 
#This is set with the FLASK_DEBUG environment variable. It may not behave as expected if set in code
#Do not enable debug mode when deploying in production.
#Default: False

#TESTING
#Enable testing mode. 
#Exceptions are propagated rather than handled by the the app’s error handlers. 
#Extensions may also change their behavior to facilitate easier testing. You should enable this in your own tests.
#Default: False

#PROPAGATE_EXCEPTIONS
#Exceptions are re-raised rather than being handled by the app’s error handlers. 
#If not set, this is implicitly true if TESTING or DEBUG is enabled.
#Default: None

#TRAP_HTTP_EXCEPTIONS
#If there is no handler for an HTTPException-type exception, re-raise it to be handled by the interactive debugger 
#instead of returning it as a simple error response.
#Default: False

#TRAP_BAD_REQUEST_ERRORS
#Trying to access a key that doesn’t exist from request dicts like args and form will return a 400 Bad Request error page. 
#Enable this to treat the error as an unhandled exception instead so that you get the interactive debugger. 
#This is a more specific version of TRAP_HTTP_EXCEPTIONS. If unset, it is enabled in debug mode.
#Default: None

#SECRET_KEY
#A secret key that will be used for securely signing the session cookie and 
#can be used for any other security related needs by extensions or your application. 
#It should be a long random bytes or str. For example, copy the output of this to your config:
#$ python -c 'import secrets; print(secrets.token_hex())'
#'192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf'
#Do not reveal the secret key when posting questions or committing code.
#Default: None

#SESSION_COOKIE_NAME
#The name of the session cookie. Can be changed in case you already have a cookie with the same name.
#Default: 'session'

#SESSION_COOKIE_DOMAIN
#The domain match rule that the session cookie will be valid for. 
#If not set, the cookie will be valid for all subdomains of SERVER_NAME. 
#If False, the cookie’s domain will not be set.
#Default: None

#SESSION_COOKIE_PATH
#The path that the session cookie will be valid for. 
#If not set, the cookie will be valid underneath APPLICATION_ROOT or / if that is not set.
#Default: None

#SESSION_COOKIE_HTTPONLY
#Browsers will not allow JavaScript access to cookies marked as “HTTP only” for security.
#Default: True

#SESSION_COOKIE_SECURE
#Browsers will only send cookies with requests over HTTPS if the cookie is marked “secure”. 
#The application must be served over HTTPS for this to make sense.
#Default: False

#SESSION_COOKIE_SAMESITE
#Restrict how cookies are sent with requests from external sites. 
#Can be set to 'Lax' (recommended) or 'Strict'. See Set-Cookie options.
#Default: None

#PERMANENT_SESSION_LIFETIME
#If session.permanent is true, the cookie’s expiration will be set this number of seconds in the future. 
#Can either be a datetime.timedelta or an int.
#Flask’s default cookie implementation validates that the cryptographic signature is not older than this value.
#Default: timedelta(days=31) (2678400 seconds)

#SESSION_REFRESH_EACH_REQUEST
#Control whether the cookie is sent with every response when session.permanent is true. 
#Sending the cookie every time (the default) can more reliably keep the session from expiring, 
#but uses more bandwidth. Non-permanent sessions are not affected.
#Default: True

#USE_X_SENDFILE
#When serving files, set the X-Sendfile header instead of serving the data with Flask. 
#Some web servers, such as Apache, recognize this and serve the data more efficiently. 
#This only makes sense when using such a server.
#Default: False

#SEND_FILE_MAX_AGE_DEFAULT
#When serving files, set the cache control max age to this number of seconds. 
#Can be a datetime.timedelta or an int. Override this value on a per-file basis using get_send_file_max_age() 
#on the application or blueprint.
#If None, send_file tells the browser to use conditional requests will be used instead of a timed cache, 
#which is usually preferable.
#Default: None

#SERVER_NAME
#Inform the application what host and port it is bound to. Required for subdomain route matching support.
#If set, will be used for the session cookie domain if SESSION_COOKIE_DOMAIN is not set. 
#Modern web browsers will not allow setting cookies for domains without a dot. To use a domain locally, 
#add any names that should route to the app to your hosts file.
#127.0.0.1 localhost.dev
#If set, url_for can generate external URLs with only an application context instead of a request context.
#Default: None

#APPLICATION_ROOT
#Inform the application what path it is mounted under by the application / web server. 
#This is used for generating URLs outside the context of a request 
#(inside a request, the dispatcher is responsible for setting SCRIPT_NAME instead; 
#see Application Dispatching for examples of dispatch configuration).
#Will be used for the session cookie path if SESSION_COOKIE_PATH is not set.
#Default: '/'

#PREFERRED_URL_SCHEME
#Use this scheme for generating external URLs when not in a request context.
#Default: 'http'

#MAX_CONTENT_LENGTH
#Don’t read more than this many bytes from the incoming request data. 
#If not set and the request does not specify a CONTENT_LENGTH, no data will be read for security.
#Default: None

#JSON_AS_ASCII
#Serialize objects to ASCII-encoded JSON. If this is disabled, 
#the JSON returned from jsonify will contain Unicode characters. 
#This has security implications when rendering the JSON into JavaScript in templates, 
#and should typically remain enabled.
#Default: True

#Deprecated since version 2.2: Will be removed in Flask 2.3. Set app.json.ensure_ascii instead.
#JSON_SORT_KEYS
#Sort the keys of JSON objects alphabetically. This is useful for caching 
#because it ensures the data is serialized the same way no matter what Python’s hash seed is. 
#While not recommended, you can disable this for a possible performance improvement at the cost of caching.
#Default: True

#Deprecated since version 2.2: Will be removed in Flask 2.3. Set app.json.sort_keys instead
#JSONIFY_PRETTYPRINT_REGULAR
#jsonify() responses will be output with newlines, spaces, and indentation for easier reading by humans. 
#Always enabled in debug mode.
#Default: False

#Deprecated since version 2.2: Will be removed in Flask 2.3. Set app.json.compact instead.
#JSONIFY_MIMETYPE
#The mimetype of jsonify responses.
#Default: 'application/json'

#Deprecated since version 2.2: Will be removed in Flask 2.3. Set app.json.mimetype instead.
#TEMPLATES_AUTO_RELOAD
#Reload templates when they are changed. If not set, it will be enabled in debug mode.
#Default: None

#EXPLAIN_TEMPLATE_LOADING
#Log debugging information tracing how a template file was loaded. 
#This can be useful to figure out why a template was not loaded or the wrong file appears to be loaded.
#Default: False

#MAX_COOKIE_SIZE
#Warn if cookie headers are larger than this many bytes. Defaults to 4093. 
#Larger cookies may be silently ignored by browsers. Set to 0 to disable the warning.
#Changed in version 2.2: Removed PRESERVE_CONTEXT_ON_EXCEPTION.

#Changed in version 2.2: JSON_AS_ASCII, JSON_SORT_KEYS, JSONIFY_MIMETYPE, 
#and JSONIFY_PRETTYPRINT_REGULAR will be removed in Flask 2.3. 
#The default app.json provider has equivalent attributes instead.
#Changed in version 2.2: ENV will be removed in Flask 2.3. Use --debug instead.


class FlaskNodeProcess(Process):
    Name="FlaskNodeProcess"
    prefixe = None
    def __init__(self, name:str=None, config:Config=None, create_app=None, prefixe=None):
        if not name is None:
            self.Name = name.capitalize()
        if not prefixe is None:
            self.prefixe = prefixe.upper()

        self.config_path = config.COMMON_FILE_PATH
        self.config = None

        self.logger = None
        self.Flask_DB = None
        self.Log_Chat = None
        self.create_app = create_app
        super(FlaskNodeProcess, self).__init__()

    def run(self):
        try:
            self.config = Config(config_file_path=self.config_path, name=self.Name)
            self.config.update(section=self.Name.upper(), configPath=self.config.COMMON_FILE_PATH, params={"{0}_PORT".format(self.prefixe if not self.prefixe is None else self.Name):str(getUnusedPort())}, name=self.Name)

            self.logger = MyLogger(self.Name.lower(), self.config)
            dblog = Database(self.logger, self.config)
            # late binding
            self.logger.DBlog = dblog
        except Exception as e:
            self.logger.error("{0} : error while trying to start component(s) : {1}".format(self.Name, e))
        try:
            self.logger.info("{0} : Flask server (Independant Process Mode) is starting.. .  . ".format(self.Name))
            socketio, app, Flask_DB, Log_Chat = self.create_app(self.Name, self.config, self.logger, self.prefixe)
            self.Flask_DB = Flask_DB
            self.Log_Chat = Log_Chat
            app.logger = self.logger
            # Unsafe mode
            self.logger.info("{0} : Warning FlaskNode Process is launched in unsafe mode (allow_unsafe_werkzeug=True)".format(self.Name))
            socketio.run(app, allow_unsafe_werkzeug=True)
        except Exception as e:
            self.logger.error("{0} : error while trying to start FlaskNode Process : {1}".format(self.Name, e))


###########################################################################################################


class FlaskNodeSubsQ(SubsQ):
    Name="FlaskNodeSubsQ"
    def __init__(self, name, mainQueue:StarQs, logger:MyLogger, config:Config, default_recv:str=None, ChildProc=None, create_app=None, prefixe=None, **kwargs):
        self.Name = name.capitalize()
        self.prefixe = None
        if not prefixe is None:
            self.prefixe = prefixe.upper()
        self.logger = logger
        self.config = config
        
        self.config.update(section=self.Name.upper(), configPath=config.COMMON_FILE_PATH, params={"{0}_PORT".format(self.prefixe if not self.prefixe is None else self.Name):str(getUnusedPort())}, name=self.Name)

        SubsQ.__init__(self, name=self.Name, mainQueue=mainQueue, default_recv=default_recv, ChildProc=ChildProc, **kwargs)
        Thread(target=self.runFlask, args=(create_app,)).start()

    def runFlask(self, create_app=None):
        try:
            self.logger.info("{0} : Flask server (Subscriber Mode) is starting.. .  . ".format(self.Name))
            socketio, app, _, _ = create_app(self.Name, self.config, self.logger, self.prefixe)
            app.logger = self.logger
            # Unsafe mode
            self.logger.info("{0} : Warning FlaskNode SubsQ is launched in unsafe mode (allow_unsafe_werkzeug=True)".format(self.Name))
            socketio.run(app)
        except Exception as e:
            self.logger.error("{0} : error while trying to start FlaskNode Thread : {1}".format(self.Name, e))



class FlaskNode:
    def __init__(self, name:str, config:Config, mainQueue=None, logger=None, default_recv:str=None, ChildProc=None, create_app=None, prefixe=None, **kwargs):
        if not mainQueue is None:
            # start subsQ Broker Analysis
            _ = FlaskNodeSubsQ(name, mainQueue, logger, config, default_recv, ChildProc, create_app, prefixe,**kwargs)
        else:
            # start independant server analysis
            p = FlaskNodeProcess(name, config, create_app, prefixe)
            p.start()
            p.join()


#================================================================
if __name__ == "__main__":
    name = "flaskNode"
    config = Config(name=name)
    ## SA Analysis server
    _newProcessNode = FlaskNode(name=name, create_app=create_app, prefixe="fn", config=config )

# SA Analysis subscriber
    #from common.Helpers.helpers import init_logger
    ##name = "{0}_ThreadQs".format(name)
    #configStr = "common"
    #config, logger = init_logger(name=name, config=configStr) 
#
    #mainQueue = StarQs(logger, config, "{0}_streamQ".format(name))
    #_newSubQsNode = FlaskNode(name, mainQueue=mainQueue, logger=logger, config=config, create_app=create_app, prefixe="fn")



