// Main JavaScript for AuraLearn

document.addEventListener('DOMContentLoaded', () => {
    // Flash message close functionality
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        /**
         * UI Update: Fades out and removes flash messages after 5 seconds.
         */
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.opacity = '0';
                msg.style.transform = 'translateY(-20px)';
                msg.style.transition = 'all 0.5s ease';
                setTimeout(() => msg.remove(), 500);
            });
        }, 5000);
    }
    
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        /**
         * Scroll event listener to apply a shadow and background opacity to the navbar 
         * when the user scrolls down the page.
         */
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.style.boxShadow = 'var(--shadow-md)';
                navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            } else {
                navbar.style.boxShadow = 'var(--shadow-sm)';
                navbar.style.background = 'rgba(255, 255, 255, 0.8)';
            }
        });
    }
});
