document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart count
    updateCartCount();

    // Add event listeners to menu buttons
    document.querySelectorAll('.menu_btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const itemId = this.dataset.id;
            const itemName = this.dataset.name;
            const price = parseFloat(this.dataset.price);
            addToCart(itemId, itemName, price);
        });
    });
});

// ✅ Add to cart function
function addToCart(itemId, itemName, price) {
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            item_id: itemId,
            item_name: itemName,
            price: price,
            quantity: 1
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Item added to cart!', false);
            updateCartCount();
        } else {
            showNotification(data.error || 'Error adding item to cart', true);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error adding item to cart', true);
    });
}

// ✅ Update cart count in menu
function updateCartCount() {
    fetch('/cart_count')
        .then(response => response.json())
        .then(data => {
            const cartBtn = document.getElementById('cart-btn');
            if (cartBtn) {
                cartBtn.textContent = `Cart (${data.count})`;
            }
        })
        .catch(error => console.error('Error:', error));
}

// ✅ Redirect to cart or sign-in
function viewCart() {
    window.location.href = '/cart';
}

// ✅ Attach event listener if element exists
const cartBtn = document.getElementById("cart-btn");
if (cartBtn) {
    cartBtn.addEventListener("click", viewCart);
}

function showNotification(message, isError) {
    const notification = document.getElementById('cartNotification');
    notification.textContent = message;
    notification.className = `cart-notification ${isError ? 'error' : 'success'}`;
    
    // Show notification
    notification.style.opacity = '1';
    notification.style.transform = 'translateY(0)';
    
    // Hide after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-100%)';
    }, 3000);
}
