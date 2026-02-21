#!/bin/bash
# Script to set up GitHub branch protection rules
# Requires: gh CLI to be authenticated

set -e

REPO="bodybybuddha/3DKenji"

echo "🔒 Setting up GitHub Branch Protection Rules"
echo "=============================================="
echo ""
echo "Repository: $REPO"
echo ""

# Check if gh is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ Error: GitHub CLI is not authenticated."
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Function to enable branch protection
setup_branch_protection() {
    local branch=$1
    local is_main=$2
    
    echo "🛡️  Setting up protection for: $branch"
    
    if [ "$is_main" = "true" ]; then
        # Strict protection for main branch
        gh api -X PUT "/repos/$REPO/branches/$branch/protection" \
            --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {},
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
EOF
    else
        # Less strict protection for dev branch
        gh api -X PUT "/repos/$REPO/branches/$branch/protection" \
            --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {},
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
EOF
    fi
    
    if [ $? -eq 0 ]; then
        echo "   ✅ $branch protection enabled"
    else
        echo "   ⚠️  Failed to set up $branch protection (may need admin rights)"
    fi
    echo ""
}

# Set up protection for main branch
if gh api "/repos/$REPO/branches/main" &>/dev/null; then
    setup_branch_protection "main" "true"
else
    echo "⚠️  Branch 'main' not found, skipping..."
    echo ""
fi

# Set up protection for dev branch
if gh api "/repos/$REPO/branches/dev" &>/dev/null; then
    setup_branch_protection "dev" "false"
else
    echo "⚠️  Branch 'dev' not found, skipping..."
    echo ""
fi

echo "🎉 Branch protection setup complete!"
echo ""
echo "📋 Summary:"
echo "  - main: Strict protection (reviews required, linear history, no deletions)"
echo "  - dev: Standard protection (no deletions, conversation resolution)"
echo ""
echo "⚙️  Review settings at: https://github.com/$REPO/settings/branches"
echo ""
echo "💡 Workflow:"
echo "  feature-branch → dev (via PR) → main (via PR)"
