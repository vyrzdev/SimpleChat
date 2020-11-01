from . import app, socketio
from ..models import get_user_object, Chatroom, Alert, ChatroomUserRegistration, Message
from flask import request, redirect, render_template, abort
from flask_login import login_required, current_user
from flask_socketio import disconnect, emit, join_room
from typing import List
from html import escape
import functools


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

@app.route("/")
@login_required
def list_rooms():
    user = get_user_object()
    usersRoomRegistrations = ChatroomUserRegistration.objects(
        user=user
    ).all()
    usersRooms = [roomReg.room for roomReg in usersRoomRegistrations]
    return render_template("chat/list_rooms.html", rooms=usersRooms)


@app.route("/room/create", methods=["POST", "GET"])
@login_required
def createRoom():
    if request.method == "GET":
        return render_template("chat/create_chat.html", title="Create Room")
    else:
        user = get_user_object()
        roomJoinCode = request.form.get("room_code")
        roomJoinCode = escape(roomJoinCode)
        if (roomJoinCode is None) or (roomJoinCode == ""):
            return render_template("chat/create_chat.html", title="Create Room", alerts=[Alert("Room Join Code Required!")])
        roomPassword = request.form.get("room_password")
        existingRoom: Chatroom = Chatroom.objects(room_code=roomJoinCode).first()
        if existingRoom is not None:
            return render_template("chat/create_chat.html", title="Create Room", alerts=[Alert("Room Already Exists!")])

        passwordSupplied = (roomPassword is not None) or (roomPassword != "")
        newRoomObject: Chatroom = Chatroom(
            room_code=roomJoinCode,
            passwordProtected=passwordSupplied,
        )
        if passwordSupplied:
            newRoomObject.setPassword(roomPassword)

        userRoomRegistration = ChatroomUserRegistration(
            user=user,
            room=newRoomObject,
            admin=True
        )
        newRoomObject.save()
        userRoomRegistration.save()
        return redirect(f"/room/{newRoomObject.room_code}")


@app.route("/room/delete")
@login_required
def delete_room():
    roomCode = request.args.get("code")
    if roomCode is None:
        abort(404)
    user = get_user_object()
    roomRegistration = Chatroom.objects(
        room_code=roomCode
    ).first()
    if roomRegistration is None:
        print("Not a room")
        abort(404)
    userRoomRegistration = ChatroomUserRegistration.objects(
        user=user,
        room=roomRegistration
    ).first()
    if not userRoomRegistration.admin:
        abort(401)
    socketio.emit("room_deleted", room=roomRegistration.room_code)
    roomRegistration.clean_delete()
    return redirect("/")


@app.route("/room/leave")
@login_required
def leave_room():
    roomCode = request.args.get("code")
    if roomCode is None:
        abort(404)
    user = get_user_object()
    roomRegistration = Chatroom.objects(
        room_code=roomCode
    ).first()
    if roomRegistration is None:
        print("Not a room")
        abort(404)
    userRoomRegistration = ChatroomUserRegistration.objects(
        user=user,
        room=roomRegistration
    ).first()
    if userRoomRegistration.admin:
        abort(401, "You Must Delete.")
    userRoomRegistration.delete()
    socketio.emit("user_left", {"username": user.username}, room=roomRegistration.room_code)
    return redirect("/")


@app.route("/room/join", methods=["POST", "GET"])
@login_required
def joinRoomInitial():
    if request.method == "GET":
        return render_template("chat/enter_code.html", title="Join Room", code=request.args.get("code"))
    else:
        user = get_user_object()
        roomJoinCode = request.form.get("room_code")
        roomJoinCode = escape(roomJoinCode)
        roomPassword = request.form.get("room_password")
        roomObject: Chatroom = Chatroom.objects(room_code=roomJoinCode).first()
        if roomObject is None:
            return render_template("chat/enter_code.html", title="Join Room", alerts=[Alert("Invalid Room Code!")])
        if roomObject.passwordProtected:
            if (roomPassword is None) or (not roomObject.checkPassword(roomPassword)):
                return render_template("chat/enter_code.html", title="Join Room", alerts=[Alert("Invalid Room Password!")])
            else:
                pass
        else:
            pass
        existingRoomUserRegistration = ChatroomUserRegistration.objects(
            user=user,
            room=roomObject
        ).first()
        if existingRoomUserRegistration is not None:
            return redirect(f"/room/{existingRoomUserRegistration.room.room_code}")
        newRoomUserRegistration = ChatroomUserRegistration(
            user=user,
            room=roomObject
        )
        newRoomUserRegistration.save()
        return redirect(f"/room/{newRoomUserRegistration.room.room_code}")


