# Contributing to Syllabify

This guide explains how to contribute code to the Syllabify project using our Git workflow.

## Overview

- **`dev` branch**: Development branch where all active work happens
- **`main` branch**: Production branch (protected, requires pull request)

## Daily Workflow: Working on Dev Branch

### 1. Clone the Repository (First Time Only)

```bash
git clone <repository-url>
cd syllabify
```

### 2. Switch to Dev Branch

Always work on the `dev` branch, not `main`:

```bash
# Check current branch
git branch

# Switch to dev branch (or create it if it doesn't exist locally)
git checkout dev

# If dev doesn't exist locally, fetch it from remote
git fetch origin
git checkout -b dev origin/dev
```

### 3. Make Sure You're Up to Date

Before starting work, pull the latest changes:

```bash
git pull origin dev
```

### 4. Make Your Changes

Create/edit files as needed for your feature or bug fix.

### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Or stage specific files
git add path/to/file

# Commit with a clear message
git commit -m "Description of your changes"
```

**Commit Message Tips:**
- Be clear and descriptive
- Use present tense ("Add feature" not "Added feature")
- Keep messages concise but informative

### 6. Push to Dev Branch

You can push directly to `dev` without a pull request:

```bash
git push origin dev
```

The CI/CD pipeline will automatically run tests and linting. Make sure your code passes these checks before moving to the next step.

---

## Creating a Pull Request to Main

When your work on `dev` is complete and tested, create a pull request to merge into `main` (production).

### 1. Make Sure Dev is Up to Date

```bash
# Switch to dev branch
git checkout dev

# Pull latest changes
git pull origin dev
```

### 2. Push Any Final Changes

```bash
# Make sure all your commits are pushed
git push origin dev
```

### 3. Create Pull Request on GitHub

1. Go to your repository on GitHub
2. Click the **"Pull requests"** tab
3. Click **"New pull request"**
4. Set the base branch to **`main`** and compare branch to **`dev`**
5. Fill in the pull request title and description:
   - **Title**: Brief summary of changes
   - **Description**: 
     - What changes were made?
     - Why were these changes needed?
     - Any additional notes for reviewers
6. Click **"Create pull request"**

### 4. Wait for CI Checks to Pass

GitHub Actions will automatically run:
- Backend tests and linting
- Frontend linting

**The pull request cannot be merged until these checks pass.** Check the status in the PR page.

### 5. Request Review

**IMPORTANT**: After creating your pull request:

1. Post a message in the Discord channel called pr-requests:
   - Mention that you've created a PR
   - Include the PR number or link
   - Ask someone to review it

2. Example message:
   ```
   Hey team! I've created PR #123 to merge dev into main. 
   Could someone please review it? Link: [PR URL]
   ```

3. Wait for approval:
   - At least **1 approval** is required before merging
   - Address any review comments if needed
   - Make changes if requested, then push to `dev` again (the PR will update automatically)

### 6. Merge the Pull Request

Once approved and all checks pass:

1. Click **"Merge pull request"** on the GitHub PR page
2. Confirm the merge
3. The changes from `dev` will be merged into `main`

---

## Troubleshooting

### "Your branch is behind 'origin/dev'"

This means someone else pushed changes to dev. Pull and merge:

```bash
git pull origin dev
```

If there are conflicts, resolve them, then:
```bash
git add .
git commit -m "Merge latest dev changes"
git push origin dev
```

### CI Checks Failing

If the GitHub Actions checks fail:

1. Check the error logs in the PR
2. Fix the issues locally
3. Commit and push to `dev` again:
   ```bash
   # Make your fixes
   git add .
   git commit -m "Fix linting/tests"
   git push origin dev
   ```
4. The PR will automatically update with the new changes

### Accidentally Committed to Main

If you accidentally committed to `main`:

```bash
# Switch to dev
git checkout dev

# Cherry-pick your commit
git cherry-pick <commit-hash>

# Push to dev
git push origin dev

# Reset main to match remote (be careful!)
git checkout main
git reset --hard origin/main
git push origin main --force  # Only do this if absolutely necessary
```

---

## Best Practices

1. **Always work on `dev`**, never commit directly to `main`
2. **Pull before you push** to avoid merge conflicts
3. **Test locally** when possible before pushing
4. **Write clear commit messages**
5. **Keep PRs focused** - one feature or bug fix per PR when possible
6. **Respond to review comments** promptly
7. **Don't merge your own PR** unless explicitly allowed - get a teammate to review

---

## Quick Reference

```bash
# Daily workflow
git checkout dev
git pull origin dev
# ... make changes ...
git add .
git commit -m "Your message"
git push origin dev

# Create PR on GitHub (web interface)
# Request review in Discord
# Merge after approval
```

---

## Questions?

If you run into issues or have questions:
- Ask in the team Discord channel
- Ask ChatGPT or your favorite AI/LLM
- Check the project README.md for more context