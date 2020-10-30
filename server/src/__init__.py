from flask import Flask
from flask_login import LoginManager
from .pre import pre
import mongoengine

from . import config


mongoengine.connect(config.Config.Database.db_connection_string, db="test_chatv2")
app = Flask(__name__)
app.secret_key = config.Config.Flask.secret_key
login = LoginManager(app)
login.login_view = "login"

from . import routes

