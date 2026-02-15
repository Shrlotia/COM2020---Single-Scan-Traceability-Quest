from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user

from sstq.extensions import login_manager, db
from sstq.models import User
from sstq.auth_decorators import login_required

auth_bp = Blueprint("auth", __name__)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        # we take the type of action (button pressed), username and password as inputs from a html form
        action = request.form.get("action")
        username = request.form.get("username")
        password = request.form.get("password")
        
        # if no username or password, no user will get authenticated
        if not username or not password:
            flash("Username and password required", "error")
            return redirect(url_for("auth.login"))
        
        # SQLite3 DB is queried for a user with the username defined by 'username'
        user = User.query.filter_by(username=username).first()
         
        if action == "login":
            # if the user wants to login but the user doesn't exist or their passwords don't match, login fails
            if not user or not user.check_password(password):
                flash("Invalid username or password", "error")
                return redirect(url_for("auth.login"))
            # otherwise, user is logged in successfully and redirected back home
            else:
                login_user(user)
                return redirect(url_for("home.home"))
            
        if action == "register":
            # decides whether the user wants to register as a 'consumer' or 'verifier' based on the value of the html checkbox
            role = "verifier" if (request.form.get("is_verifier") is not None) else "consumer"
            
            # if there is already a user with that username, a new one spongebobviously can't be registered
            if user:
                flash("Username already exists: Pick another", "error")
                return redirect(url_for("auth.login"))
            # if no user exists, we can create a new record in the 'User' table
            else:
                new_user = User(username=username, role=role)
                # password is set using the in-built method because it allows the password to be securely hashed based on the secret app key
                new_user.set_password(password)
                
                db.session.add(new_user)
                # commit the full transaction to DB when no errors happen
                db.session.commit()
                
                # automatically logs the user in (might change later but probably not) and redirects them to the homepage
                login_user(new_user)
                flash("Account successfully created", "success")
                return redirect(url_for("home.home"))
            
# endpoint that isn't linked to a webpage but rather a request that logs out the current user
@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():
    # flask_login can easily logout the the auth user automatically
    logout_user()  
    flash("You have been logged out", "success")
    # takes user back to the homepage to ensure an anonymous user cannot accidentally access the wrong page
    return redirect(url_for("home.home"))