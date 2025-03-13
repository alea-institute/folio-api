// Typeahead initialization
$(document).ready(function () {
    var results = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('label'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/search/prefix?query=%QUERY',
            wildcard: '%QUERY',
            transform: function (response) {
                // track seen IRIs
                let seen = {};
                let search_results = [];

                for (let c of response.classes) {
                    // check if we've seen it already
                    if (seen[c.iri]) {
                        // skip it
                    } else {
                        seen[c.iri] = true;

                        let label = c.label || c.preferred_label || (c.alternative_labels && c.alternative_labels[0]) || c.iri;
                        search_results.push({
                            label: label,
                            iri: c.iri,
                            alternative_labels: c.alternative_labels.join(', '),
                            definition: c.definition || 'No definition available'
                        });
                    }
                }

                return search_results;
            }
        }
    });

    $('#search-input').typeahead({
            hint: true,
            highlight: true,
            minLength: 1
        },
        {
            name: 'results',
            display: 'label',
            source: results,
            limit: 10,
            templates: {
                suggestion: function (data) {
                    return `
                        <div class="flex flex-col">
                            <span class="font-semibold text-[--color-primary]">${data.label}</span>
                            <span class="text-sm font-semibold text-[--color-text-secondary] truncate">${data.iri}</span>
                            <span class="text-sm font-light text-[--color-text-muted] truncate">Synonyms: ${data.alternative_labels}</span>
                            <span class="text-sm font-light text-[--color-text-muted] truncate">Definition: ${data.definition}</span>
                        </div>
                    `;
                },
                notFound: '<div class="p-3 text-center text-[--color-text-muted]">No results found</div>'
            }
        });

    // Handle selection
    $('#search-input').on('typeahead:select', function (ev, suggestion) {
        navigateToIRI(suggestion.iri + "/html");
    });
});

function navigateToIRI(iri) {
    // Navigate to the IRI URL
    window.location.href = iri;
}
