document.getElementById("pay-btn").addEventListener("click", function () {
    const amountInr = document.getElementById("amount").value;

    fetch("/process_payment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount_inr: amountInr })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`✅ Payment Successful! ${data.tokens_added} Tokens Added.`);
            window.location.href = data.redirect_url;  // Redirect to token page
        } else {
            alert(`❌ Payment Failed: ${data.error}`);
        }
    });
});
