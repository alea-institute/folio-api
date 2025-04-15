function copyIRI() {
    // Get the IRI element that contains the actual IRI value
    const iriElement = document.getElementById('iri-value');
    if (!iriElement) {
        console.error('IRI element not found');
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
            
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}
