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

document.getElementById("barcodeUpdateForm").addEventListener("submit", async e =>{
    e.preventDefault();

    const barcode = document.getElementById("barcodeToUpdate").value.trim();

    const res = await fetch("/validate_barcode", {
        method: 'POST',
        headers: {"Content-Type" : "application/json"},
        body: JSON.stringify({barcode})
    });

    const barcode_valid = await res.json();

    if (!barcode_valid.valid && barcode_valid.message==="Barcode already exists"){
        getProductDetails(barcode);

        document.getElementById("barcodeUpdateForm").hidden = true;
        document.getElementById("UpdateProductDetails").hidden = false;
        return;
    }else{
        alert("barcode doesn't exit in the system u should add it instead")
    }
});

function displayProduct(product, barcode) {
    document.getElementById("update-barcode").innerText = barcode;
    document.getElementById("update-name").innerText = product.name;
    document.getElementById("update-category").innerText = product.category;
    document.getElementById("update-brand").innerText = product.brand;
    document.getElementById("update-description").innerText = product.description;
}

async function getProductDetails(barcode){
    try {
        const res = await fetch(`/update_product?barcode=${barcode}`);

        const productDetails= await res.json();
        displayProduct(productDetails, barcode);
    }catch (err){
        alert("Network error")
    }
};

document.getElementById("cancel-update-button").addEventListener("click", (e) =>{
    document.getElementById("barcodeUpdateForm").hidden = false;
    document.getElementById("UpdateProductDetails").hidden = true;
    document.getElementById("update-barcode").innerText = "";
    document.getElementById("update-name").innerText = "";
    document.getElementById("update-category").innerText = "";
    document.getElementById("update-brand").innerText = "";
    document.getElementById("update-description").innerText = "";
});
