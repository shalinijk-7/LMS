// Main JavaScript for AuraLearn

document.addEventListener('DOMContentLoaded', () => {

    // ===== MULTI THEME SYSTEM =====
    const body = document.body;
    const themeBtn = document.getElementById('themePickerBtn');
    const themeDropdown = document.getElementById('themeDropdown');
    const themeOptions = document.querySelectorAll('.theme-option');

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || body.getAttribute('data-theme') || 'default';
    applyTheme(savedTheme);

    // Toggle dropdown
    if (themeBtn && themeDropdown) {
        themeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            themeDropdown.classList.toggle('show');
        });

        // Close when clicking outside
        document.addEventListener('click', () => {
            themeDropdown.classList.remove('show');
        });

        themeDropdown.addEventListener('click', (e) => e.stopPropagation());
    }

    // Theme option click
    themeOptions.forEach(option => {
        option.addEventListener('click', () => {
            const theme = option.getAttribute('data-theme');
            applyTheme(theme);
            localStorage.setItem('theme', theme);

            // Save to server if logged in
            fetch('/settings/update_theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ theme: theme })
            }).catch(() => {});

            themeDropdown.classList.remove('show');
        });
    });

    function applyTheme(theme) {
        body.setAttribute('data-theme', theme);

        // Highlight active option
        themeOptions.forEach(opt => {
            opt.classList.toggle('active', opt.getAttribute('data-theme') === theme);
        });
    }

    // ===== Flash message close functionality =====
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.opacity = '0';
                msg.style.transform = 'translateY(-20px)';
                msg.style.transition = 'all 0.5s ease';
                setTimeout(() => msg.remove(), 500);
            });
        }, 5000);
    }
    
    // ===== Navbar scroll effect =====
    const navbar = document.querySelector('.navbar');
    if (navbar) {
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