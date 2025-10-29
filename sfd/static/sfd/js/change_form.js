// core/static/core/js/admin_fk_disable.js

window.addEventListener('load', function() {
    // Find all foreign key dropdown wrappers on the page
    const wrappers = document.querySelectorAll('.related-widget-wrapper');

    wrappers.forEach(wrapper => {
        const select = wrapper.querySelector('select');
        // The "view" link is identified by the 'view-related' class in modern Django
        const viewLink = wrapper.querySelector('.view-related');

        // If we can't find a select or a view link, skip this widget
        if (!select || !viewLink) {
            return;
        }

        // A function to toggle the link's active state
        const toggleLinkState = () => {
            if (select.value) {
                // If a value is selected, make the link active
                viewLink.style.pointerEvents = 'auto';
                viewLink.style.opacity = '1';
                viewLink.removeAttribute('tabindex'); // Make it focusable again
            } else {
                // If no value is selected ("---------"), disable the link
                viewLink.style.pointerEvents = 'none';
                viewLink.style.opacity = '0.4';
                viewLink.setAttribute('tabindex', '-1'); // Remove from tab navigation
            }
        };

        // Run the function once on page load to set the initial state
        toggleLinkState();

        // Add an event listener to run the function every time the dropdown changes
        select.addEventListener('change', toggleLinkState);    
    });
});