@app.route("/room/<room_code>")
@login_required
def load_room(room_code):
    roomRegistration = Chatroom.objects(room_code=room_code).first()
    if roomRegistration is None:
        abort(404)
    user = get_user_object()
    userRoomRegistration: ChatroomUserRegistration = ChatroomUserRegistration.objects(
        user=user,
        room=roomRegistration
    ).first()
    if userRoomRegistration is None:
        return redirect(f"/room/join?code={room_code}")

    return render_template("chat/chatroom.html", room_code=escape(room_code), is_admin=userRoomRegistration.admin)


@socketio.on("join_room_foo")
@authenticated_only
def joinRoom(data):
    userObject = get_user_object()
    room_code = data.get("room_code")
    if room_code is None:
        disconnect()
    activeUserSessions = ChatroomUserRegistration.objects(
        user=userObject,
        active=True
    ).count()
    if activeUserSessions > 0:
        disconnect()
    roomObject: Chatroom = Chatroom.objects(room_code=room_code).first()
    userRoomRegistration: ChatroomUserRegistration = ChatroomUserRegistration.objects(
        user=userObject,
        room=roomObject
    ).first()
    if userRoomRegistration is None:
        disconnect()
    else:
        join_room(room_code)
        userRoomRegistration.connect()
        userRoomRegistration.save()
        pastMessages = Message.objects(
            room=roomObject
        ).limit(50)
        emit("user_data", {"username": userObject.username})
        emit("message_history", {
            "messages": [
                {"username": message.author.username,
                 "message": {
                    "_id": str(message.id),
                    "text": message.message.get("text"),
                    "sent_at": message.timeSent.timestamp()
                 }
                }
            for message in pastMessages]
        })
        emit("user_joined", {"username": userObject.username}, room=room_code)


@socketio.on("message_send")
@authenticated_only
def message_send(data):
    userObject = get_user_object()
    room_code = data.get("room_code")
    roomObject: Chatroom = Chatroom.objects(room_code=room_code).first()
    userRoomRegistration: ChatroomUserRegistration = ChatroomUserRegistration.objects(
        user=userObject,
        room=roomObject
    ).first()
    if userRoomRegistration is None:
        disconnect()
    else:
        newMessage = Message(
            author=userObject,
            room=roomObject,
            message={
                "text": escape(data.get("message_text"))
            }
        )
        newMessage.save()
        emit("message_sent", {
            "username": userObject.username,
            "message": {
                "_id": str(newMessage.id),
                "text": escape(data.get("message_text")),
                "sent_at": newMessage.timeSent.timestamp()
            }
        }, room=room_code)


@socketio.on("disconnect")
def on_disconnect():
    ActiveRoomUserRegistrations = ChatroomUserRegistration.objects(
        user=get_user_object(),
        active=True
    ).all()

    roomUserReg: ChatroomUserRegistration
    for roomUserReg in ActiveRoomUserRegistrations:
        roomUserReg.disconnect()
        roomUserReg.save()
        emit("user_left", {"username": get_user_object().username}, room=roomUserReg.room.room_code)


@socketio.on("users_in_room")
def users_in_room(data):
    userObject = get_user_object()
    room_code = data.get("room_code")
    roomObject: Chatroom = Chatroom.objects(room_code=room_code).first()
    userRoomRegistration: ChatroomUserRegistration = ChatroomUserRegistration.objects(
        user=userObject,
        room=roomObject
    ).first()
    if userRoomRegistration is None:
        disconnect()
    else:
        activeUserRegistrationsInRoom: List[ChatroomUserRegistration] = ChatroomUserRegistration.objects(
            room=roomObject,
            active=True
        ).all()
        userDump = list()
        for activeUserReg in activeUserRegistrationsInRoom:
            userDump.append({
                "username": activeUserReg.user.username
            })
        emit("users_in_room_resp", {"users": userDump})

