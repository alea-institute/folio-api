function copyIRI() {
    {
        const iri = document.querySelector('dd a').href;
        navigator.clipboard.writeText(iri).then(() => {
            {
                const button = document.querySelector('button');
                const originalText = button.textContent;
                button.textContent = '✓';

                setTimeout(() => {
                    {
                        button.textContent = originalText;
                    }
                }, 2000);
            }
        }).catch(err => {
            {
                console.error('Failed to copy: ', err);
            }
        });
    }
}
