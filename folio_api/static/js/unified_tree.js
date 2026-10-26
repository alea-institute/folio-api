/**
 * Unified Tree JavaScript — Combined class + property tree in one view.
 * Parameterized by section config so both types share the same tree logic.
 */

// Section configuration — maps each entity type to its API endpoints and DOM ids
const SECTIONS = {
    class: {
        rootListId: 'class-tree-root',
        sectionId: 'class-section',
        countId: 'class-count',
        treeDataEndpoint: '/taxonomy/tree/data',
        nodeDataEndpoint: '/taxonomy/tree/node/',
        detailsEndpoint: '/taxonomy/class-details/',
        searchEndpoint: '/taxonomy/tree/search',
        pathEndpoint: '/taxonomy/tree/path/',
        type: 'class'
    },
    property: {
        rootListId: 'property-tree-root',
        sectionId: 'property-section',
        countId: 'property-count',
        treeDataEndpoint: '/properties/tree/data',
        nodeDataEndpoint: '/properties/tree/node/',
        detailsEndpoint: '/properties/property-details/',
        searchEndpoint: '/properties/tree/search',
        pathEndpoint: '/properties/tree/path/',
        type: 'property'
    }
};

const explorerPage = document.querySelector('[data-ontology]');
const ontologyKey = explorerPage ? explorerPage.dataset.ontology : 'folio';
const treeBlocked = explorerPage && explorerPage.dataset.treeState === 'blocked';

function ontologyUrl(value) {
    const url = new URL(value, window.location.origin);
    if (ontologyKey === 'canon') url.searchParams.set('ontology', 'canon');
    else url.searchParams.delete('ontology');
    return url;
}

// Cache and state
const nodeDataCache = new Map();
const MAX_CACHE_SIZE = 200;
let lastSearchTrees = { class: null, property: null };
let searchGeneration = 0;
let revealGeneration = 0;

const HISTORY_KEY = 'folioExplorer';
let committedQuery = '';
let navigationBusy = false;
let restoringHistory = false;
let selectionGeneration = 0;
let detailsPending = false;
let restoreRequests = null;
let historySaveTimer;
const branchLoads = new WeakMap();

function occurrencePath(node) {
    return $(node).parents('.tree-node').get().reverse().concat($(node).get())
        .map(item => item.dataset.id);
}

function findOccurrence(type, path) {
    let list = $('#' + SECTIONS[type].rootListId);
    let node = $();
    for (const id of path) {
        node = list.children('.tree-node').filter(function() { return this.dataset.id === id; }).first();
        if (!node.length) return node;
        list = node.children('.children-container');
    }
    return node;
}

function occurrenceContainer(type, path) {
    return path.length ? findOccurrence(type, path).children('.children-container')
        : $('#' + SECTIONS[type].rootListId);
}

function captureSelection() {
    const selected = $('.tree-node.selected').first();
    return selected.length ? { type: selected.attr('data-type'), path: occurrencePath(selected) } : null;
}

function captureView() {
    const sections = {};
    for (const type of Object.keys(SECTIONS)) {
        const root = $('#' + SECTIONS[type].rootListId);
        const loaded = [];
        const expanded = [];
        const siblings = [];
        root.add(root.find('.children-container')).each(function() {
            const list = $(this);
            const path = list.parent().hasClass('tree-node') ? occurrencePath(list.parent()) : [];
            if (this.dataset.loaded === 'true') loaded.push(path);
            const row = list.children('.siblings-row');
            if (row.data('siblingsLoaded')) siblings.push({ path, open: !!row.data('siblingsOpen') });
        });
        root.find('.tree-node.expanded').each(function() {
            const children = $(this).children('.children-container');
            if (children.children('.tree-node').length || children[0]?.dataset.loaded === 'true') {
                expanded.push(occurrencePath(this));
            }
        });
        sections[type] = { open: root[0].style.display !== 'none', loaded, expanded, siblings };
    }
    return { version: 1, query: committedQuery, sections, selection: captureSelection() };
}

function savedView(state) {
    const view = state && state[HISTORY_KEY];
    const path = value => Array.isArray(value) && value.every(id => typeof id === 'string' && id.length > 0);
    if (!view || view.version !== 1 || typeof view.query !== 'string' ||
        (view.query.length > 0 && view.query.length < 2) || !view.sections) return null;
    for (const type of Object.keys(SECTIONS)) {
        const section = view.sections[type];
        if (!section || typeof section.open !== 'boolean' ||
            !Array.isArray(section.loaded) || !section.loaded.every(path) ||
            !Array.isArray(section.expanded) || !section.expanded.every(p => path(p) && p.length) ||
            !Array.isArray(section.siblings) ||
            !section.siblings.every(row => row && path(row.path) && typeof row.open === 'boolean')) return null;
    }
    const selection = view.selection;
    if (selection !== null && (!selection || !Object.hasOwn(SECTIONS, selection.type) ||
        !path(selection.path) || !selection.path.length)) return null;
    return view;
}

function historyNotice(message, retry) {
    let notice = document.getElementById('tree-history-notice');
    if (!notice) {
        notice = document.createElement('div');
        notice.id = 'tree-history-notice';
        notice.className = 'p-2 text-sm';
        notice.setAttribute('role', 'status');
        document.getElementById('explore-tree').before(notice);
    }
    notice.textContent = message;
    notice.hidden = !message;
    if (retry) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'tree-retry';
        button.textContent = 'Retry';
        button.addEventListener('click', retry);
        notice.append(' ', button);
    }
}

function selectionUrl(selection) {
    const url = ontologyUrl(window.location.href);
    url.searchParams.delete('node');
    url.searchParams.delete('type');
    if (selection) {
        url.searchParams.set('node', selection.path[selection.path.length - 1]);
        url.searchParams.set('type', selection.type);
    }
    return url;
}

function writeView(mode, url = ontologyUrl(window.location.href)) {
    if (navigationBusy || restoringHistory) return;
    const view = captureView();
    if (JSON.stringify(savedView(history.state)) === JSON.stringify(view) && url.href === location.href) return;
    const envelope = history.state && typeof history.state === 'object' ? history.state : {};
    try {
        history[mode + 'State']({ ...envelope, [HISTORY_KEY]: view }, '', url);
    } catch (_) {
        historyNotice('This view could not be saved in browser history. You can keep browsing.');
    }
}

function saveViewSoon(generation = searchGeneration) {
    if (navigationBusy || restoringHistory) return;
    clearTimeout(historySaveTimer);
    historySaveTimer = setTimeout(() => {
        if (generation === searchGeneration) writeView('replace');
    }, 0);
}

function beginNavigation(restoring = false) {
    if (!restoring) writeView('replace');
    clearTimeout(historySaveTimer);
    $('.children-container').each(function() {
        if ($(this).children('.loading-indicator').length && !$(this).children('.tree-node').length) {
            setNodeExpanded($(this).parent('.tree-node'), false);
        }
    });
    searchGeneration++;
    revealGeneration++;
    selectionGeneration++;
    navigationBusy = true;
    restoringHistory = restoring || restoringHistory;
    restoreRequests = restoring ? new Map() : null;
    historyNotice('');
    document.getElementById('explore-tree').setAttribute('aria-busy', 'true');
    document.getElementById('explore-tree').inert = true;
    document.dispatchEvent(new CustomEvent('entity:navigation-start'));
    return searchGeneration;
}

function finishNavigation(generation, mode, url) {
    if (generation !== searchGeneration) return;
    navigationBusy = false;
    restoringHistory = false;
    restoreRequests = null;
    document.getElementById('explore-tree').setAttribute('aria-busy', 'false');
    document.getElementById('explore-tree').inert = false;
    if (mode) writeView(mode, url);
}

