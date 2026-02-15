# all imports for flask web app deployment, flask role-based auth and links to the app, database and user table from 'config.py' and 'models.py'
from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from sstq.auth_decorators import roles_required
from sstq.config import app, db
from sstq.models import User, Product
# import all the routes from add_product to register them
# from sstq import add_product

# creates a new login manager for the current application where the default login view (if you aren't logged in) is 'login.html'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# links the current web app session to the user that has just logged in
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# connects to the index (/) of the web app and shows the homepage, full of useful information
# the 'GET' part tells us what HTTP requests the endpoint can handle (this one just shows data)
@app.route("/", methods=["GET"])
def home():
    # render a html template (webpage); this doesn't refresh the browser window
    return render_template("home.html")

# endpoint that allows the user to enter in or scan a barcode for a product
@app.route("/scan", methods=["GET", "POST"])
@login_required # means you cannot access this page without being authenticated
def scan():
    # if we want to see the main scan page, we load it in this branch
    if request.method == "GET":
        return render_template("scan.html")
    # once we scan the barcode, we can process it and show the product info
    elif request.method == "POST":
        # if the barcode is empty, the value is set to ""
        barcode = request.form.get("barcode", "").strip()
        
        # keeps refreshing the scan page if the barcode is not valid (empty)
        if not barcode:
            return redirect(url_for("scan"))

        # if the barcode is valid, we send it the the '/product/<barcode>' endpoint to be displayed
        return redirect(url_for("product_detail", barcode=barcode))

# product list page that shows all products in the DB
@app.route("/product", methods=["GET"])
@login_required
def product():
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template("product.html", products=products)

# simple product details page that receives the detected barcode
@app.route("/product/<barcode>", methods=["GET"])
@login_required
def product_detail(barcode):
    product = db.session.get(Product, barcode)
    if not product:
        return render_template("error.html", message="Product not found")
    return render_template("product_detail.html", barcode = product.barcode, name = product.name, category = product.category,
                            brand = product.brand, description = product.description, image = product.image)

# allows the user to check the 'Traceability Timeline' for a given product
@app.route("/timeline", methods=["GET"])
@login_required
def timeline():
    return render_template("timeline.html")

# allows the player to play 'Trace Quest' with a given product
@app.route("/trace_quest", methods=["GET"])
@login_required
def tracequest():
    return render_template("tracequest.html")

# shows a profile page for each player with their stats, completed missions and potential leaderboard (2nd sprint only)
@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html")

# endpoint that allows a verifier to add/update products within the DB, adding claims and evidence labels
@app.route("/add_product", methods=["GET"])
@roles_required("verifier", "admin") # you can only visit this page if your auth user type is 'verifier' or 'admin'
def add():
    
    if request.is_json:
        #it will pass the permission check if it is testing  
        if not app.config.get("TESTING"):       
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
        
        data = request.get_json()

        if not data or "productData" not in data:
            return jsonify({"success": False}), 400

        product_data = data["productData"]
        barcode = product_data.get("barcode")

        #check for duplicates
        existing = Product.query.filter_by(barcode=barcode).first()
        if existing:
            return jsonify({"success": False}), 400
        
        new_product = Product(
            barcode=barcode,
            name=product_data.get("name"),
            category=product_data.get("category"),
            brand=product_data.get("brand"),
            description=product_data.get("description"),
            image=product_data.get("image"),
        )

        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            "success": True,
            "barcode": barcode
        }), 200
    
    #if not JSON it will show the html
    return render_template("add.html")

@app.route("/login", methods=["GET", "POST"])
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
            return redirect(url_for("login"))
        
        # SQLite3 DB is queried for a user with the username defined by 'username'
        user = User.query.filter_by(username=username).first()
         
        if action == "login":
            # if the user wants to login but the user doesn't exist or their passwords don't match, login fails
            if not user or not user.check_password(password):
                flash("Invalid username or password", "error")
                return redirect(url_for("login"))
            # otherwise, user is logged in successfully and redirected back home
            else:
                login_user(user)
                return redirect(url_for("home"))
            
        if action == "register":
            # decides whether the user wants to register as a 'consumer' or 'verifier' based on the value of the html checkbox
            role = "verifier" if (request.form.get("is_verifier") is not None) else "consumer"
            
            # if there is already a user with that username, a new one spongebobviously can't be registered
            if user:
                flash("Username already exists: Pick another", "error")
                return redirect(url_for("login"))
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
                return redirect(url_for("home"))
            
# endpoint that isn't linked to a webpage but rather a request that logs out the current user
@app.route("/logout", methods=["GET"])
@login_required
def logout():
    # flask_login can easily logout the the auth user automatically
    logout_user()  
    flash("You have been logged out", "success")
    # takes user back to the homepage to ensure an anonymous user cannot accidentally access the wrong page
    return redirect(url_for("home"))

# this endpoint actually contains all of the added/updated products for a VERIFIER (not necessarily an admin)
@app.route("/admin", methods=["GET"])
@roles_required("verifier", "admin")
def admin():
    return render_template("admin.html")

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":  
    with app.app_context():
        db.create_all()
        
    # Listen on all interfaces so the app is reachable from your phone on the same Wi-Fi.
    # does not work on mobile no matter what I try, might have to fix later
    app.run(debug=True, host="0.0.0.0", port=8000)
