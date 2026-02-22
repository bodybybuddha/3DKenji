// Theme switching and global utilities

(function () {
    'use strict';

    /**
     * Theme Manager: Handle theme switching and persistence
     */
    const ThemeManager = {
        // Storage key for user preference
        storageKey: 'kenji-theme',

        /**
         * Initialize theme from user preference or default
         */
        init() {
            // Get saved theme preference
            const saved = localStorage.getItem(this.storageKey);

            // Get user preference from media query
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

            // Load theme: saved > computed from media query > 'dark'
            const theme = saved || (prefersDark ? 'dark' : 'light') || 'dark';

            this.loadTheme(theme);

            // Watch for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                const newTheme = e.matches ? 'dark' : 'light';
                // Only auto-switch if no saved preference
                if (!saved) {
                    this.loadTheme(newTheme);
                }
            });
        },

        /**
         * Load a theme by name
         */
        loadTheme(themeName) {
            // Remove existing theme stylesheet if present
            const existing = document.getElementById('theme-css');
            if (existing) {
                existing.remove();
            }

            // Load new theme CSS from API endpoint
            const link = document.createElement('link');
            link.id = 'theme-css';
            link.rel = 'stylesheet';
            link.href = `/api/v1/theme/css/${encodeURIComponent(themeName)}`;

            link.onerror = () => {
                console.error(`Failed to load theme: ${themeName}`);
                // Fallback to dark theme
                if (themeName !== 'dark') {
                    this.loadTheme('dark');
                }
            };

            document.head.appendChild(link);

            // Save preference
            localStorage.setItem(this.storageKey, themeName);

            // Update document attribute for CSS selectors
            document.documentElement.setAttribute('data-theme', themeName);

            // Dispatch custom event
            window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme: themeName } }));
        },

        /**
         * Get current theme
         */
        getCurrent() {
            return localStorage.getItem(this.storageKey) || 'dark';
        },

        /**
         * Toggle between dark and light themes
         */
        toggle() {
            const current = this.getCurrent();
            const next = current === 'dark' ? 'light' : 'dark';
            console.log(`Theme toggle: ${current} -> ${next}`);
            this.loadTheme(next);

            // Provide visual feedback
            if (window.HTMXHelper) {
                HTMXHelper.showToast(`Switched to ${next} theme`, 'success', 1500);
            }
        }
    };

    /**
     * HTMX Configuration and Helpers
     */
    const HTMXHelper = {
        init() {
            // Configure HTMX defaults
            if (window.htmx) {
                htmx.config.defaultIndicatorStyle = 'spinner';
                htmx.config.defaultSwapStyle = 'outerHTML';
                htmx.config.timeout = 10000;

                // Add CSRF token to requests if needed
                const token = document.querySelector('meta[name="csrf-token"]');
                if (token) {
                    htmx.on('htmx:xhr:configRequest', (detail) => {
                        detail.xhr.setRequestHeader('X-CSRF-Token', token.content);
                    });
                }
            }
        },

        /**
         * Show a toast notification
         */
        showToast(message, type = 'info', duration = 3000) {
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} toast`;
            toast.innerHTML = `
        <div class="alert-content">
          <p class="alert-message">${message}</p>
        </div>
        <button class="alert-close" role="button" aria-label="Close">&times;</button>
      `;

            document.body.appendChild(toast);

            // Handle close button
            toast.querySelector('.alert-close').addEventListener('click', () => {
                this.hideToast(toast);
            });

            // Auto-hide
            if (duration > 0) {
                setTimeout(() => this.hideToast(toast), duration);
            }

            return toast;
        },

        /**
         * Hide a toast notification
         */
        hideToast(toast) {
            toast.classList.add('is-hiding');
            setTimeout(() => toast.remove(), 300);
        },
    };

    /**
     * Form Helper: Client-side validation helper
     */
    const FormHelper = {
        /**
         * Validate a form element
         */
        validate(form) {
            let isValid = true;

            form.querySelectorAll('[required]').forEach((field) => {
                const group = field.closest('.form-group');
                if (!group) return;

                if (!field.value.trim()) {
                    this.showError(group, 'This field is required');
                    isValid = false;
                } else {
                    this.clearError(group);
                }

                // Type-specific validation
                if (field.type === 'email' && field.value) {
                    if (!this.isValidEmail(field.value)) {
                        this.showError(group, 'Invalid email address');
                        isValid = false;
                    }
                }
            });

            return isValid;
        },

        /**
         * Show validation error in form group
         */
        showError(group, message) {
            group.classList.add('is-invalid');
            let feedback = group.querySelector('.form-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'form-feedback';
                group.appendChild(feedback);
            }
            feedback.textContent = message;
        },

        /**
         * Clear validation error from form group
         */
        clearError(group) {
            group.classList.remove('is-invalid');
            const feedback = group.querySelector('.form-feedback');
            if (feedback) {
                feedback.remove();
            }
        },

        /**
         * Simple email validation
         */
        isValidEmail(email) {
            return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        },

        /**
         * Validate username format
         */
        isValidUsername(username) {
            return /^[a-zA-Z0-9_-]{3,32}$/.test(username);
        },

        /**
         * Validate password strength
         */
        isValidPassword(password) {
            return (
                password.length >= 8 &&
                /[A-Z]/.test(password) &&
                /[a-z]/.test(password) &&
                /\d/.test(password)
            );
        },

        /**
         * Display field-level errors from validation response
         */
        displayFieldErrors(form, errors) {
            // Clear all existing errors
            form.querySelectorAll('.form-feedback').forEach(el => el.remove());
            form.querySelectorAll('.is-invalid').forEach(field => {
                field.classList.remove('is-invalid');
            });

            // Display new errors
            Object.entries(errors).forEach(([field, messages]) => {
                const input = form.querySelector(`[name="${field}"]`);
                if (input) {
                    const group = input.closest('.form-group') || input.closest('div');
                    if (group) {
                        group.classList.add('is-invalid');
                        const feedback = document.createElement('div');
                        feedback.className = 'form-feedback';
                        messages.forEach((msg) => {
                            const item = document.createElement('div');
                            item.textContent = msg;
                            feedback.appendChild(item);
                        });
                        group.appendChild(feedback);
                    }
                }
            });
        },

        /**
         * Setup real-time validation on form fields
         */
        setupRealTimeValidation(form) {
            form.querySelectorAll('[data-validate]').forEach(field => {
                const validateType = field.getAttribute('data-validate');

                field.addEventListener('input', () => {
                    this.validateField(field, validateType);
                });

                field.addEventListener('blur', () => {
                    this.validateField(field, validateType);
                });
            });
        },

        /**
         * Validate a single field
         */
        validateField(field, type) {
            const group = field.closest('.form-group') || field.closest('div');
            if (!group) {
                return;
            }
            let isValid = true;
            let message = '';

            switch (type) {
                case 'email':
                    isValid = !field.value || this.isValidEmail(field.value);
                    message = 'Invalid email format';
                    break;
                case 'username':
                    isValid = !field.value || this.isValidUsername(field.value);
                    message = 'Username must be 3-32 characters (letters, numbers, _, -)';
                    break;
                case 'password':
                    isValid = !field.value || this.isValidPassword(field.value);
                    message = 'Password must contain uppercase, lowercase, and number (8+ chars)';
                    break;
                case 'url':
                    isValid = !field.value || /^https?:\/\/.+/.test(field.value);
                    message = 'Invalid URL format';
                    break;
            }

            if (field.value && !isValid) {
                this.showError(group, message);
            } else {
                this.clearError(group);
            }
        }
    };

    /**
     * CSRF Token Helper
     */
    const CSRFHelper = {
        getToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return meta ? meta.getAttribute('content') : null;
        },

        addToForm(form) {
            const token = this.getToken();
            if (!token) return;

            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            input.value = token;
            form.appendChild(input);
        }
    };

    /**
     * Dropdown Menu Helper
     */
    const DropdownHelper = {
        init() {
            // Handle user menu dropdown
            const menuBtn = document.getElementById('user-menu-btn');
            const menu = document.getElementById('user-menu');

            if (menuBtn && menu) {
                menuBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    menu.classList.toggle('is-open');
                });

                // Close on click outside
                document.addEventListener('click', (e) => {
                    if (!menu.contains(e.target) && !menuBtn.contains(e.target)) {
                        menu.classList.remove('is-open');
                    }
                });

                // Close when clicking menu items
                menu.querySelectorAll('a').forEach(link => {
                    link.addEventListener('click', () => {
                        menu.classList.remove('is-open');
                    });
                });
            }
        }
    };

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', () => {
        ThemeManager.init();
        HTMXHelper.init();
        DropdownHelper.init();
    });

    // Expose to global scope for use in templates/scripts
    window.ThemeManager = ThemeManager;
    window.HTMXHelper = HTMXHelper;
    window.FormHelper = FormHelper;
    window.CSRFHelper = CSRFHelper;
})();
