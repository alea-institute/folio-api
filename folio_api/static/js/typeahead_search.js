/**
 * Typeahead search functionality for FOLIO classes
 * Provides auto-suggestion as users type with proper fallback behavior
 */
(function() {
    // Initialize when document is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeTypeahead();
    });
    
    /**
     * INTERIM FIX: Strip 'folio:' prefix from property labels for human-readable display.
     * Remove this function once https://github.com/alea-institute/FOLIO/pull/5 is merged
     * and folio-python is updated with human-readable rdfs:label values.
     */
    function stripFolioPrefix(label) {
        if (label && label.startsWith('folio:')) {
            return label.substring(6);
        }
        return label || '';
    }

    /**
     * Initializes typeahead search functionality
     */
    function initializeTypeahead() {
        // Try multiple query forms to improve matching (lowercase, titlecase, etc.)
        function searchWithMultipleQueryForms(query, sync, async) {
            // If no query, return empty results
            if (!query) {
                return async([]);
            }
            
            // Original query as entered by user
            let originalQuery = query;
            
            // Lowercase query
            let lowercaseQuery = query.toLowerCase();
            
            // Titlecase query (capitalize first letter of each word)
            let titlecaseQuery = query.split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                .join(' ');
            
            // First try with the original query
            results.search(originalQuery, sync, function(results1) {
                // If we got results, return them
                if (results1 && results1.length > 0) {
                    async(results1);
                    return;
                }
                
                // If original query didn't work, try lowercase
                if (originalQuery !== lowercaseQuery) {
                    results.search(lowercaseQuery, sync, function(results2) {
                        if (results2 && results2.length > 0) {
                            async(results2);
                            return;
                        }
                        
                        // If lowercase didn't work, try titlecase
                        if (originalQuery !== titlecaseQuery && lowercaseQuery !== titlecaseQuery) {
                            results.search(titlecaseQuery, sync, async);
                        } else {
                            async(results2);
                        }
                    });
                } 
                // If original and lowercase are the same, try titlecase
                else if (originalQuery !== titlecaseQuery) {
                    results.search(titlecaseQuery, sync, async);
                } else {
                    async(results1);
                }
            });
        }
        
        const results = new Bloodhound({
            datumTokenizer: function(obj) {
                // Tokenize the label, alt labels, and preferred label
                let tokens = Bloodhound.tokenizers.whitespace(obj.label || '');
                if (obj.alternative_labels) {
                    obj.alternative_labels.forEach(function(alt) {
                        tokens = tokens.concat(Bloodhound.tokenizers.whitespace(alt || ''));
                    });
                }
                if (obj.preferred_label) {
                    tokens = tokens.concat(Bloodhound.tokenizers.whitespace(obj.preferred_label));
                }
                return tokens;
            },
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
                                entity_type: 'Class',
                                alternative_labels: c.alternative_labels && c.alternative_labels.length ? c.alternative_labels.join(', ') : 'None',
                                definition: c.definition || 'No definition available'
                            });
                        }
                    }

                    // Also include properties
                    if (response.properties) {
                        for (let p of response.properties) {
                            if (seen[p.iri]) continue;
                            seen[p.iri] = true;
                            // INTERIM: stripFolioPrefix can be removed once FOLIO PR #5 is merged
                            let label = stripFolioPrefix(p.label || p.preferred_label || (p.alternative_labels && p.alternative_labels[0]) || p.iri);
                            search_results.push({
                                label: label,
                                iri: p.iri,
                                entity_type: 'Property',
                                alternative_labels: p.alternative_labels && p.alternative_labels.length ? p.alternative_labels.join(', ') : 'None',
                                definition: p.definition || 'No definition available'
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
                source: searchWithMultipleQueryForms, // Use our custom search function
                limit: 20, // Increased limit to show more results
                templates: {
                    suggestion: function (data) {
                        // Highlight the matching part of the label if possible
                        let label = data.label;
                        const query = $('#search-input').val().trim().toLowerCase();

                        if (query && query.length > 0 && label) {
                            // Try to highlight the query within the label
                            const labelLower = label.toLowerCase();
                            const index = labelLower.indexOf(query);

                            if (index >= 0) {
                                const beforeMatch = label.substring(0, index);
                                const match = label.substring(index, index + query.length);
                                const afterMatch = label.substring(index + query.length);

                                label = `${beforeMatch}<span class="bg-yellow-200 text-black">${match}</span>${afterMatch}`;
                            }
                        }

                        // Highlight preferred label if it matches the query
                        let prefLabelHtml = '';
                        if (data.preferred_label) {
                            let prefText = data.preferred_label;
                            if (query && query.length > 0) {
                                const prefLower = prefText.toLowerCase();
                                const prefIdx = prefLower.indexOf(query);
                                if (prefIdx >= 0) {
                                    prefText = prefText.substring(0, prefIdx) +
                                        '<span class="bg-yellow-200 text-black">' + prefText.substring(prefIdx, prefIdx + query.length) + '</span>' +
                                        prefText.substring(prefIdx + query.length);
                                }
                            }
                            prefLabelHtml = `<span class="text-sm font-light text-[--color-text-muted] truncate">Preferred: ${prefText}</span>`;
                        }

                        // Type badge
                        const isProperty = data.entity_type === 'Property';
                        const badgeColor = isProperty ? 'bg-teal-100 text-teal-800' : 'bg-blue-100 text-blue-800';
                        const badgeText = isProperty ? 'Property' : 'Class';
                        const badge = `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${badgeColor} ml-2">${badgeText}</span>`;

                        return `
                            <div class="flex flex-col p-2 hover:bg-gray-100">
                                <span class="font-semibold text-[--color-primary]">${label}${badge}</span>
                                <span class="text-sm font-semibold text-[--color-text-secondary] truncate">${data.iri}</span>
                                ${prefLabelHtml}
                                <span class="text-sm font-light text-[--color-text-muted] truncate">Synonyms: ${data.alternative_labels}</span>
                                <span class="text-sm font-light text-[--color-text-muted] truncate">Definition: ${data.definition}</span>
                            </div>
                        `;
                    },
                    notFound: '<div class="p-3 text-center text-[--color-text-muted]">No results found</div>'
                }
            });
    
        // Handle selection with click or keyboard
        $('#search-input').on('typeahead:select', function (ev, suggestion) {
            navigateToIRI(suggestion.iri + "/html");
        });
        
        // Add keyboard accessibility 
        $('#search-input').on('keydown', function(e) {
            if (e.key === 'Enter') {
                const selectedSuggestion = $('.tt-cursor').data('suggestion');
                if (selectedSuggestion) {
                    navigateToIRI(selectedSuggestion.iri + "/html");
                }
            }
        });
    }

    /**
     * Navigates to the specified IRI URL
     * @param {string} iri - The IRI URL to navigate to
     */
    function navigateToIRI(iri) {
        // Navigate to the IRI URL
        window.location.href = iri;
    }
    
    // Make navigation function available globally
    window.navigateToIRI = navigateToIRI;
})();