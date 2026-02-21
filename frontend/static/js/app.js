// Theme switching and global utilities

(function() {
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
      this.loadTheme(next);
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

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    HTMXHelper.init();
  });

  // Expose to global scope for use in templates/scripts
  window.ThemeManager = ThemeManager;
  window.HTMXHelper = HTMXHelper;
  window.FormHelper = FormHelper;
  window.CSRFHelper = CSRFHelper;
})();
