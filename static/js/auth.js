document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // 1. Password Visibility Toggle
    // ==========================================
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    
    /**
     * Click event listeners to toggle password visibility.
     * Changes input type and swaps the eye/eye-slash icons.
     */
    togglePasswordButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });

    // ==========================================
    // 2. Password Strength & Validation (Signup)
    // ==========================================
    const passwordInput = document.getElementById('register-password');
    const confirmPasswordInput = document.getElementById('confirm-password');
    const strengthBar = document.getElementById('password-strength-bar');
    const strengthText = document.getElementById('password-strength-text');
    const registerForm = document.getElementById('register-form');
    
    if (passwordInput && strengthBar && strengthText) {
        /**
         * Input event listener to calculate password strength in real-time.
         * Updates the UI progress bar and text to indicate strength level.
         */
        passwordInput.addEventListener('input', function() {
            const val = this.value;
            let strength = 0;
            
            if (val.length >= 8) strength += 1;
            if (val.match(/[a-z]+/)) strength += 1;
            if (val.match(/[A-Z]+/)) strength += 1;
            if (val.match(/[0-9]+/)) strength += 1;
            if (val.match(/[$@#&!]+/)) strength += 1;

            // Reset classes
            strengthBar.className = 'progress-bar';
            
            if (val.length === 0) {
                strengthBar.style.width = '0%';
                strengthText.textContent = '';
            } else if (strength <= 2) {
                strengthBar.style.width = '33%';
                strengthBar.classList.add('bg-danger');
                strengthText.textContent = 'Weak';
                strengthText.className = 'text-danger small fw-medium mt-1';
            } else if (strength <= 4) {
                strengthBar.style.width = '66%';
                strengthBar.classList.add('bg-warning');
                strengthText.textContent = 'Medium';
                strengthText.className = 'text-warning small fw-medium mt-1';
            } else {
                strengthBar.style.width = '100%';
                strengthBar.classList.add('bg-success');
                strengthText.textContent = 'Strong';
                strengthText.className = 'text-success small fw-medium mt-1';
            }
            
            validatePasswords();
        });
    }
    
    if (confirmPasswordInput) {
        /**
         * Input event listener for confirm password to validate in real-time.
         */
        confirmPasswordInput.addEventListener('input', validatePasswords);
    }
    
    function validatePasswords() {
        if (!passwordInput || !confirmPasswordInput) return true;
        
        const pwd = passwordInput.value;
        const confirm = confirmPasswordInput.value;
        const mismatchError = document.getElementById('password-mismatch-error');
        const lengthError = document.getElementById('password-length-error');
        
        let isValid = true;
        
        // Length check
        if (pwd.length > 0 && pwd.length < 8) {
            if (lengthError) lengthError.classList.remove('d-none');
            isValid = false;
        } else {
            if (lengthError) lengthError.classList.add('d-none');
        }
        
        // Match check
        if (confirm.length > 0 && pwd !== confirm) {
            if (mismatchError) mismatchError.classList.remove('d-none');
            isValid = false;
        } else {
            if (mismatchError) mismatchError.classList.add('d-none');
        }
        
        return isValid;
    }

    // ==========================================
    // 3. Form Submission Handling
    // ==========================================
    
    // Register Form Handling
    if (registerForm) {
        /**
         * Submit event listener for the registration form.
         * Validates terms checkbox and passwords before submission, updating UI with errors if needed.
         */
        registerForm.addEventListener('submit', function(e) {
            const termsCheckbox = document.getElementById('agree-terms');
            const termsError = document.getElementById('terms-error');
            
            // Validate Terms
            if (termsCheckbox && !termsCheckbox.checked) {
                e.preventDefault();
                if (termsError) termsError.classList.remove('d-none');
                return;
            } else if (termsError) {
                termsError.classList.add('d-none');
            }
            
            // Validate Passwords
            if (!validatePasswords() || passwordInput.value.length < 8 || passwordInput.value !== confirmPasswordInput.value) {
                e.preventDefault();
                // Manually trigger validation display if they didn't touch the confirm field
                if (passwordInput.value !== confirmPasswordInput.value) {
                    document.getElementById('password-mismatch-error').classList.remove('d-none');
                }
                if (passwordInput.value.length < 8) {
                    document.getElementById('password-length-error').classList.remove('d-none');
                }
                return;
            }
            
            // Show Loading State
            setButtonLoading(this, 'Creating Account...');
        });
        
        // Hide terms error when user checks the box
        const termsCheckbox = document.getElementById('agree-terms');
        if (termsCheckbox) {
            /**
             * Change event listener to hide the terms error message when the user checks the box.
             */
            termsCheckbox.addEventListener('change', function() {
                const termsError = document.getElementById('terms-error');
                if (this.checked && termsError) {
                    termsError.classList.add('d-none');
                }
            });
        }
    }
    
    // Login Form Handling
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        /**
         * Submit event listener for the login form.
         * Shows loading state UI on the submit button.
         */
        loginForm.addEventListener('submit', function(e) {
            // Show Loading State
            setButtonLoading(this, 'Logging in...');
        });
    }
    
    /**
     * Helper function to update the submit button UI to a loading state.
     * Prevents double submission by disabling the button.
     */
    function setButtonLoading(form, loadingText) {
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            // Prevent double submission
            if (btn.hasAttribute('disabled')) {
                return;
            }
            
            const originalText = btn.innerHTML;
            btn.setAttribute('data-original-text', originalText);
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${loadingText}`;
            
            // For robust handling, if the server doesn't respond quickly, we don't want them stuck forever, but standard form submission will navigate away.
            // If they stop the page load, we should technically re-enable, but standard practice is to let the browser navigate.
        }
    }
});
