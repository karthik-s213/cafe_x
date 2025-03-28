document.getElementById('signinForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('signinEmail').value;
    const password = document.getElementById('signinPassword').value;

    try {
        const response = await fetch('/signin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();
        if (result.success) {
            window.location.href = "/";  // ✅ Redirect to profile after sign-in
        } else {
            alert(result.error);
        }
    } catch (error) {
        console.error("Error:", error);
    }
});
