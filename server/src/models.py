import mongoengine
from flask_login import UserMixin, current_user
from . import login
from werkzeug.security import generate_password_hash, check_password_hash
from .config import Config
from uuid import uuid4
import datetime


def generate_room_code():
    return str(uuid4())[:Config.App.code_length]


class Alert:
    def __init__(self, message):
        self.message = message


@login.user_loader
def user_loader(userID):
    return User.objects(id=userID).first()


class User(mongoengine.Document, UserMixin):
    username = mongoengine.StringField(required=True)
    email = mongoengine.EmailField(required=True)
    passwordHash = mongoengine.StringField(required=True)

    def checkPassword(self, plaintextPass):
        return check_password_hash(self.passwordHash, plaintextPass)

    def setPassword(self, plaintextPass):
        self.passwordHash = generate_password_hash(plaintextPass)


def get_user_object() -> User:
    return User.objects(id=current_user.id).first()


class Chatroom(mongoengine.Document):
    room_code = mongoengine.StringField(required=True, default=generate_room_code, unique=True)
    passwordProtected = mongoengine.BooleanField(default=False)

    roomPasswordHash = mongoengine.StringField()

    def checkPassword(self, plaintextPass):
        return check_password_hash(self.roomPasswordHash, plaintextPass)

    def setPassword(self, plaintextPass):
        self.roomPasswordHash = generate_password_hash(plaintextPass)

    def clean_delete(self):
        userRegistrations = ChatroomUserRegistration.objects(
            room=self
        ).all()
        for userReg in userRegistrations:
            userReg.delete()
        self.delete()


class ChatroomUserRegistration(mongoengine.Document):
    user: User = mongoengine.ReferenceField(User, required=True)
    room: Chatroom = mongoengine.ReferenceField(Chatroom, required=True)
    admin: bool = mongoengine.BooleanField(default=False)
    active: bool = mongoengine.BooleanField(default=False)

    def connect(self):
        self.active = True

    def disconnect(self):
        self.active = False


class Message(mongoengine.Document):
    author: User = mongoengine.ReferenceField(User, required=True)
    room: Chatroom = mongoengine.ReferenceField(Chatroom, required=True)
    message: dict = mongoengine.DictField(required=True, default=dict)
    timeSent: datetime.datetime = mongoengine.DateTimeField(required=True, default=datetime.datetime.utcnow)
