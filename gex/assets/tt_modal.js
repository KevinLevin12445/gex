// Instant client-side modal behavior for Tastytrade API configuration
(function() {
    function getModal() {
        return document.getElementById('tt-modal');
    }

    function openModal() {
        var modal = getModal();
        if (modal) {
            modal.style.display = 'flex';
            var inp = document.getElementById('tt-input-client-id');
            if (inp && !inp.value) {
                setTimeout(function() { inp.focus(); }, 50);
            }
        }
    }

    function closeModal() {
        var modal = getModal();
        if (modal) {
            modal.style.display = 'none';
        }
    }

    document.addEventListener('click', function(e) {
        // Check for modal open triggers
        if (
            e.target.closest('#tt-modal-open-btn') ||
            e.target.closest('#rt-badge') ||
            e.target.closest('.tt-open-trigger') ||
            e.target.closest('[data-action="open-tt-modal"]')
        ) {
            openModal();
            return;
        }

        // Check for modal close triggers
        if (
            e.target.closest('#tt-modal-close-icon') ||
            e.target.closest('#tt-modal-close-btn') ||
            e.target.id === 'tt-modal'
        ) {
            closeModal();
            return;
        }
    }, true);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            closeModal();
        }
    });
})();
