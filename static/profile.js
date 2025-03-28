function fetchTokenBalance() {
    fetch('/get_token_balance')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById("token-balance").innerText = data.tokens.toFixed(2);
        }
    })
    .catch(error => console.error("Error fetching token balance:", error));
}

document.addEventListener("DOMContentLoaded", fetchTokenBalance);
    // ✅ Handle Quick Sign-In Form Submission
    if (quickSigninForm) {
        quickSigninForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            const email = document.getElementById("signin-email").value;
            const password = document.getElementById("signin-password").value;

            try {
                const response = await fetch('/signin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, password: password })
                });

                const result = await response.json();
                if (result.success) {
                    window.location.href = "/profile";  // ✅ Redirect to Profile Page after sign-in
                } else {
                    alert("Invalid email or password");
                }
            } catch (error) {
                console.error("Error:", error);
            }
        });
    }
});
