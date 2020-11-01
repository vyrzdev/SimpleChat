from . import app, models
from flask import render_template, redirect, request
from flask_login import current_user, logout_user, login_user, login_required
from html import escape


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "GET":
        if request.args.get("next") is not None:
            return render_template("auth/login.html", next=request.args.get("next"))
        else:
            return render_template("auth/login.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        if username is None:
            return render_template("auth/login.html", alerts=[models.Alert("Username Required!")])
        if password is None:
            return render_template("auth/login.html", alerts=[models.Alert("Password Required!")])

        userObject = models.User.objects(username=username).first()
        if userObject is None:
            return render_template("auth/login.html", alerts=[models.Alert("Invalid Username/Password!")])
        if not userObject.checkPassword(password):
            return render_template("auth/login.html", alerts=[models.Alert("Invalid Username/Password!")])
        else:
            login_user(userObject)
            print(request.args.get("next"))
            if request.args.get("next") is not None:
                return redirect(request.args.get("next"))
            return redirect("/")


@app.route("/register", methods=["POST", "GET"])
def register():
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "GET":
        return render_template("auth/register.html")
    else:
        username = request.form.get("username")
        username = escape(username)
        email = request.form.get("email")
        password = request.form.get("password")
        check_password = request.form.get("check_password")
        if username == "":
            return render_template("auth/register.html", alerts=[models.Alert("Username is required!")])
        if email == "":
            return render_template("auth/register.html", alerts=[models.Alert("Email is required!")])
        if password == "":
            return render_template("auth/register.html", alerts=[models.Alert("Password is required!")])
        if check_password != password:
            return render_template("auth/register.html", alerts=[models.Alert("Passwords do not match!")])
        else:
            newUser = models.User(
                username=username,
                email=email,
            )
            newUser.setPassword(password)
            newUser.save()
            return redirect("/login")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")
