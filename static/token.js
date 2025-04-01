document.addEventListener("DOMContentLoaded", function () {
    fetch('/get_token_balance')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById("token-balance").innerText = data.tokens;
        }
    });
});

function purchaseTokens() {
    let amountInr = document.getElementById("amount-inr").value;

    fetch('/process_patments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: amountInr })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Tokens Purchased: " + data.tokens_purchased);
            document.getElementById("token-balance").innerText = data.tokens_purchased;
        } else {
            alert(data.error);
        }
    });
}


// ✅ Ensure real-time update when "Use Tokens to Buy Items" is clicked
document.getElementById("purchase-btn").addEventListener("click", function () {
    fetch('/get_cart_total')  // ✅ Get total price from the database
    .then(response => response.json())
    .then(cartData => {
        if (!cartData.success) {
            document.getElementById("message").innerText = "❌ Error fetching cart total.";
            return;
        }

        const totalPrice = cartData.total_price;  // ✅ Updated total price from backend

        fetch('/get_token_balance')
        .then(response => response.json())
        .then(data => {
            const availableTokens = data.tokens;  // ✅ Get updated tokens from database

            if (availableTokens >= totalPrice) {
                fetch("/pay_with_tokens", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ total_price: totalPrice })  // ✅ Send correct total price
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        document.getElementById("message").innerText = `✅ Purchase successful! Remaining Tokens: ${result.remaining_tokens}`;
                        
                        // ✅ Force refresh token balance and cart total immediately
                        fetchTokenBalanceAndCart();
                    } else {
                        document.getElementById("message").innerText = `❌ ${result.error}`;
                    }
                })
                .catch(error => console.error("Error processing payment:", error));
            } else {
                document.getElementById("message").innerText = "❌ Not enough tokens!";
            }
        })
        .catch(error => console.error("Error fetching token balance:", error));
    })
    .catch(error => console.error("Error fetching cart total:", error));
});

// ✅ Refresh token balance and cart on page load
document.addEventListener("DOMContentLoaded", fetchTokenBalanceAndCart);
