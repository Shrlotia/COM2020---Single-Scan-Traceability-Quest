document.getElementById("barcode-form").addEventListener("submit", async e =>{
    e.preventDefault();

    const barcode = document.getElementById("barcode").value.trim();

    const res = await fetch("/validate_barcode", {
        method: 'POST',
        headers: {"Content-Type" : "application/json"},
        body: JSON.stringify({barcode})
    });

    const barcode_valid = await res.json();

    if (!barcode_valid.valid){
        document.getElementById("error").innerText = barcode_valid.message;
        document.getElementById("error").hidden = false;
        return;
    };

    document.getElementById("barcode-form").hidden = true;
    document.getElementById("details-form").hidden = false;
});

productDetailsForm.addEventListener('submit', e =>{
    e.preventDefault();

    const productData = {
        barcode: document.getElementById("barcode").value.trim(),
        name: document.getElementById("name").value.trim(),
        category: document.getElementById("category").value.trim(),
        brand: document.getElementById("brand").value.trim(),
        Description: document.getElementById("Description").value.trim()
    };

    fetch("/add_product", {
        method: 'POST',
        headers: {"Content-Type" : "application/json"},
        body: JSON.stringify({productData})
    })
    .then(res => res.json())
    .then(data => {
    if (data.success) {
        // Navigate to the product page
        window.location.href = `/product/${data.barcode}`;
    } else {
        console.error("Error:", data.message);
    }
    });


});