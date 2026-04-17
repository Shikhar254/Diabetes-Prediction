function togglePassword() {
    let passwordField = document.getElementById("adminPassword");
    let icon = document.getElementById("eyeIcon");
    let msg = document.getElementById("passMsg");

    // If empty → show warning and stop
    if (passwordField.value.trim() === "") {
        msg.style.display = "block";

        setTimeout(() => {
            msg.style.display = "none";
        }, 2000);

        return;
    }

    // Hide warning if password exists
    msg.style.display = "none";

    // Toggle show/hide
    if (passwordField.type === "password") {
        passwordField.type = "text";
        icon.innerText = "Hide";
    } else {
        passwordField.type = "password";
        icon.innerText = "Show";
    }
}