document.getElementById('signupForm').addEventListener('submit', async function (e) {
    e.preventDefault();  // Prevent default form submission

    const formData = new FormData(this);
    
    try {
        const response = await fetch('/signup', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.success) {
            window.location.href = "/cart";  // ✅ Redirect to cart after signup
        } else {
            alert(result.error); // Show error message
        }
    } catch (error) {
        console.error("Error:", error);
    }
});