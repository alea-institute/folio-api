/**
 * Draggable split-pane resizer with localStorage persistence.
 *
 * Usage:
 *   initSplitPane({ storageKey: 'folio-taxonomy-split', defaultPct: 25 });
 *
 * - Inserts a drag handle between #tree-container and #detail-container.
 * - Saves the tree-panel width (%) to localStorage on every drag.
 * - Restores width from localStorage on page load.
 * - Double-click the handle to reset to the default width.
 * - Disabled on mobile (< 768 px) where the panels stack vertically.
 */
function initSplitPane(opts) {
    const storageKey = opts.storageKey || 'folio-split-pct';
    const defaultPct = opts.defaultPct || 25;
    const minPct = opts.minPct || 15;
    const maxPct = opts.maxPct || 55;

    const container = document.querySelector('.tree-explorer-container');
    const treePanel = document.getElementById('tree-container');
    const detailPanel = document.getElementById('detail-container');
    if (!container || !treePanel || !detailPanel) return;

    // --- Create handle ---
    const handle = document.createElement('div');
    handle.className = 'split-handle';
    handle.title = 'Drag to resize \u00b7 Double-click to reset';
    treePanel.after(handle);

    // --- Apply width ---
    function applyWidth(pct) {
        treePanel.style.flex = 'none';
        treePanel.style.width = pct + '%';
        detailPanel.style.flex = '1';
        detailPanel.style.width = 'auto';
    }

    function isDesktop() {
        return window.innerWidth >= 768;
    }

    function activate() {
        const saved = localStorage.getItem(storageKey);
        const pct = saved ? parseFloat(saved) : defaultPct;
        applyWidth(pct);
        handle.style.display = '';
    }

    function deactivate() {
        // Remove inline overrides so Tailwind classes take over
        treePanel.style.flex = '';
        treePanel.style.width = '';
        detailPanel.style.flex = '';
        detailPanel.style.width = '';
        handle.style.display = 'none';
    }

    if (isDesktop()) {
        activate();
    } else {
        handle.style.display = 'none';
    }

    // --- Drag state ---
    let dragging = false;

    function onPointerDown(e) {
        if (!isDesktop()) return;
        dragging = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        // Prevent iframe / selection interference
        detailPanel.style.pointerEvents = 'none';
        e.preventDefault();
    }

    function onPointerMove(e) {
        if (!dragging) return;
        const rect = container.getBoundingClientRect();
        let pct = ((e.clientX - rect.left) / rect.width) * 100;
        pct = Math.max(minPct, Math.min(maxPct, pct));
        applyWidth(pct);
        localStorage.setItem(storageKey, pct.toFixed(2));
    }

    function onPointerUp() {
        if (!dragging) return;
        dragging = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        detailPanel.style.pointerEvents = '';
    }

    // Mouse events
    handle.addEventListener('mousedown', onPointerDown);
    document.addEventListener('mousemove', onPointerMove);
    document.addEventListener('mouseup', onPointerUp);

    // Touch events (tablets in landscape)
    handle.addEventListener('touchstart', function (e) {
        onPointerDown(e.touches[0]);
        e.preventDefault();
    }, { passive: false });
    document.addEventListener('touchmove', function (e) {
        if (dragging) onPointerMove(e.touches[0]);
    }, { passive: true });
    document.addEventListener('touchend', onPointerUp);

    // Double-click to reset
    handle.addEventListener('dblclick', function () {
        applyWidth(defaultPct);
        localStorage.setItem(storageKey, defaultPct);
    });

    // Respond to viewport changes
    window.addEventListener('resize', function () {
        if (isDesktop()) {
            activate();
        } else {
            deactivate();
        }
    });
}
