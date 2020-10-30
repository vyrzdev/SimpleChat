from flask import redirect
from flask_login import current_user


def pre(routeFunction):
    def newFunc(*args, **kwargs):
        if not current_user.is_authenticated:
            return "AHHHHHHHHHHHHH"
        return routeFunction(*args, **kwargs)

    return newFunc
