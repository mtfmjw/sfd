/**
 * Person Search JavaScript Functions
 * 
 * This file contains JavaScript functions for handling person form
 * search popup functionality, including postcode and municipality selection.
 */

/**
 * Sets person data from search popup.
 * 
 * This function is called by the search popup window to pass
 * selected postcode and municipality data back to the person form.
 * 
 * @param {Object} data - The selected data from search popup
 * @param {string} data.postcode - Selected postcode value
 * @param {string} data.municipality - Selected municipality value
 * @param {string} data.municipality_id - Selected municipality object ID
 * @param {string} data.address_detail - Selected address detail
 */
function setPersonData(data) {
    // console.log('Received person data:', data);
    
    // Set postcode field
    if (data.postcode) {
        // Update the search display field
        const postcodeSearchField = document.getElementById('id_postcode_search');
        if (postcodeSearchField) {
            // Format postcode with dash (XXX-XXXX)
            const formattedPostcode = data.postcode.length === 7 ? 
                data.postcode.substring(0, 3) + '-' + data.postcode.substring(3) : 
                data.postcode;
            postcodeSearchField.value = formattedPostcode;
        }
        
        // Update the hidden postcode field with the postcode object ID
        const postcodeHiddenField = document.getElementById('id_postcode');
        if (postcodeHiddenField && data.postcode_id) {
            postcodeHiddenField.value = data.postcode_id;
        }
    }
    
    // Set municipality field
    if (data.municipality) {
        // Update the municipality display field
        const municipalityDisplayField = document.getElementById('id_municipality_display');
        if (municipalityDisplayField) {
            municipalityDisplayField.value = data.municipality;
        }
        
        // Update the hidden municipality field with the municipality object ID
        const municipalityHiddenField = document.getElementById('id_municipality');
        if (municipalityHiddenField && data.municipality_id) {
            municipalityHiddenField.value = data.municipality_id;
        }
    }

    // Set address detail field
    if (data.address_detail) {
        const addressDetailField = document.getElementById('id_address_detail');
        if (addressDetailField) {
            addressDetailField.value = data.address_detail;
        }
    }

    console.log('Person data fields updated successfully');
}


// Helper function to select record from a table row element
function selectRecordFromRow(rowElement) {
    const postcode = rowElement.getAttribute('data-postcode') || '';
    const municipality = rowElement.getAttribute('data-municipality') || '';
    const municipality_id = rowElement.getAttribute('data-municipality-id') || '';
    const address_detail = rowElement.getAttribute('data-address-detail') || '';

    // Pass the selected data back to the parent window
    if (typeof window.setPersonData === 'function') {
    window.setPersonData({
        postcode: postcode,
        municipality: municipality,
        municipality_id: municipality_id,
        address_detail: address_detail
    });
    }
    
    // Close the popup modal
    if (typeof window.closePopupModalDynamic === 'function') {
    window.closePopupModalDynamic();
    } else {
    window.close();
    }
}

// Function to select a record and pass data back to parent window
function selectRecord() {
    const selectedRadio = document.querySelector('input[name="selected_pk"]:checked');
    
    if (!selectedRadio) {
        alert('{% translate "Please select a record first." %}');
        return;
    }
    
    // Find the parent row and use the helper function
    const rowElement = selectedRadio.closest('tr');
    if (rowElement) {
    selectRecordFromRow(rowElement);
    }
}

/**
 * Opens popup modal for search functionality.
 * 
 * This function is called when a search button is clicked to open
 * the search popup modal window.
 */
function openPopupModalDynamic() {
    // This function should be implemented to show the modal
    // It might already exist in your admin interface
    console.log('Opening popup modal for search');
}

/**
 * Closes popup modal after selection.
 * 
 * This function is called to close the search popup modal
 * after a selection has been made.
 */
function closePopupModalDynamic() {
    // This function should be implemented to close the modal
    // It might already exist in your admin interface
    console.log('Closing popup modal');
}