function notifySelection(node) {
    document.dispatchEvent(new CustomEvent('entity:selected', {
        detail: node && node.length ? { iri: node.attr('data-id'), type: node.attr('data-type') }
            : { iri: null, type: null }
    }));
}

function clearSelection() {
    selectionGeneration++;
    detailsPending = false;
    $('.tree-node.selected').removeClass('selected');
    document.getElementById('class-details').innerHTML = '<div class="p-4 text-gray-500"><h3>Select an item</h3><p>Choose a class or property from the tree to view its details</p></div>';
}

function resumeSelection(generation) {
    const node = $('.tree-node.selected').first();
    if (node.length && detailsPending) loadDetails(node.attr('data-id'), node.attr('data-type'), generation);
    notifySelection(node);
}

async function childData(nodeId, sectionType, generation) {
    const key = sectionType + ':' + nodeId;
    const cache = generation === searchGeneration ? restoreRequests : null;
    if (cache && cache.has(key)) return cache.get(key);
    const request = fetch(ontologyUrl(SECTIONS[sectionType].treeDataEndpoint + '?node_id=' + encodeURIComponent(nodeId)))
        .then(async response => {
            if (!response.ok) throw new Error('Could not load branch');
            const children = await response.json();
            if (!Array.isArray(children)) throw new Error('Invalid child list');
            return children;
        });
    if (cache) cache.set(key, request);
    return request;
}

function setNodeExpanded(node, expanded) {
    node.toggleClass('expanded', expanded).toggleClass('collapsed', !expanded);
    node.children('.node-content').find('.expand-icon').toggleClass('expanded', expanded);
    node.children('.children-container').stop(true, true).toggle(expanded);
}

// ---------- Cache helper ----------
async function getNodeData(nodeId, sectionType) {
    const cacheKey = sectionType + ':' + nodeId;
    if (nodeDataCache.has(cacheKey)) return nodeDataCache.get(cacheKey);

    const cfg = SECTIONS[sectionType];
    const extractedId = extractIdFromIri(nodeId);
    const response = await fetch(ontologyUrl(cfg.nodeDataEndpoint + encodeURIComponent(extractedId)));
    if (!response.ok) throw new Error('Failed to fetch node data: ' + response.status);
    const data = await response.json();

    nodeDataCache.set(cacheKey, data);
    nodeDataCache.set(sectionType + ':' + extractedId, data);

    // Prune cache
    if (nodeDataCache.size > MAX_CACHE_SIZE) {
        const keys = [...nodeDataCache.keys()];
        const deleteCount = Math.ceil(MAX_CACHE_SIZE * 0.2);
        for (let i = 0; i < deleteCount; i++) nodeDataCache.delete(keys[i]);
    }
    return data;
}

// ---------- IRI helpers ----------
function extractIdFromIri(iri) {
    if (ontologyKey === 'canon' || !iri || !iri.startsWith('http')) return iri;
    const parts = iri.split('/').filter(p => p.trim().length > 0);
    return parts.length > 0 ? parts[parts.length - 1] : iri;
}

// ---------- Section collapse/expand ----------
function setupSectionHeaders() {
    document.querySelectorAll('.section-header').forEach(header => {
        header.addEventListener('click', () => {
            if (navigationBusy) return;
            const sectionType = header.dataset.section;
            const cfg = SECTIONS[sectionType];
            const rootList = document.getElementById(cfg.rootListId);
            const chevron = header.querySelector('.section-chevron');
            if (rootList.style.display === 'none') {
                rootList.style.display = '';
                chevron.classList.remove('collapsed');
            } else {
                rootList.style.display = 'none';
                chevron.classList.add('collapsed');
            }
            saveViewSoon();
        });
    });
}

// ---------- Tree node rendering ----------
function renderTreeNode(node, container, sectionType) {
    const hasChildren = node.children;
    const nodeClass = hasChildren ? 'has-children collapsed' : '';
    const expandIcon = hasChildren
        ? '<span class="expand-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"></polyline></svg></span>'
        : '<span class="leaf-indicator"><span class="leaf-dot"></span></span>';

    const li = $(`
        <li class="tree-node ${nodeClass}" data-id="${node.id}" data-type="${sectionType}">
            <div class="node-content">
                ${expandIcon}
                <span class="node-label">${node.text}</span>
            </div>
            ${hasChildren ? '<ul class="children-container" style="display:none;"></ul>' : ''}
        </li>
    `);
    container.append(li);
}

function renderLoadedChildren(nodeId, list, sectionType, children) {
    list.children('.tree-node, .tree-error-row').remove();
    children.forEach(node => renderTreeNode(node, list, sectionType));
    list.attr('data-loaded', 'true');
    if (nodeId === '#') document.getElementById(SECTIONS[sectionType].countId).textContent = children.length;
    setupNodeClickHandlers();
}

function loadTreeNodes(nodeId, container, sectionType, { generation = searchGeneration, strict = false } = {}) {
    const list = $(container);
    if (!list.length) return Promise.resolve(false);
    if (list[0].dataset.loaded === 'true') return Promise.resolve(true);
    const pending = branchLoads.get(list[0]);
    if (pending?.generation === generation) return pending.promise;
    const promise = (async () => {
        const indicator = $('<li class="loading-indicator"><span>Loading...</span></li>').appendTo(list);
        try {
            const children = await childData(nodeId, sectionType, generation);
            if (generation !== searchGeneration) return false;
            renderLoadedChildren(nodeId, list, sectionType, children);
            return true;
        } catch (error) {
            if (generation !== searchGeneration) return false;
            if (strict) throw error;
            list.append('<li class="tree-error-row">Error loading. Try again.</li>');
            return false;
        } finally {
            indicator.remove();
        }
    })();
    const load = { generation, promise };
    branchLoads.set(list[0], load);
    const release = () => { if (branchLoads.get(list[0]) === load) branchLoads.delete(list[0]); };
    promise.then(release, release);
    return promise;
}

// ---------- Retained search context ----------
function isSearchFilterActive() {
    return document.getElementById('explore-search-input')?.dataset.filtering === 'true';
}

// Accept either a native container or a jQuery wrapper, as callers use both.
function mergeChildrenIntoContainer(container, sectionType, fetchedChildren) {
    const list = $(container);
    const existingIds = new Set(list.children('.tree-node').map(function() {
        return this.dataset.id;
    }).get());

    fetchedChildren.forEach(node => {
        const id = String(node.id);
        if (existingIds.has(id)) return;
        const li = document.createElement('li');
        li.className = 'tree-node tree-node-context' + (node.children ? ' has-children collapsed' : '');
        li.dataset.id = id;
        li.dataset.type = sectionType;
        const content = document.createElement('div');
        content.className = 'node-content';
        content.innerHTML = node.children
            ? '<span class="expand-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"></polyline></svg></span>'
            : '<span class="leaf-indicator"><span class="leaf-dot"></span></span>';
        const label = document.createElement('span');
        label.className = 'node-label';
        label.textContent = node.text;
        content.appendChild(label);
        li.appendChild(content);
        if (node.children) {
            const children = document.createElement('ul');
            children.className = 'children-container';
            children.style.display = 'none';
            li.appendChild(children);
        }

        const sortLabel = String(node.text).toLowerCase();
        const next = list.children('.tree-node').get().find(existing => {
            // Preferred-label annotations and query highlighting are presentation only.
            const existingLabel = $(existing).children('.node-content').children('.node-label').clone();
            existingLabel.find('.preflabel-annotation').remove();
            return sortLabel.localeCompare(existingLabel.text().trim().toLowerCase()) < 0;
        });
        if (next) next.before(li);
        else list.append(li);
        existingIds.add(id);
    });

    refreshSiblingsRow(list, sectionType);
    setupNodeClickHandlers();
}

