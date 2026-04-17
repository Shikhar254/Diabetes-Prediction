function calculateBMI() {
    let height = document.getElementById("height").value;
    let weight = document.getElementById("weight").value;

    if (height === "" || weight === "") {
        alert("Please enter both Height and Weight!");
        return;
    }

    height = height / 100; // convert cm to meters
    let bmi = weight / (height * height);

    document.getElementById("bmi").value = bmi.toFixed(2);
}
function toggleSkinThickness() {
    let checkbox = document.getElementById("unknownSkin");
    let input = document.getElementById("skinThickness");

    if (checkbox.checked) {
        input.value = 20;  // average value
        input.readOnly = true;
    } else {
        input.readOnly = false;
        input.value = "";
    }
}

function toggleInsulin() {
    let checkbox = document.getElementById("unknownInsulin");
    let input = document.getElementById("insulin");

    if (checkbox.checked) {
        input.value = 80; // average value 
        input.readOnly = true;
    } else {
        input.readOnly = false;
        input.value = "";
    }
}

function setDPFValue() {
    let dropdown = document.getElementById("familyHistory");
    let dpfHidden = document.getElementById("dpfValue");
    let dpfDisplay = document.getElementById("dpfDisplay");

    dpfHidden.value = dropdown.value;
    dpfDisplay.innerText = dropdown.value;
}