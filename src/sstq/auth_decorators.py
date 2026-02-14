# the imports allow the decorator to use other 'wrapped' decorators within, cause aborts for the wrong users and looks at the current user
from functools import wraps
from flask import abort
from flask_login import current_user, login_required

# allows for the decorator to have multiple values (i.e.: something can be accessible for 'verifier' and 'admin' roles)
def roles_required(*roles):
    # 'view_func' is the name of the method the decorator will be used on
    def decorator(view_func):
        # needs to be there because of the multi-value decorator
        @wraps(view_func)
        # still requires the base login authentication from flask_login
        @login_required
        def wrapped_view(*args, **kwargs):
            # if the tags are not the ones in the decorator, don't allow them on certain webpages
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator