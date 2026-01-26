# imports all tools for requesting and responding to HTTP requests, as well as the 'app', 'db' and 'Contact' elements
from flask import request, jsonify, render_template
from config import app, db
from models import Contact

# connects to the index (/) of the web app and shows the default view
@app.route("/", methods=["GET", "POST"])
def index():
    username = None
    
    # In this example, we can send json data to the server so that it can display out 'username'
    if request.method == "POST":
        username = request.form["username"]
        
    # renders one of our html files in '/templates' while supplying the variable 'username'
    return render_template("index.html", username=username)

# connects to 'localhost:5050/contacts' endpoint and displays all contact data
@app.route("/contacts", methods=["GET"])
def get_contacts():
    # queries our sqlite DB and gets all records
    contacts = Contact.query.all()
    return render_template("contacts.html", contacts=contacts)

# connects to 'localhost:5050/create_contact' endpoints and allows us to add a new contact
@app.route("/create_contact", methods=["POST"])
def create_contact():
    # fetches all parameters from the request
    first_name = request.json.get("firstName")
    last_name = request.json.get("lastName")
    email = request.json.get("email")
    
    # error handling for when the json request has incomplete data
    if not first_name or not last_name or not email:
        return jsonify({"message": "You must include a first and last name as well as an email"}), 400
        
    # we turn user data from request into a new DB entry and attempt to add it to the DB
    new_contact = Contact(first_name=first_name, last_name=last_name, email=email)
    
    try:
        db.session.add(new_contact)
        db.session.commit()
    except Exception as e:
        return jsonify({"message": str(e)}), 400
    
    return jsonify({"message": "User has been created"}), 201

# updates contact based on parameters within the URL
@app.route("/update_contact/<int:id>", methods=["PATCH"])
def update_contact(id):
    # queries DB for user with same ID as what is in the URL
    contact = Contact.query.get(id)
    
    if not contact:
        return jsonify({"message": f"No user with ID {id} in DB"}), 404
    
    # updates the relevant DB record with either A) a new attribute or B) keeps it the same
    data = request.json
    contact.first_name = data.get("firstName", contact.first_name)
    contact.last_name = data.get("lastName", contact.last_name)
    contact.email = data.get("email", contact.email)
    
    # commit transaction to our DB
    db.session.commit()
    
    return jsonify({"message": f"User with ID {id} has been updated"}), 200

@app.route("/delete_contact/<int:id>", methods=["DELETE"])
def delete_contact(id):
    contact = Contact.query.get(id)
    
    if not contact:
        return jsonify({"message": f"No user with ID {id} in DB"}), 404
    
    # deletes a record from the DB
    db.session.delete(contact)
    db.session.commit()
    
    return jsonify({"message": f"User with ID {id} has been deleted"}), 200

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":  
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)