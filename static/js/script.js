// gets the form by its ID and adds an event listener for the 'submit' button, waiting indefinitely (async) for a response
document.getElementById("create-form").addEventListener("submit", async (e) => {
    // prevents the document from refreshing automatically, allowing the form data to be submitted fully
    e.preventDefault();

    // JSONified version of the data inputted into the fields of the form
    const data = {
        firstName: document.getElementById("firstName").value,
        lastName: document.getElementById("lastName").value,
        email: document.getElementById("email").value,
    };

    // the script sends a POST request to the '/create_contact' endpoint with the JSON data from the 'data'
    // variable, where 'response' is the response to that HTTP request from the server
    const response = await fetch("/create_contact", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    // If the status code of the response is 200 (OK, i.e.: the request was successful), we can safely
    // reload the page.
    if (response.ok) {
        location.reload();
    } else {
        // Otherwise, we show a popup alert in the browser
        alert("Failed to create contact");
    }
});

// function takes the 'id' of the contact to delete from the DB
// async means the function waits until everything is finished
async function deleteContact(id) {
    // sends DELETE HTTP request to endpoint '/delete_contact' with 'id' as the parameter
    const response = await fetch(`/delete_contact/${id}`, {
        method: "DELETE"
    });

    if (response.ok) {
        location.reload();
    } else {
        console.log(id);
        alert("Failed to delete");
    }
}

// functions takes the 'id' of the contact to update in the DB
async function updateContact(id) {
    // This is the data from another table (unique from 'create-form') as JSON
    const data = {
        firstName: document.getElementById(`fn-${id}`).value,
        lastName: document.getElementById(`ln-${id}`).value,
        email: document.getElementById(`em-${id}`).value
    }

    // sends PATCH request to '/update_contacts' with input 'id' as a parameter
    const response = await fetch(`/update_contact/${id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        location.reload();
    } else {
        console.log(id);
        alert("Failed to update");
    }
}