function siblingsCountLabel(row, count) {
    const text = '+' + count + ' siblings';
    return { text, ariaLabel: text + ' ' + row.attr('data-branch-label') };
}

function refreshSiblingsRow(container, sectionType, nodeId) {
    const list = $(container);
    const row = list.children('.siblings-row');
    if (!row.length) return;
    if (nodeId === undefined) nodeId = list.parent('.tree-node').attr('data-id') || '#';
    const tree = lastSearchTrees[sectionType];
    let hidden;
    if (nodeId === '#' && tree && Number.isInteger(tree.hidden_root_count)) {
        // Search roots can include promoted nodes outside the full-tree root list.
        const originalRoots = new Set((tree.root_nodes || []).map(String));
        const revealedRoots = list.children('.tree-node').get().filter(node => !originalRoots.has(node.dataset.id)).length;
        hidden = tree.hidden_root_count - revealedRoots;
    } else {
        const node = tree && tree.nodes && tree.nodes[nodeId];
        if (node && Number.isInteger(node.child_count)) {
            hidden = node.child_count - list.children('.tree-node').length;
        }
    }
    // Keep row-initiated reveals hideable, including after a successful Retry.
    if (row.data('siblingsRequested') && list.children('.tree-node-context').length) {
        if (!row.data('siblingsLoaded')) showSiblingsRowContext(row);
        row.data('siblingsLoaded', true);
        list.append(row);
        return;
    }
    if (hidden !== undefined) {
        hidden = Math.max(0, hidden);
        if (hidden === 0) { row.remove(); return; }
        // Preserve the native control and its handlers.
        const control = row.find('button').first();
        const label = siblingsCountLabel(row, hidden);
        (control.length ? control : row).text(label.text);
        if (control.length) control.attr('aria-label', label.ariaLabel);
    }
    list.append(row);
}

async function fetchAndMergeChildren(nodeId, container, sectionType,
        { control, generation = searchGeneration, strict = false } = {}) {
    const stillSearching = () => generation === searchGeneration && isSearchFilterActive();
    const list = $(container);
    const activatedControl = $(control);
    list.children('.tree-error-row').remove();
    const indicator = $('<li class="loading-indicator"><span>Loading...</span></li>').appendTo(list);
    activatedControl.prop('disabled', true).data('loadGeneration', generation);
    try {
        const children = await childData(nodeId, sectionType, generation);
        if (!stillSearching()) return false;
        mergeChildrenIntoContainer(list, sectionType, children);
        list.attr('data-loaded', 'true');
        return true;
    } catch (error) {
        if (!stillSearching()) return false;
        if (strict) throw error;
        const row = $('<li class="tree-error-row"><span>Error loading. </span><button type="button" class="tree-retry">Retry</button></li>');
        row.find('button').on('click', async function(event) {
            event.stopPropagation();
            if (navigationBusy) return;
            const retryGeneration = searchGeneration;
            const success = await fetchAndMergeChildren(nodeId, list, sectionType, { control });
            if (success && retryGeneration === searchGeneration) saveViewSoon(retryGeneration);
        });
        list.append(row);
        refreshSiblingsRow(list, sectionType, nodeId);
        return false;
    } finally {
        indicator.remove();
        if (activatedControl.data('loadGeneration') === generation) activatedControl.prop('disabled', false);
    }
}

// Native sibling controls retain direct context children so reopening never fetches.
function appendSiblingsRow(container, sectionType, parentId, parentLabel, hidden) {
    if (hidden <= 0) return;
    const row = $('<li class="siblings-row"></li>').attr({
        'data-parent-id': parentId,
        'data-type': sectionType,
        'data-branch-label': parentId === '#' ? 'at the top level' : 'under ' + parentLabel
    });
    const label = siblingsCountLabel(row, hidden);
    $('<button type="button" class="siblings-toggle"></button>').attr({
        'aria-expanded': 'false',
        'aria-label': label.ariaLabel
    }).text(label.text).appendTo(row);
    $(container).append(row);
}

// Reveal retained siblings before selecting a node hidden by this row.
function showSiblingsRowContext(row) {
    row = $(row);
    row.parent().children('.tree-node-context').show();
    row.data('siblingsOpen', true);
    row.children('.siblings-toggle').text('Hide siblings').attr({
        'aria-expanded': 'true',
        'aria-label': 'Hide siblings ' + row.attr('data-branch-label')
    });
}

function hideSiblingsRowContext(row) {
    const context = row.parent().children('.tree-node-context');
    context.hide();
    row.data('siblingsOpen', false);
    const label = siblingsCountLabel(row, context.length);
    row.children('.siblings-toggle').text(label.text).attr({ 'aria-expanded': 'false', 'aria-label': label.ariaLabel });
}

async function toggleSiblingsRow(row) {
    if (navigationBusy) return;
    const generation = searchGeneration;
    const button = row.children('.siblings-toggle');
    if (button.prop('disabled')) return;
    let success = true;
    try {
        if (row.data('siblingsOpen')) {
            hideSiblingsRowContext(row);
        } else if (row.data('siblingsLoaded')) {
            showSiblingsRowContext(row);
        } else {
            row.data('siblingsRequested', true);
            success = await fetchAndMergeChildren(row.attr('data-parent-id'), row.parent(), row.attr('data-type'), { control: button, generation });
            if (success && generation === searchGeneration) {
                row.data('siblingsLoaded', true);
                showSiblingsRowContext(row);
            }
        }
    } finally {
        if (generation === searchGeneration) {
            if (success) saveViewSoon(generation);
        }
    }
}

// ---------- Click handlers ----------
function setupNodeClickHandlers() {
    try {
        $('.siblings-toggle').off('click.unified').on('click.unified', function(e) {
            e.stopPropagation();
            toggleSiblingsRow($(this).closest('.siblings-row'));
        });
        $('.expand-icon').off('click.unified').on('click.unified', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length) toggleNode(li);
        });
        $('.node-content').off('click.unified').on('click.unified', function() {
            const li = $(this).closest('li');
            if (li.length) selectNode(li);
        });
        $('.node-content').off('dblclick.unified').on('dblclick.unified', function(e) {
            e.stopPropagation();
            const li = $(this).closest('li');
            if (li.length && li.hasClass('has-children')) toggleNode(li);
        });
    } catch (_) {}
}

async function toggleNode(li, { save = true } = {}) {
    if (navigationBusy || !li.length) return;
    const generation = searchGeneration;
    const nodeId = li.attr('data-id');
    const sectionType = li.attr('data-type');
    const container = li.children('.children-container');
    const icon = li.children('.node-content').find('.expand-icon');
    if (icon.prop('disabled')) return;
    let success = true;
    try {
        if (li.hasClass('collapsed')) {
            setNodeExpanded(li, true);
            if (isSearchFilterActive()) {
                const node = lastSearchTrees[sectionType]?.nodes?.[nodeId];
                const count = container.children('.tree-node').length;
                const needsChildren = li.hasClass('tree-node-context') ? count === 0
                    : li.hasClass('tree-node-match') && !container.children('.siblings-row').length && count < (node?.child_count || 0);
                if (needsChildren && container[0]?.dataset.loaded !== 'true') {
                    success = await fetchAndMergeChildren(nodeId, container, sectionType, { control: icon, generation });
                }
            } else if (container[0]?.dataset.loaded !== 'true') {
                success = await loadTreeNodes(nodeId, container, sectionType, { generation });
            }
        } else {
            setNodeExpanded(li, false);
        }
    } finally {
        if (generation === searchGeneration) {
            if (success && save) saveViewSoon(generation);
        }
    }
}

