document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("waitlistForm");
    const emailInput = document.getElementById("emailInput");
    const confirmMsg = document.getElementById("confirmMsg");
    const confirmEmail = document.getElementById("confirmEmail");
    const ctaBtn = document.getElementById("ctaBtn");
    const ctaConfirm = document.getElementById("ctaConfirm");

    function markSubmitted(email) {
        form.hidden = true;
        confirmEmail.textContent = email;
        confirmMsg.hidden = false;
        ctaBtn.hidden = true;
        ctaConfirm.hidden = false;
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!emailInput.value) return;
        markSubmitted(emailInput.value);
    });

    ctaBtn.addEventListener("click", () => {
        emailInput.scrollIntoView({ behavior: "smooth", block: "center" });
        emailInput.focus();
    });
});
