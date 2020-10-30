import mongoengine
from flask_login import UserMixin
from . import login
from werkzeug.security import generate_password_hash, check_password_hash


class Alert:
    def __init__(self, message):
        self.message = message


@login.user_loader
def user_loader(userID):
    return User.objects.get(id=userID)


class User(mongoengine.Document, UserMixin):
    username = mongoengine.StringField(required=True)
    email = mongoengine.EmailField(required=True)
    passwordHash = mongoengine.StringField(required=True)

    def checkPassword(self, plaintextPass):
        return check_password_hash(self.passwordHash, plaintextPass)

    def setPassword(self, plaintextPass):
        self.passwordHash = generate_password_hash(plaintextPass)