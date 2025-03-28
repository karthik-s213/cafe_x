function getCart() {
    return JSON.parse(localStorage.getItem('cart')) || [];
}

function renderCart() {
    let cart = getCart();

    fetch('/get_cart_data', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart }) // ✅ Send menu_id instead of item name
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            document.getElementById('cart-items').innerHTML = '<p>Your cart is empty.</p>';
            document.getElementById('total-items').innerText = "0";
            document.getElementById('total-price').innerText = "0.00";
            return;
        }

        const cartItemsContainer = document.getElementById('cart-items');
        const totalItems = document.getElementById('total-items');
        const totalPrice = document.getElementById('total-price');

        cartItemsContainer.innerHTML = '';
        let itemCount = 0;

        data.cart.forEach(item => {
            itemCount += item.quantity;

            const cartItem = document.createElement('div');
            cartItem.classList.add('cart-item');

            cartItem.innerHTML = `
                <div class="item-details">
                    <h2>${item.name}</h2>
                    <p>$${item.price.toFixed(2)} x ${item.quantity}</p>
                </div>
                <div class="actions">
                    <button onclick="updateQuantity(${item.menu_id}, ${item.quantity - 1})">-</button>
                    <button onclick="updateQuantity(${item.menu_id}, ${item.quantity + 1})">+</button>
                    <button class="remove-btn" onclick="removeItem(${item.menu_id})">❌ Remove</button>
                </div>
            `;

            cartItemsContainer.appendChild(cartItem);
        });

        totalItems.innerText = itemCount;
        totalPrice.innerText = data.total_price.toFixed(2);
    })
    .catch(error => console.error("Error fetching updated cart data:", error));
}
function updateQuantity(menuId, newQuantity) {
    let cart = getCart();
    const item = cart.find(item => item.menu_id === menuId);

    if (item) {
        if (newQuantity <= 0) {
            removeItem(menuId);
        } else {
            item.quantity = newQuantity;
            updateCart(cart);
        }
    }
}
function removeItem(menuId) {
    let cart = getCart();
    cart = cart.filter(item => item.menu_id !== menuId);
    updateCart(cart);
    updateCartCount();
}

document.getElementById("checkout-btn").addEventListener("click", function () {
    const totalPrice = parseFloat(document.getElementById("total-price").innerText);

    fetch("/pay_with_tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ total_price: totalPrice })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Payment successful! Remaining Tokens: " + data.remaining_tokens);
            localStorage.removeItem("cart"); // ✅ Clear cart after successful payment
            window.location.href = "/"; // ✅ Redirect to home page
        } else {
            alert(data.error); // Show error if not enough tokens
        }
    })
    .catch(error => console.error("Error processing payment:", error));
});



// ✅ Function to remove an item from the cart & update menu button
// ✅ Function to remove an item from the cart & update menu button
function removeItem(itemName) {
    let cart = getCart();
    cart = cart.filter(item => item.name !== itemName); // ✅ Remove item from cart
    updateCart(cart);
    updateCartCount(); // ✅ Ensure cart button count updates in menu page
}


// ✅ Function to update the cart button count in menu
function updateCartCount() {
    const cart = getCart();
    const totalItems = cart.reduce((acc, item) => acc + item.quantity, 0);
    
    const cartButton = document.getElementById("cart-btn");
    if (cartButton) {
        cartButton.innerText = `Cart (${totalItems})`; // ✅ Update button text
    }
}

// ✅ Initial render of the cart & update cart count on load
window.onload = function () {
    renderCart();
    updateCartCount(); // ✅ Update cart button count on page load
};
function viewCart() {
    fetch('/cart_count')
    .then(response => response.json())
    .then(data => {
        if (data.count > 0) {
            window.location.href = "/cart";
        } else {
            sessionStorage.setItem("previousPage", "/cart");  // ✅ Save previous page
            window.location.href = "/signin";  // ✅ Redirect to Sign-In
        }
    })
    .catch(error => console.error("Error:", error));
}
