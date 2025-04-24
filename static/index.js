document.addEventListener("DOMContentLoaded", function () {
    const orderButton = document.getElementById("orderMeal");

    orderButton.addEventListener("click", function (event) {
        event.preventDefault(); // Prevent default link behavior

        // Show confirmation popup
        if (confirm("Do you want to proceed to the menu?")) {
            window.location.href = "/menu"; // Redirect to menu page
        }
    });
});

    document.addEventListener("DOMContentLoaded", function () {
        fetch('/get_token_balance')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById("token-balance").innerText = data.tokens.toFixed(2);
            }
        })
        .catch(error => console.error("Error fetching token balance:", error));
    });

    