function selectNode(li, updateUrl = true, { generation, reveal = true, notify = true } = {}) {
    li = li.first();
    if (!li.length || (navigationBusy && generation === undefined)) return Promise.resolve(false);
    if (updateUrl && li.hasClass('selected') && !navigationBusy) {
        ensureNodeVisible(li);
        saveViewSoon();
        if (notify) notifySelection(li);
        return loadDetails(li.attr('data-id'), li.attr('data-type'));
    }
    const ownsNavigation = generation === undefined;
    if (ownsNavigation) generation = beginNavigation();
    if (generation !== searchGeneration) return Promise.resolve(false);
    if (reveal) ensureNodeVisible(li);
    $('.tree-node.selected').removeClass('selected');
    li.addClass('selected');
    const details = loadDetails(li.attr('data-id'), li.attr('data-type'), generation);
    if (notify) notifySelection(li);
    if (ownsNavigation) finishNavigation(generation, updateUrl ? 'push' : null, selectionUrl(captureSelection()));
    return details;
}

function ensureNodeVisible(li) {
    if (isSearchFilterActive()) {
        li.add(li.parents('.tree-node')).each(function() {
            const node = $(this);
            const row = node.parent().children('.siblings-row');
            if (node.hasClass('tree-node-context') && this.style.display === 'none' &&
                row.length && !row.data('siblingsOpen')) {
                showSiblingsRowContext(row);
            }
        });
    }
    const cfg = SECTIONS[li.attr('data-type')];
    document.getElementById(cfg.rootListId).style.display = '';
    const section = document.getElementById(cfg.sectionId);
    section.style.display = '';
    section.querySelector('.section-chevron')?.classList.remove('collapsed');
    li.parents('li.tree-node').each(function() {
        const parent = $(this);
        if (parent.hasClass('collapsed')) setNodeExpanded(parent, true);
    });
}

// ---------- Detail loading ----------
async function loadDetails(iri, sectionType, generation = searchGeneration) {
    const selection = ++selectionGeneration;
    const current = () => generation === searchGeneration && selection === selectionGeneration;
    const container = document.getElementById('class-details');
    if (!container || !current()) return false;
    detailsPending = true;
    container.innerHTML = '<div class="p-4" role="status">Loading details...</div>';
    const cfg = SECTIONS[sectionType];
    const nodeId = encodeURIComponent(extractIdFromIri(iri));
    try {
        const response = await fetch(ontologyUrl(cfg.detailsEndpoint + nodeId));
        if (!current()) return false;
        if (!response.ok) throw new Error('Could not fetch rendered template');
        const html = await response.text();
        if (!current()) return false;
        container.innerHTML = html;
        return true;
    } catch (_) {
        if (!current()) return false;
        try {
            const response = await fetch(ontologyUrl(cfg.nodeDataEndpoint + nodeId));
            if (!current()) return false;
            if (!response.ok) throw new Error('Could not fetch details');
            const data = await response.json();
            if (!current()) return false;
            const heading = document.createElement('h3');
            heading.className = 'text-2xl font-semibold mb-2';
            heading.textContent = data.label || 'Unknown';
            const definition = document.createElement('p');
            definition.textContent = data.definition || '';
            container.replaceChildren(heading, definition);
            return true;
        } catch (_) {
            if (current()) container.innerHTML = '<div class="p-4 text-red-500">Unable to load details. Please try again or select a different item.</div>';
            return false;
        }
    } finally {
        if (current()) detailsPending = false;
    }
}

function loadClassDetails(iri) {
    return selectNodeByIri(iri);
}

// ---------- selectNodeByIri: cross-type navigation ----------
async function selectNodeByIri(iri) {
    if (navigationBusy) return;
    const existing = $('.tree-node').filter(function() { return this.dataset.id === iri; }).first();
    if (existing.length) return selectNode(existing);
    const generation = beginNavigation();
    try {
        if (isSearchFilterActive()) {
            const selected = await revealAndSelectInSearch(iri, generation);
            if (!selected) throw new Error('Could not reveal item');
        } else {
            const paths = await Promise.all(Object.keys(SECTIONS).map(async type => {
                const response = await fetch(ontologyUrl(SECTIONS[type].pathEndpoint + encodeURIComponent(extractIdFromIri(iri))));
                return response.ok ? response.json() : null;
            }));
            if (generation !== searchGeneration) return;
            const index = paths.findIndex(result => result?.path?.length);
            if (index < 0) throw new Error('Node not found');
            const type = Object.keys(SECTIONS)[index];
            const path = paths[index].path.map(item => item.iri);
            await loadNodePath(path, type, generation);
            if (generation !== searchGeneration) return;
            const node = findOccurrence(type, path);
            if (!node.length) throw new Error('Node not found');
            selectNode(node, false, { generation });
        }
        if (generation !== searchGeneration) return;
        finishNavigation(generation, 'push', selectionUrl(captureSelection()));
    } catch (_) {
        if (generation !== searchGeneration) return;
        finishNavigation(generation);
        resumeSelection(generation);
        historyNotice('Unable to reveal that item. Please try again.');
    }
}

