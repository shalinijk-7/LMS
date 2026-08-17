/**
 * Theme Management System for AuraLearn
 * Handles applying, saving, and switching themes using localStorage.
 */

// This function is called synchronously in the <head> to prevent theme flashing
window.initTheme = function() {
    try {
        const savedTheme = localStorage.getItem('auralearn-theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    } catch (e) {
        console.error('Error loading theme:', e);
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const currentTheme = localStorage.getItem('auralearn-theme') || 'light';
    
    /**
     * Applies the chosen theme by updating the DOM, saving to localStorage, 
     * and dispatching a custom event for other components to react.
     */
    window.setTheme = function(themeName) {
        // Set attribute on HTML root
        document.documentElement.setAttribute('data-theme', themeName);
        
        // Save to localStorage
        localStorage.setItem('auralearn-theme', themeName);
        
        // Update active states on any theme selector cards or buttons
        document.querySelectorAll('.theme-option-card').forEach(card => {
            if (card.dataset.themeValue === themeName) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });

        // Dispatch a custom event so charts/plugins can listen and re-render if needed
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: themeName } }));
    };

    // Initialize UI active states for custom cards
    document.querySelectorAll('.theme-option-card').forEach(card => {
        if (card.dataset.themeValue === currentTheme) {
            card.classList.add('active');
        }
        
        /**
         * Click event listener to set the selected theme when a theme card is clicked.
         */
        card.addEventListener('click', function(e) {
            e.preventDefault();
            setTheme(this.dataset.themeValue);
        });
    });
});
