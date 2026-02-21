# GitHub Repository Setup Guide

This guide will help you configure the 3DKenji repository with proper branch protection, CI/CD, and workflows.

## 🚀 Quick Setup (Automated)

Run the automated setup script:

```bash
.github/setup_branch_protection.sh
```

This will configure:
- ✅ Branch protection for `main` (strict)
- ✅ Branch protection for `dev` (standard)
- ✅ Required status checks
- ✅ Pull request reviews
- ✅ Prevent branch deletion

## 📋 What Was Configured

### 1. Branch Protection Rules

#### `main` Branch (Production)
- ✅ Requires pull request before merging
- ✅ Requires 1 approval from code owners
- ✅ Requires status checks to pass (CI tests)
- ✅ Dismisses stale reviews on new commits
- ✅ Requires conversation resolution
- ✅ Requires linear history (no merge commits)
- ✅ Prevents force pushes
- ✅ Prevents deletion
- ✅ Enforces rules for administrators

#### `dev` Branch (Integration)
- ✅ Requires pull request before merging
- ✅ Requires status checks to pass (CI tests)
- ✅ Requires conversation resolution
- ✅ Prevents force pushes
- ✅ Prevents deletion
- ⚠️ No review requirement (fast iteration)

### 2. GitHub Actions CI/CD

**File**: `.github/workflows/ci.yml`

**Triggers**:
- Push to `main`, `dev`, or `feature/**` branches
- Pull requests to `main` or `dev`

**Jobs**:
1. **Test Job**:
   - Runs pytest with coverage
   - Uses PostgreSQL service container
   - Validates all 52+ tests pass
   - Reports code coverage

2. **Lint Job** (optional):
   - Runs ruff for code quality
   - Checks formatting

### 3. Code Owners

**File**: `.github/CODEOWNERS`

- Automatically requests review from @bodybybuddha
- Applies to all files by default
- Special rules for critical paths (backend, migrations, docs)

### 4. Templates

#### Pull Request Template
**File**: `.github/pull_request_template.md`

Provides structured PR description with:
- Change type classification
- Testing checklist
- Code quality checklist

#### Issue Templates
**Files**: 
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`

Standardized formats for:
- Bug reports with reproduction steps
- Feature requests with use cases

## 🔄 Development Workflow

### Standard Flow

```
feature/my-feature → dev → main
        ↓              ↓      ↓
       PR            PR    Release
```

### Detailed Steps

#### 1. Start a Feature
```bash
# Make sure you're up to date
git checkout dev
git pull origin dev

# Create feature branch
git checkout -b feature/my-awesome-feature

# Work on your feature
git add .
git commit -m "Add awesome feature"
git push origin feature/my-awesome-feature
```

#### 2. Create Pull Request to `dev`
```bash
# Using gh CLI
gh pr create --base dev --head feature/my-awesome-feature

# Or via GitHub UI
# Go to: https://github.com/bodybybuddha/3DKenji/compare
```

#### 3. Merge to `dev` (After Approval & CI Pass)
- CI tests must pass ✅
- Code review approved (if required) ✅
- All conversations resolved ✅
- Click "Merge pull request" on GitHub

#### 4. Create Release PR to `main`
```bash
# From dev branch, create PR to main
gh pr create --base main --head dev --title "Release v1.1.0"
```

#### 5. Merge to `main` (Production Release)
- CI tests must pass ✅
- **Requires 1 approval** (important!) ✅
- All conversations resolved ✅
- Click "Merge pull request" on GitHub

#### 6. Tag the Release
```bash
git checkout main
git pull origin main
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

## 🛠️ Manual Configuration (Optional)

If you need to adjust settings manually:

### Via GitHub UI

1. Go to: https://github.com/bodybybuddha/3DKenji/settings/branches
2. Click "Add rule" or edit existing rules
3. Configure as needed

### Via API (Advanced)

```bash
# Get current protection status
gh api repos/bodybybuddha/3DKenji/branches/main/protection

# Update protection (use script for easier management)
gh api -X PUT repos/bodybybuddha/3DKenji/branches/main/protection \
  --input protection_config.json
```

## 🔍 Verification

### Check Branch Protection Status

```bash
# View main branch protection
gh api repos/bodybybuddha/3DKenji/branches/main/protection

# View dev branch protection
gh api repos/bodybybuddha/3DKenji/branches/dev/protection
```

### Test CI Pipeline

```bash
# Push to a feature branch
git checkout -b test/ci-check
git commit --allow-empty -m "Test CI"
git push origin test/ci-check

# Check workflow status
gh run list --branch test/ci-check
```

## 📊 Repository Status

View at: https://github.com/bodybybuddha/3DKenji

- **Branch Protection**: ✅ Configured
- **CI/CD Pipeline**: ✅ Active
- **Code Owners**: ✅ Set
- **PR Template**: ✅ Ready
- **Issue Templates**: ✅ Ready

## 🔒 Security Best Practices

1. **Never commit directly to `main`** - Always use PRs
2. **Keep `dev` stable** - Test thoroughly before merging
3. **Review all PRs** - Even your own (self-review)
4. **Run tests locally** - Before pushing: `make test`
5. **Keep dependencies updated** - Review Dependabot alerts
6. **Rotate secrets regularly** - Update GitHub secrets as needed

## 🆘 Troubleshooting

### "Branch is protected" Error

**Solution**: Create a pull request instead of pushing directly.

```bash
git checkout -b feature/my-fix
git push origin feature/my-fix
gh pr create --base dev
```

### CI Tests Failing

**Solution**: Run tests locally first.

```bash
make test
# Fix any failures, then push
```

### Can't Delete Feature Branch

**Solution**: Delete via GitHub UI after PR is merged, or use:

```bash
git push origin --delete feature/branch-name
```

## 📚 Additional Resources

- [GitHub Branch Protection Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Code Owners Guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

## ✅ Next Steps

1. **Run the setup script**: `.github/setup_branch_protection.sh`
2. **Verify in GitHub UI**: Check settings/branches
3. **Test the workflow**: Create a test PR
4. **Document team workflows**: Share this guide with contributors

---

**Setup Complete!** Your repository now has enterprise-grade branch protection and CI/CD. 🎉