// Reveal details links through the same child and sibling controls as search browsing.
async function revealAndSelectInSearch(iri, search) {
    const generation = ++revealGeneration;
    const searchTrees = lastSearchTrees;
    const stillSearching = () => generation === revealGeneration && search === searchGeneration &&
        lastSearchTrees === searchTrees &&
        isSearchFilterActive();
    try {
        let sectionType = ['class', 'property'].find(type => searchTrees[type]?.nodes?.[iri]);
        let targetData;
        if (!sectionType) {
            sectionType = 'class';
            try {
                targetData = await getNodeData(iri, sectionType);
            } catch (error) {
                if (!stillSearching()) return;
                if (error.message !== 'Failed to fetch node data: 404') throw error;
                sectionType = 'property';
                targetData = await getNodeData(iri, sectionType);
            }
        }
        if (!stillSearching()) return;
        const root = $('#' + SECTIONS[sectionType].rootListId);
        const findNode = id => root.find('.tree-node').filter(function() {
            return this.dataset.id === id;
        }).first();
        const chain = [iri];
        const visited = new Set();
        let current = iri;
        let ancestor = null;
        while (true) {
            if (visited.has(current)) throw new Error('Cycle in node parent chain');
            visited.add(current);
            const data = current === iri && targetData ? targetData : await getNodeData(current, sectionType);
            if (!stillSearching()) return;
            const parents = data.parents || [];
            if (!parents.length) break;
            // Check all parents: endpoint label order can differ from the search path.
            const candidates = parents.map(parent => ({
                iri: parent.iri,
                inDom: findNode(parent.iri).length > 0,
                inTree: !!searchTrees[sectionType]?.nodes?.[parent.iri]
            }));
            const shown = candidates.find(parent => parent.inDom) || candidates.find(parent => parent.inTree);
            if (shown) {
                ancestor = shown.iri;
                break;
            }
            current = parents[0].iri;
            chain.unshift(current);
        }

        let parent = ancestor === null ? $() : findNode(ancestor);
        if (ancestor !== null && !parent.length) return;
        for (const nextId of chain) {
            if (!stillSearching()) return;
            const container = parent.length ? parent.children('.children-container') : root;
            const findChild = () => container.children('.tree-node').filter(function() {
                return this.dataset.id === nextId;
            }).first();
            let next = findChild();
            if (!next.length) {
                if (parent.hasClass('tree-node-match') || parent.hasClass('tree-node-context')) {
                    // Await the merge before toggling to avoid a second, unawaited fetch.
                    const success = await fetchAndMergeChildren(parent.attr('data-id'), container, sectionType,
                        { control: parent.children('.node-content').find('.expand-icon') });
                    if (!stillSearching() || !success) return;
                } else {
                    let row = container.children('.siblings-row');
                    if (!parent.length && !row.length) {
                        // Empty search sections are not rendered, including their root row.
                        appendSiblingsRow(container, sectionType, '#', '', searchTrees[sectionType]?.hidden_root_count || 1);
                        setupNodeClickHandlers();
                        row = container.children('.siblings-row');
                    }
                    if (!row.length) return;
                    row.data('siblingsRequested', true);
                    const success = await fetchAndMergeChildren(parent.attr('data-id') || '#', container, sectionType,
                        { control: row.find('button') });
                    if (!stillSearching() || !success) return;
                    row.data('siblingsLoaded', true);
                    showSiblingsRowContext(row);
                }
                next = findChild();
            }
            if (!next.length) return;
            if (parent.hasClass('collapsed')) setNodeExpanded(parent, true);
            parent = next;
        }
        if (!stillSearching()) return;
        selectNode(parent, false, { generation: search });
        parent[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        return true;
    } catch (error) {
        console.warn('Unable to reveal search node:', error);
    }
}
// ============================================================
// Phase 1: Detail-pane tab strip (Details | Entity Graph)
// Wires the buttons added by tree.html (Plan 05 Task 1) to swap
// panel visibility. Updates window.EntityGraph.state.activeTab so
// the graph module knows whether to fetch on entity:selected.
// ============================================================

function wireDetailTabs() {
    var tabDetails = document.getElementById('tab-details');
    var tabGraph   = document.getElementById('tab-graph');
    var panelDetails = document.getElementById('tab-panel-details');
    var panelGraph   = document.getElementById('tab-panel-graph');
    if (!tabDetails || !tabGraph || !panelDetails || !panelGraph) {
        // tree.html structure not present (e.g. dev page); nothing to wire.
        return;
    }

    var ACTIVE_CLS = 'px-4 py-2 text-sm font-semibold border-b-2 border-blue-600 bg-white text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2';
    var INACTIVE_CLS = 'px-4 py-2 text-sm font-semibold border-b-2 border-transparent bg-gray-100 text-gray-600 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2';

    function activate(which) {
        var detailsActive = (which === 'details');
        tabDetails.setAttribute('aria-selected', detailsActive ? 'true' : 'false');
        tabGraph.setAttribute('aria-selected',   detailsActive ? 'false' : 'true');
        tabDetails.setAttribute('tabindex', detailsActive ? '0' : '-1');
        tabGraph.setAttribute('tabindex',   detailsActive ? '-1' : '0');
        tabDetails.className = detailsActive ? ACTIVE_CLS : INACTIVE_CLS;
        tabGraph.className   = detailsActive ? INACTIVE_CLS : ACTIVE_CLS;
        if (detailsActive) {
            panelDetails.classList.remove('hidden');
            panelDetails.removeAttribute('hidden');
            panelGraph.classList.add('hidden');
            panelGraph.setAttribute('hidden', '');
        } else {
            panelGraph.classList.remove('hidden');
            panelGraph.removeAttribute('hidden');
            panelDetails.classList.add('hidden');
            panelDetails.setAttribute('hidden', '');
        }
        if (window.EntityGraph && window.EntityGraph.state) {
            window.EntityGraph.state.activeTab = detailsActive ? 'details' : 'graph';
        }
        // Plan 13: show the Full screen button only while the Graph tab is
        // active. Hidden on Details so the tab strip stays clean.
        var fsBtn = document.getElementById('tab-fullscreen');
        if (fsBtn) {
            if (detailsActive) fsBtn.classList.add('hidden');
            else               fsBtn.classList.remove('hidden');
        }
        if (!detailsActive && window.EntityGraph && typeof window.EntityGraph.onTabActivated === 'function') {
            try { window.EntityGraph.onTabActivated(); } catch (err) {
                if (window.console && window.console.error) window.console.error(err);
            }
        }
    }

    tabDetails.addEventListener('click', function () { activate('details'); });
    tabGraph.addEventListener('click',   function () { activate('graph');   });

    // Arrow-key cycling per UI-SPEC §Interaction Contract (ARIA tablist pattern).
    function onKey(e) {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
        e.preventDefault();
        var current = (document.activeElement === tabGraph) ? 'graph' : 'details';
        var next = (current === 'details') ? 'graph' : 'details';
        activate(next);
        (next === 'graph' ? tabGraph : tabDetails).focus();
    }
    tabDetails.addEventListener('keydown', onKey);
    tabGraph.addEventListener('keydown',   onKey);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireDetailTabs);
} else {
    wireDetailTabs();
}

window.selectNodeByIri = selectNodeByIri;

// ---------- Load and select node (expand path) ----------
async function loadAndSelectNode(nodeId, sectionType, generation) {
    const root = $('#' + SECTIONS[sectionType].rootListId);
    let node = root.find('.tree-node').filter(function() { return this.dataset.id === nodeId; }).first();
    if (!node.length) {
        const response = await fetch(ontologyUrl(SECTIONS[sectionType].pathEndpoint + encodeURIComponent(extractIdFromIri(nodeId))));
        if (generation !== searchGeneration) return false;
        if (response.status === 404) {
            historyNotice('That item is no longer available in the tree.');
            return false;
        }
        if (!response.ok) throw new Error('Could not find node path');
        const data = await response.json();
        if (generation !== searchGeneration) return false;
        const path = (data.path || []).map(item => item.iri);
        await loadNodePath(path, sectionType, generation);
        if (generation !== searchGeneration) return false;
        node = findOccurrence(sectionType, path);
    }
    if (!node.length) { historyNotice('That item is no longer available in the tree.'); return false; }
    const loaded = await selectNode(node, false, { generation, notify: false });
    if (generation === searchGeneration && !loaded) throw new Error('Could not restore details');
    return loaded;
}

async function loadNodePath(path, sectionType, generation) {
    let list = $('#' + SECTIONS[sectionType].rootListId);
    for (let i = 0; i < path.length; i++) {
        if (generation !== searchGeneration) return;
        await loadTreeNodes(i === 0 ? '#' : path[i - 1], list, sectionType, { generation, strict: true });
        if (generation !== searchGeneration) return;
        const node = list.children('.tree-node').filter(function() { return this.dataset.id === path[i]; }).first();
        if (!node.length) return;
        if (i < path.length - 1) setNodeExpanded(node, true);
        list = node.children('.children-container');
    }
}

