/**
 * Copies the IRI value to the clipboard and provides visual feedback
 */
function copyIRI() {
    // Get the IRI element that contains the actual IRI value
    const iriElement = document.getElementById('iri-value');
    if (!iriElement) {
        // Display a user-facing error instead of console.error
        const errorNotification = document.createElement('div');
        errorNotification.className = 'error-notification';
        errorNotification.textContent = 'IRI element not found';
        document.body.appendChild(errorNotification);
        
        setTimeout(() => {
            document.body.removeChild(errorNotification);
        }, 3000);
        return;
    }
    
    // Get the IRI value (either from the text content or the title attribute which has the full IRI)
    const iri = iriElement.getAttribute('title') || iriElement.textContent;
    
    // Copy to clipboard
    navigator.clipboard.writeText(iri).then(() => {
        // Get the button that was clicked
        const button = document.querySelector('button.copy-button');
        if (button) {
            const originalText = button.textContent;
            button.textContent = '✓';
            
            // Add aria notification for screen readers
            const notification = document.createElement('div');
            notification.setAttribute('aria-live', 'polite');
            notification.className = 'sr-only';
            notification.textContent = 'IRI copied to clipboard';
            document.body.appendChild(notification);
            
            // Reset button text after 2 seconds
            setTimeout(() => {
                button.textContent = originalText;
                
                // Clean up notification
                document.body.removeChild(notification);
            }, 2000);
        }
    }).catch(_err => {
        // Show error to user - removed console.error for production
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.textContent = 'Failed to copy to clipboard';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    });
}