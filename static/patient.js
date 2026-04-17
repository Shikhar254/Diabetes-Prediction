function toggleNoneSymptom() {
    let noneBox = document.getElementById("noneSymptom");
    let symptoms = document.querySelectorAll(".symptomCheck");

    if (noneBox.checked) {
        symptoms.forEach((box) => {
            box.checked = false;
        });
    }
}

document.addEventListener("DOMContentLoaded", function () {
    let symptoms = document.querySelectorAll(".symptomCheck");
    let noneBox = document.getElementById("noneSymptom");

    symptoms.forEach((box) => {
        box.addEventListener("change", function () {
            if (box.checked) {
                noneBox.checked = false;
            }
        });
    });
});

function validateSymptoms() {
    let noneBox = document.getElementById("noneSymptom");
    let symptoms = document.querySelectorAll(".symptomCheck");
    let errorBox = document.getElementById("symptomError");

    let checked = false;

    if (noneBox.checked) {
        checked = true;
    }

    symptoms.forEach((box) => {
        if (box.checked) {
            checked = true;
        }
    });

    if (!checked) {
        errorBox.style.display = "block";
        return false;
    } else {
        errorBox.style.display = "none";
        return true;
    }
}