// ---------- Tree styles ----------
function applyTreeStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .section-tree-root, .children-container { list-style-type: none; padding-left: 0; }
        .children-container { padding-left: 14px; border-left: 1px solid rgba(209, 213, 219, 0.7); margin-left: 6px; }
        .children-container .tree-node:not(.selected):not(.tree-node-highlighted) > .node-content { background-color: white; color: var(--color-text-default, rgb(16, 16, 16)); }
        .tree-node { margin: 1px 0; position: relative; }
        .node-content { display: flex; align-items: center; padding: 2px 6px; border-radius: 3px; cursor: pointer; word-break: break-word; white-space: normal; border-bottom: 1px solid rgba(229, 231, 235, 0.3); line-height: 1.2; }
        .node-content:hover { background-color: rgba(59, 130, 246, 0.1); }
        .tree-node.selected > .node-content { background-color: var(--color-primary, rgb(24, 70, 120)) !important; color: white !important; font-weight: 600; }
        .node-label { flex-grow: 1; }
        @media (max-width: 768px) {
            .tree-explorer-container { flex-direction: column; }
            #tree-container, #detail-container { width: 100%; max-height: none; }
            #explore-tree { max-height: 400px; }
        }
        #explore-tree::-webkit-scrollbar { width: 8px; }
        #explore-tree::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        #explore-tree::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        #explore-tree::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
        .node-label span.bg-blue-100 { background-color: rgba(229, 231, 235, 0.7); padding: 0 2px; border-radius: 2px; font-weight: bold; color: var(--color-primary, rgb(24, 70, 120)); }
    `;
    document.head.appendChild(style);
}

function applyArrowStyles() {
    if (document.getElementById('unified-tree-arrow-styles')) return;
    const s = document.createElement('style');
    s.id = 'unified-tree-arrow-styles';
    s.textContent = `
        .expand-icon { cursor: pointer; width: 20px; height: 20px; display: inline-flex !important; align-items: center !important; justify-content: center; flex-shrink: 0; border-radius: 3px; transition: transform 0.15s ease; color: #6b7280; margin-right: 4px; }
        .expand-icon:hover { background-color: rgba(107, 114, 128, 0.12); color: #374151; }
        .expand-icon.expanded { transform: rotate(90deg); }
        .expand-icon svg { display: block; }
        .leaf-indicator { width: 20px; height: 20px; display: inline-flex !important; align-items: center !important; justify-content: center; flex-shrink: 0; margin-right: 4px; }
        .leaf-dot { width: 6px; height: 6px; border-radius: 50%; background-color: #d1d5db; }
        .tree-node.selected > .node-content .leaf-dot { background-color: rgba(255, 255, 255, 0.6); }
        .tree-node.selected > .node-content .expand-icon { color: white; }
    `;
    document.head.appendChild(s);
}

function applyContextStyles() {
    if (document.getElementById('unified-tree-context-styles')) return;
    const style = document.createElement('style');
    style.id = 'unified-tree-context-styles';
    style.textContent = `
        .tree-node-context > .node-content { color: var(--color-text-muted) !important; font-weight: 400 !important; }
        .tree-error-row, .siblings-row { list-style: none; color: var(--color-text-muted); font-size: 0.85em; padding: 3px 6px; }
        .siblings-toggle { min-height: 32px; padding: 4px 8px; display: inline-flex; align-items: center; cursor: pointer; background: transparent; border: 0; color: inherit; font: inherit; }
        .siblings-toggle:focus-visible { outline: 2px solid var(--color-primary, rgb(24,70,120)); outline-offset: 2px; }
        .tree-retry { color: inherit; cursor: pointer; background: transparent; border: 1px solid currentColor; border-radius: 3px; padding: 1px 6px; }
        .tree-retry:disabled { opacity: 0.6; cursor: wait; }
    `;
    document.head.appendChild(style);
}

// ---------- Expand / Collapse all ----------
async function toggleNodeBatch(nodes, resetUrl = false) {
    const generation = searchGeneration;
    await Promise.all($(nodes).get().map(node => toggleNode($(node), { save: false })));
    if (generation !== searchGeneration) return;
    if (resetUrl) resetUrlParameters();
    else saveViewSoon(generation);
}

function expandAllNodes() {
    if (navigationBusy) return;
    const collapsed = $('.tree-node.collapsed');
    const nodes = isSearchFilterActive()
        ? collapsed.not('.tree-node-match, .tree-node-context').get().concat(
            collapsed.filter('.tree-node-match, .tree-node-context').slice(0, 50).get())
        : collapsed;
    return toggleNodeBatch(nodes);
}

function collapseAllNodes() {
    if (navigationBusy) return;
    const selectedNodeId = getCurrentSelectedNodeId();
    let shouldResetUrl = false;
    if (selectedNodeId) {
        const selectedNode = $('.tree-node[data-id="' + selectedNodeId + '"]');
        if (selectedNode.length > 0 && selectedNode.parents('.tree-node').length > 0) shouldResetUrl = true;
    }
    return toggleNodeBatch($('.tree-node.expanded'), shouldResetUrl);
}

// Expand one ply deeper than the current frontier.
// First click expands depth 0 (top branches); each subsequent click drills one more level.
function expandOneMoreLevel() {
    if (navigationBusy) return;
    if (isSearchFilterActive()) {
        const collapsed = $('.tree-node.collapsed:visible');
        return toggleNodeBatch(collapsed.not('.tree-node-match, .tree-node-context').get().concat(
            collapsed.filter('.tree-node-match, .tree-node-context').slice(0, 50).get()));
    }
    let maxExpandedDepth = -1;
    $('.tree-node.expanded').each(function() {
        maxExpandedDepth = Math.max(maxExpandedDepth, $(this).parents('.tree-node').length);
    });
    return toggleNodeBatch($('.tree-node.collapsed').filter(function() {
        return $(this).parents('.tree-node').length === maxExpandedDepth + 1;
    }));
}

// Collapse only the deepest currently-expanded layer.
function collapseOneLevel() {
    if (navigationBusy) return;
    let maxDepth = -1;
    $('.tree-node.expanded').each(function() {
        maxDepth = Math.max(maxDepth, $(this).parents('.tree-node').length);
    });
    if (maxDepth < 0) return;
    return toggleNodeBatch($('.tree-node.expanded').filter(function() {
        return $(this).parents('.tree-node').length === maxDepth;
    }));
}

function getCurrentSelectedNodeId() {
    const url = ontologyUrl(window.location.href);
    const nodeParam = url.searchParams.get('node');
    if (nodeParam) return nodeParam;
    const selectedNode = $('.tree-node.selected');
    return selectedNode.length > 0 ? selectedNode.data('id') : null;
}

function resetUrlParameters() {
    writeView('replace', selectionUrl(null));
}

// ---------- Keyboard navigation ----------
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(event) {
        if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'BUTTON') return;
        const selectedNode = document.querySelector('.tree-node.selected');
        if (!selectedNode) return;

        if (event.key === ' ') {
            event.preventDefault();
            if (selectedNode.classList.contains('has-children')) {
                const icon = selectedNode.querySelector('.expand-icon');
                if (icon) icon.click();
            }
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('collapsed')) {
                const icon = selectedNode.querySelector('.expand-icon');
                if (icon) icon.click();
            }
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            if (selectedNode.classList.contains('has-children') && selectedNode.classList.contains('expanded')) {
                const icon = selectedNode.querySelector('.expand-icon');
                if (icon) icon.click();
            }
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            const visible = Array.from(document.querySelectorAll('.tree-node')).filter(n => window.getComputedStyle(n).display !== 'none');
            const idx = visible.indexOf(selectedNode);
            if (idx < visible.length - 1) {
                const nc = visible[idx + 1].querySelector('.node-content');
                if (nc) nc.click();
            }
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            const visible = Array.from(document.querySelectorAll('.tree-node')).filter(n => window.getComputedStyle(n).display !== 'none');
            const idx = visible.indexOf(selectedNode);
            if (idx > 0) {
                const nc = visible[idx - 1].querySelector('.node-content');
                if (nc) nc.click();
            }
        }
    });
}

// ---------- History navigation ----------
async function restoreHistory(state, initial = false) {
    const snapshot = savedView(state);
    const generation = beginNavigation(true);
    try {
        clearSelection();
        if (snapshot?.query) {
            const data = await fetchSearch(snapshot.query);
            if (generation !== searchGeneration) return;
            renderSearchResults(snapshot.query, data);
        } else {
            await clearFilterMode(generation);
        }
        if (generation !== searchGeneration) return;
        let missing = false;
        if (snapshot) {
            for (const type of Object.keys(SECTIONS)) {
                const section = snapshot.sections[type];
                const siblingPaths = new Set(section.siblings.map(item => JSON.stringify(item.path)));
                for (const path of [...section.loaded].sort((a, b) => a.length - b.length)) {
                    const list = occurrenceContainer(type, path);
                    if (!list.length) { missing = true; continue; }
                    if (siblingPaths.has(JSON.stringify(path))) {
                        if (!list.children('.siblings-row').length) {
                            const label = list.parent('.tree-node').children('.node-content').children('.node-label').text();
                            appendSiblingsRow(list, type, path.at(-1) || '#', label, 1);
                        }
                        list.children('.siblings-row').data('siblingsRequested', true);
                    }
                    if (snapshot.query) {
                        await fetchAndMergeChildren(path.at(-1) || '#', list, type, { generation, strict: true });
                    } else {
                        await loadTreeNodes(path.at(-1) || '#', list, type, { generation, strict: true });
                    }
                    if (generation !== searchGeneration) return;
                }
                const root = $('#' + SECTIONS[type].rootListId);
                const expanded = new Set(section.expanded.map(path => JSON.stringify(path)));
                root.find('.tree-node.has-children').each(function() {
                    setNodeExpanded($(this), expanded.has(JSON.stringify(occurrencePath(this))));
                });
                for (const siblings of section.siblings) {
                    const list = occurrenceContainer(type, siblings.path);
                    const row = list.children('.siblings-row');
                    if (!row.length) { missing = true; continue; }
                    row.data('siblingsLoaded', true);
                    showSiblingsRowContext(row);
                    if (!siblings.open) hideSiblingsRowContext(row);
                }
                root.toggle(section.open);
                $('#' + SECTIONS[type].sectionId + ' .section-chevron').toggleClass('collapsed', !section.open);
            }
            if (snapshot.selection) {
                const node = findOccurrence(snapshot.selection.type, snapshot.selection.path);
                if (node.length) {
                    const loaded = await selectNode(node, false, { generation, reveal: false, notify: false });
                    if (generation !== searchGeneration) return;
                    if (!loaded) throw new Error('Could not restore details');
                } else {
                    missing = true;
                }
            }
        } else {
            const params = new URLSearchParams(location.search);
            const nodeId = params.get('node') || (typeof state?.nodeId === 'string' ? state.nodeId : null);
            const requestedType = params.get('type') || state?.type;
            const type = Object.hasOwn(SECTIONS, requestedType) ? requestedType : 'class';
            if (nodeId) await loadAndSelectNode(nodeId, type, generation);
        }
        if (generation !== searchGeneration) return;
        notifySelection($('.tree-node.selected').first());
        finishNavigation(generation, initial && !snapshot ? 'replace' : null);
        if (missing) historyNotice('Some saved branches or the selected item are no longer available. The remaining view has been restored.');
    } catch (_) {
        if (generation !== searchGeneration) return;
        document.getElementById('explore-tree').setAttribute('aria-busy', 'false');
        historyNotice('This view could not be restored.', () => restoreHistory(state, initial));
    }
}

function setupHistoryNavigation() {
    window.addEventListener('popstate', event => restoreHistory(event.state));
    return restoreHistory(history.state, true);
}


// ---------- Search ----------
function setupSearch() {
    const input = document.getElementById('explore-search-input');
    const button = document.getElementById('explore-search-button');
    if (!input || !button) return;

    function doSearch() {
        if (input.value.length >= 2) searchUnified(input.value);
        else if (input.value.length) alert('Please enter at least 2 characters for search');
        else resetTreeSearch();
    }

    button.addEventListener('click', doSearch);
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); doSearch(); }
        if (e.key === 'Escape') { input.value = ''; resetTreeSearch(); }
    });

    // Wire up the inline clear (X) button
    const clearBtn = document.getElementById('explore-search-clear');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            resetTreeSearch();
            input.focus();
        });
    }
}

async function fetchSearch(query) {
    return Promise.all(Object.values(SECTIONS).map(async cfg => {
        const response = await fetch(ontologyUrl(cfg.searchEndpoint + '?query=' + encodeURIComponent(query)));
        if (!response.ok) throw new Error('Search failed');
        const data = await response.json();
        if (!Array.isArray(data.matches) || !data.tree) throw new Error('Invalid search results');
        return data;
    }));
}

async function searchUnified(query) {
    if (!query || query.length < 2) return;
    const interruptedRestore = restoringHistory;
    const generation = beginNavigation();
    try {
        const data = await fetchSearch(query);
        if (generation !== searchGeneration) return;
        if (data.every(result => result.matches.length === 0)) {
            await clearFilterMode(generation);
            if (generation !== searchGeneration) return;
            notifySelection(null);
        } else {
            renderSearchResults(query, data);
            const first = $('.tree-node-highlighted').first();
            selectNode(first, false, { generation });
        }
        finishNavigation(generation, 'push', selectionUrl(captureSelection()));
    } catch (_) {
        if (generation !== searchGeneration) return;
        finishNavigation(generation);
        if (interruptedRestore) {
            const recovery = restoreHistory(history.state);
            const recoveryGeneration = searchGeneration;
            await recovery;
            if (recoveryGeneration !== searchGeneration || restoringHistory) return;
        } else {
            resumeSelection(generation);
        }
        historyNotice('Search could not be loaded. Please try again.');
    }
}

function renderSearchResults(query, [classData, propData]) {
    committedQuery = query;
    document.getElementById('explore-search-input').value = query;
    const classSec = document.getElementById('class-section');
    const propSec = document.getElementById('property-section');
    lastSearchTrees = { class: classData.tree || null, property: propData.tree || null };
    const classMatches = classData.matches || [];
    const propMatches = propData.matches || [];
    const totalMatches = classMatches.length + propMatches.length;

    // Add filter controls
    addFilterModeControls(totalMatches, query, classMatches.length, propMatches.length);

    // Render class section
    const classRoot = document.getElementById(SECTIONS.class.rootListId);
    delete classRoot.dataset.loaded;
    classRoot.innerHTML = '';
    if (classMatches.length > 0 && classData.tree) {
        renderFilteredTree(classData.tree, classRoot, 'class', query);
        classSec.style.display = '';
        // Ensure section is expanded
        const classChevron = classSec.querySelector('.section-chevron');
        if (classChevron) classChevron.classList.remove('collapsed');
        classRoot.style.display = '';
    } else {
        // Collapse empty class section
        classRoot.style.display = 'none';
        const classChevron = classSec.querySelector('.section-chevron');
        if (classChevron) classChevron.classList.add('collapsed');
    }

    // Render property section
    const propRoot = document.getElementById(SECTIONS.property.rootListId);
    delete propRoot.dataset.loaded;
    propRoot.innerHTML = '';
    if (propMatches.length > 0 && propData.tree) {
        renderFilteredTree(propData.tree, propRoot, 'property', query);
        propSec.style.display = '';
        const propChevron = propSec.querySelector('.section-chevron');
        if (propChevron) propChevron.classList.remove('collapsed');
        propRoot.style.display = '';
    } else {
        propRoot.style.display = 'none';
        const propChevron = propSec.querySelector('.section-chevron');
        if (propChevron) propChevron.classList.add('collapsed');
    }

    // Update count badges
    document.getElementById('class-count').textContent = classMatches.length || '';
    document.getElementById('property-count').textContent = propMatches.length || '';

    setupNodeClickHandlers();

    // Highlight matches
    document.querySelectorAll('.tree-node-match').forEach(node => {
        node.classList.add('tree-node-highlighted');
        const label = node.querySelector('.node-label');
        if (label) {
            // Highlight in the main label text and in the preflabel annotation separately
            const annotation = label.querySelector('.preflabel-annotation');
            if (annotation) {
                const mainText = label.firstChild;
                if (mainText && mainText.nodeType === Node.TEXT_NODE) {
                    const span = document.createElement('span');
                    span.innerHTML = highlightText(mainText.textContent, query);
                    label.replaceChild(span, mainText);
                }
                annotation.innerHTML = '(' + highlightText(annotation.textContent.replace(/[()]/g, ''), query) + ')';
            } else {
                label.innerHTML = highlightText(label.textContent, query);
            }
        }
    });

}

function renderFilteredTree(treeData, container, sectionType, query) {
    if (!treeData || !treeData.root_nodes) return;
    treeData.root_nodes.forEach(nodeId => {
        renderFilteredNode(nodeId, treeData, container, sectionType);
    });
    appendSiblingsRow(container, sectionType, '#', '', treeData.hidden_root_count || 0);
}

function renderFilteredNode(nodeId, treeData, container, sectionType) {
    const node = treeData.nodes[nodeId];
    if (!node) return;
    const hasChildren = (node.child_count || 0) > 0 || (node.children && node.children.length > 0);
    const isExpanded = (node.children || []).some(childId => hasMatchDescendant(childId, treeData));
    const nodeClass = hasChildren ? (isExpanded ? 'has-children expanded' : 'has-children collapsed') : '';
    const isMatch = node.is_match ? 'tree-node-match' : '';
    const expandIcon = hasChildren
        ? '<span class="expand-icon' + (isExpanded ? ' expanded' : '') + '"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"></polyline></svg></span>'
        : '<span class="leaf-indicator"><span class="leaf-dot"></span></span>';

    // Show preferred label annotation when match is via preferred_label
    let labelHtml = node.label;
    if (node.is_match && node.preferred_label && node.match_field === 'preferred_label') {
        labelHtml += ' <span class="preflabel-annotation">(' + node.preferred_label + ')</span>';
    }

    const li = document.createElement('li');
    li.className = 'tree-node ' + nodeClass + ' ' + isMatch;
    li.dataset.id = node.id;
    li.dataset.type = sectionType;
    li.innerHTML = '<div class="node-content">' + expandIcon + '<span class="node-label">' + labelHtml + '</span></div>' +
        (hasChildren ? '<ul class="children-container" style="display:' + (isExpanded ? 'block' : 'none') + ';"></ul>' : '');
    container.appendChild(li);

    if (hasChildren) {
        const childrenContainer = li.querySelector('.children-container');
        (node.children || []).forEach(childId => {
            renderFilteredNode(childId, treeData, childrenContainer, sectionType);
        });
        const hidden = (node.child_count || 0) - $(childrenContainer).children('.tree-node').length;
        if (!node.is_match || isExpanded) appendSiblingsRow(childrenContainer, sectionType, nodeId, node.label, hidden);
    }
}

function hasMatchDescendant(nodeId, treeData) {
    const node = treeData.nodes[nodeId];
    if (!node) return false;
    if (node.is_match) return true;
    if (node.children) {
        for (const childId of node.children) {
            if (hasMatchDescendant(childId, treeData)) return true;
        }
    }
    return false;
}

function addFilterModeControls(totalCount, query, classCount, propCount) {
    // Show the inline clear (X) button inside the search input
    const clearBtn = document.getElementById('explore-search-clear');
    if (clearBtn) clearBtn.style.display = 'flex';

    // Build match-count text
    let detail = totalCount + ' match' + (totalCount !== 1 ? 'es' : '');
    if (classCount > 0 && propCount > 0) {
        detail += ' (' + classCount + ' class' + (classCount !== 1 ? 'es' : '') + ', ' + propCount + ' propert' + (propCount !== 1 ? 'ies' : 'y') + ')';
    } else if (classCount > 0) {
        detail += ' in classes';
    } else if (propCount > 0) {
        detail += ' in properties';
    }

    // Show the match-count line below the search input
    const countEl = document.getElementById('search-match-count');
    if (countEl) {
        countEl.textContent = detail;
        countEl.style.display = '';
    }

    // Mark filter as active (used by resetTreeSearch to detect filter state)
    document.getElementById('explore-search-input').dataset.filtering = 'true';

    addFilterModeStyles();
}

async function clearFilterMode(generation) {
    const types = Object.keys(SECTIONS);
    const roots = await Promise.all(types.map(type => childData('#', type, generation)));
    if (generation !== searchGeneration) return;
    committedQuery = '';
    lastSearchTrees = { class: null, property: null };
    document.getElementById('explore-search-clear').style.display = 'none';
    const count = document.getElementById('search-match-count');
    count.textContent = '';
    count.style.display = 'none';
    const input = document.getElementById('explore-search-input');
    input.value = '';
    delete input.dataset.filtering;
    clearSelection();
    types.forEach((type, index) => {
        const cfg = SECTIONS[type];
        const root = document.getElementById(cfg.rootListId);
        root.innerHTML = '';
        delete root.dataset.loaded;
        root.style.display = '';
        document.getElementById(cfg.sectionId).style.display = '';
        document.querySelector('#' + cfg.sectionId + ' .section-chevron').classList.remove('collapsed');
        renderLoadedChildren('#', $(root), type, roots[index]);
    });
}

async function resetTreeSearch() {
    if (!committedQuery && !navigationBusy) {
        document.getElementById('explore-search-input').value = '';
        return;
    }
    const generation = beginNavigation();
    try {
        await clearFilterMode(generation);
        if (generation !== searchGeneration) return;
        notifySelection(null);
        finishNavigation(generation, 'push', selectionUrl(null));
    } catch (_) {
        if (generation !== searchGeneration) return;
        finishNavigation(generation);
        resumeSelection(generation);
        historyNotice('The full tree could not be loaded. Please try again.');
    }
}

function addFilterModeStyles() {
    if (document.getElementById('filter-mode-styles')) return;
    const style = document.createElement('style');
    style.id = 'filter-mode-styles';
    style.textContent = '.tree-node-highlighted>.node-content,.tree-node-match>.node-content{background-color:var(--color-primary,rgb(24,70,120))!important;color:white!important;border-left-color:rgba(255,255,255,0.8)!important}.tree-node-match>.node-content{font-weight:500}.preflabel-annotation{font-size:0.8em;opacity:0.85;font-style:italic}';
    document.head.appendChild(style);
}

function highlightText(text, query) {
    const regex = new RegExp('(' + escapeRegEx(query) + ')', 'gi');
    return text.replace(regex, '<span class="bg-blue-100">$1</span>');
}

function escapeRegEx(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ---------- Main initialization ----------
function initializeUnifiedTree() {
    if (treeBlocked) return;
    if (typeof $ === 'undefined') {
        const treeEl = document.getElementById('explore-tree');
        if (treeEl) treeEl.innerHTML = '<div class="p-4 text-yellow-800 bg-yellow-100 rounded"><h3 class="font-medium">Unable to load tree</h3><p>JavaScript libraries needed for the tree are not available.</p></div>';
        return;
    }

    applyTreeStyles();
    applyArrowStyles();
    applyContextStyles();
    setupSectionHeaders();

    setupNodeClickHandlers();
    setupKeyboardNavigation();
    setupHistoryNavigation();
    setupSearch();
}
