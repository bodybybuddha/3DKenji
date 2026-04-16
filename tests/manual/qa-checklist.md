# Frontend-Backend Integration QA Checklist

## Overview
This checklist should be used before each release to ensure all user inputs and forms are properly validated on both frontend and backend.

## Legend
- [ ] Not tested
- [x] Tested and passing
- [!] Tested but has issues
- [N/A] Not applicable

---

## Authentication & User Management

### User Registration
- [ ] Valid registration completes successfully
- [ ] Empty username is rejected
- [ ] Username < 3 characters is rejected
- [ ] Username > 50 characters is rejected
- [ ] Username with spaces is rejected
- [ ] Username with special characters is handled
- [ ] SQL injection in username is prevented
- [ ] XSS in username is prevented
- [ ] Empty email is rejected
- [ ] Invalid email format is rejected
- [ ] Duplicate email is rejected
- [ ] Empty password is rejected
- [ ] Password < 8 characters is rejected
- [ ] Weak password is rejected (if complexity required)
- [ ] XSS in display name is sanitized
- [ ] Unicode in display name is supported
- [ ] Form shows inline validation errors
- [ ] Form shows server-side validation errors
- [ ] Success message displays after registration
- [ ] User is redirected after registration

### User Login
- [ ] Valid credentials log in successfully
- [ ] Empty username is rejected
- [ ] Empty password is rejected
- [ ] Wrong password shows error
- [ ] Non-existent user shows error
- [ ] Error message doesn't reveal user existence
- [ ] SQL injection in login is prevented
- [ ] Rate limiting prevents brute force
- [ ] Session is created on success
- [ ] User is redirected after login

### User Logout
- [ ] Logout button is visible when logged in
- [ ] Logout clears session
- [ ] Logout redirects to appropriate page
- [ ] User cannot access protected pages after logout

### Profile Management
- [ ] Profile page loads with current user data
- [ ] Email update works with valid email
- [ ] Email update rejects invalid format
- [ ] Email update rejects duplicate email
- [ ] Display name update works
- [ ] Display name sanitizes XSS
- [ ] Display name supports unicode
- [ ] Password change requires old password
- [ ] Password change validates new password
- [ ] Password change confirms password match
- [ ] Success message shows after update
- [ ] Form field errors are displayed inline

---

## Project Management

### Project Creation
- [ ] Valid project creates successfully
- [ ] Empty name is rejected
- [ ] Name < min length is rejected
- [ ] Name > max length is rejected or truncated
- [ ] XSS in name is sanitized
- [ ] SQL injection in name is prevented
- [ ] Unicode in name is supported
- [ ] Special characters in name are handled
- [ ] Empty description is allowed (if optional)
- [ ] XSS in description is sanitized
- [ ] Very long description is handled
- [ ] Duplicate project name handling (per requirements)
- [ ] Modal opens when create button clicked
- [ ] Modal closes on cancel
- [ ] Modal closes on successful creation
- [ ] Form validation shows before submission
- [ ] Server validation errors are displayed
- [ ] Success message appears after creation
- [ ] New project appears in list

### Project Viewing
- [ ] Projects list loads correctly
- [ ] Empty state shows when no projects
- [ ] Project cards display all info
- [ ] Clicking project opens detail view
- [ ] Project detail shows all information
- [ ] Project detail handles missing data gracefully

### Project Editing
- [ ] Edit button opens edit form
- [ ] Form pre-populates with current data
- [ ] Name validation works on edit
- [ ] Description validation works on edit
- [ ] Save updates the project
- [ ] Cancel discards changes
- [ ] Changes reflect in list immediately

### Project Deletion
- [ ] Delete button shows confirmation
- [ ] Confirmation can be cancelled
- [ ] Confirmation deletes the project
- [ ] Deleted project removed from list
- [ ] Cannot delete another user's project

---

## Model Upload

### File Upload
- [ ] Valid file uploads successfully
- [ ] Empty file is rejected
- [ ] File too large is rejected
- [ ] Invalid file type is rejected
- [ ] File with malicious name is handled
- [ ] Path traversal in filename is prevented
- [ ] Unicode in filename is supported
- [ ] Upload progress is shown
- [ ] Upload can be cancelled
- [ ] Success message after upload
- [ ] Uploaded file appears in list
- [ ] File metadata is captured correctly

### File Management
- [ ] Uploaded files list loads
- [ ] File details can be viewed
- [ ] File can be downloaded
- [ ] File can be deleted
- [ ] Delete requires confirmation
- [ ] Cannot delete another user's files

---

## API Key Management

### Key Creation
- [ ] Valid key creates successfully
- [ ] Empty name is rejected
- [ ] Name too long is rejected
- [ ] XSS in name is sanitized
- [ ] Key secret is displayed once after creation
- [ ] Key secret can be copied
- [ ] Expiration date can be set
- [ ] Past expiration date is rejected
- [ ] Invalid date format is rejected
- [ ] Scopes can be selected (if applicable)
- [ ] Invalid scopes are rejected
- [ ] Modal/form closes after creation
- [ ] New key appears in list

