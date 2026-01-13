'use strict';
// A function to apply formatting to a specific input field
function formatNumberInput(inputId) {
    const input = document.getElementById(inputId);
    if (!input) {
        return;
    }

    function updateValue() {
        let value = input.value.replace(/,/g, ''); // Remove existing commas
        if (value === '' || isNaN(value)) {
            return;
        }
        
        const number = parseFloat(value);
        // Use toLocaleString for robust, internationally-friendly formatting
        input.value = number.toLocaleString('en-US');
    }

    input.addEventListener('input', updateValue);
    // Also format the initial value on page load
    updateValue();
}