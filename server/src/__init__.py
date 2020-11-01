from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
import mongoengine

from . import config


mongoengine.connect(db="test_chatv2")
app = Flask(__name__)
if config.Config.Flask.secret_key == "DEFAULT":
    print("Okay so you gotta change the secret_key option in config.py, which is located in the src directory.")
    print("Couldn't be bothered to you know... config file?")
    exit()
app.secret_key = config.Config.Flask.secret_key
login = LoginManager(app)
login.login_view = "login"
socketio = SocketIO(app)


from . import routes

