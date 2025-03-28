document.addEventListener("DOMContentLoaded", function () {
    updateCartCount();
});

// ✅ Add to cart function
function addToCart(item, price) {
    let cart = JSON.parse(localStorage.getItem("cart")) || [];
  
    const existingItem = cart.find(cartItem => cartItem.name === item);
    if (existingItem) {
        existingItem.quantity++;
    } else {
        cart.push({ name: item, price: price, quantity: 1 });
    }
  
    localStorage.setItem("cart", JSON.stringify(cart));
    updateCartCount();
}

// ✅ Update cart count in menu
function updateCartCount() {
    const cart = JSON.parse(localStorage.getItem("cart")) || [];
    const totalItems = cart.reduce((acc, item) => acc + item.quantity, 0);
  
    const cartButton = document.getElementById("cart-btn");
    if (cartButton) {
        cartButton.innerText = `Cart (${totalItems})`;
    }
}

// ✅ Sync cart across multiple tabs
window.addEventListener("storage", updateCartCount);

// ✅ Redirect to cart or sign-in
function viewCart() {
    fetch('/is_logged_in')
    .then(response => response.json())
    .then(data => {
        if (data.logged_in) {
            window.location.href = "/cart";
        } else {
            sessionStorage.setItem("previousPage", "/cart");
            window.location.href = "/signin";
        }
    });
}

// ✅ Attach event listener if element exists
const cartBtn = document.getElementById("cart-btn");
if (cartBtn) {
    cartBtn.addEventListener("click", viewCart);
}