### Key Management
- [ ] Keys list loads correctly
- [ ] Key details are displayed (not secret)
- [ ] Expired keys are marked
- [ ] Revoke button shows confirmation
- [ ] Revocation confirmation works
- [ ] Revoked key cannot be used
- [ ] Cannot revoke another user's key
- [ ] Key creation time displays correctly
- [ ] Key expiration time displays correctly

### Key Usage
- [ ] Valid key authenticates requests
- [ ] Invalid key is rejected (401)
- [ ] Expired key is rejected (401)
- [ ] Revoked key is rejected (401)
- [ ] Key with insufficient scope is rejected (403)
- [ ] Key respects rate limits

---

## Admin Functions

### User Management (Admin)
- [ ] User list loads for admin
- [ ] Non-admin cannot access user list
- [ ] Create user button works
- [ ] Create user form validates
- [ ] New user appears in list
- [ ] Edit user button works
- [ ] Edit user form pre-populates
- [ ] User updates save correctly
- [ ] Delete user requires confirmation
- [ ] User deletion works
- [ ] Cannot delete self

### Settings (Admin)
- [ ] Settings page loads
- [ ] Settings form pre-populates
- [ ] Settings validation works
- [ ] Settings updates save
- [ ] Invalid settings are rejected
- [ ] Success message after save

### Logs (Admin)
- [ ] Log viewer loads
- [ ] Logs display correctly
- [ ] Log filtering works
- [ ] Log search works
- [ ] Cannot access logs as non-admin

---

## HTMX Interactions

### Dynamic Forms
- [ ] Form validation triggers on blur
- [ ] Validation errors display inline
- [ ] Form submission via HTMX works
- [ ] Loading states display during requests
- [ ] Success responses update UI
- [ ] Error responses display messages
- [ ] Multiple rapid submissions handled

### Modals
- [ ] Modal opens on button click
- [ ] Modal content loads via HTMX
- [ ] Modal form submission works
- [ ] Modal closes on success
- [ ] Modal closes on cancel
- [ ] Modal closes on backdrop click
- [ ] Modal closes on ESC key
- [ ] Form resets when modal reopens

### Partial Updates
- [ ] List items update without page reload
- [ ] Item deletion updates list
- [ ] Item creation adds to list
- [ ] Item edit updates in place
- [ ] Loading indicators show during updates

---

## Error Handling

### Frontend Errors
- [ ] Network errors display user-friendly message
- [ ] Timeout errors are handled
- [ ] Invalid response format handled
- [ ] Console shows no errors during normal use
- [ ] Form validation errors are clear
- [ ] Success messages are visible

### Backend Errors
- [ ] 400 errors return validation details
- [ ] 401 errors redirect to login
- [ ] 403 errors show permission denied
- [ ] 404 errors show not found message
- [ ] 500 errors show generic error message
- [ ] Error format is consistent
- [ ] Stack traces not exposed in production

---

## Security

### Input Sanitization
- [ ] SQL injection prevented in all inputs
- [ ] XSS prevented in all user content
- [ ] Path traversal prevented in file operations
- [ ] Command injection prevented
- [ ] Null bytes handled
- [ ] CRLF injection prevented

### Authentication & Authorization
- [ ] Protected routes require authentication
- [ ] Admin routes require admin role
- [ ] Users can only access their own data
- [ ] API keys require valid authentication
- [ ] Sessions have appropriate timeout
- [ ] CSRF protection on state-changing operations

### Data Validation
- [ ] All required fields validated
- [ ] All length limits enforced
- [ ] All format validations work
- [ ] Type coercion is safe
- [ ] Boundary values handled correctly
- [ ] Database constraints enforced

---

## Browser Compatibility

- [ ] Chrome/Chromium latest
- [ ] Firefox latest
- [ ] Safari latest
- [ ] Edge latest
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

---

## Accessibility

- [ ] Keyboard navigation works
- [ ] Tab order is logical
- [ ] Focus indicators visible
- [ ] Form labels properly associated
- [ ] Error messages announced by screen readers
- [ ] ARIA labels present where needed
- [ ] Color contrast meets WCAG AA
- [ ] Alt text on images

---

## Performance

- [ ] Page load time < 2 seconds
- [ ] API responses < 500ms
- [ ] Form submission feedback < 500ms
- [ ] No unnecessary API calls
- [ ] Images optimized
- [ ] No console warnings/errors

---

## Notes Section

Date: ___________
Tester: ___________

Issues Found:
```
1. 
2.
3.
```

Blockers:
```
1.
2.
```

Sign-off: ___________
