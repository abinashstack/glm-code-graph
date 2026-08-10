# Setup and Push Instructions

This guide will help you set up the repository and push it to GitHub.

## Step 1: Install Git (if not already installed)

### Windows
1. Download from: https://git-scm.com/download/win
2. Run installer and follow the prompts
3. Restart your terminal/command prompt

### macOS
```bash
brew install git
```

### Linux
```bash
sudo apt install git  # Debian/Ubuntu
# or
sudo yum install git  # CentOS/RHEL
```

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `glm-code-graph-demo`
3. Description: "Token reduction demonstration for GLM Code Graph"
4. Select **Public** (or Private if you prefer)
5. Click **Create repository**

## Step 3: Initialize Git Repository

Open terminal in the `glm-token-test` directory and run:

```bash
cd "C:/Users/abina/AppData/Local/Temp/glm-token-test"

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: GLM Code Graph token reduction demonstration"

# Check status
git status
```

## Step 4: Push to GitHub

### Option A: Using HTTPS (easiest)

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/glm-code-graph-demo.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Option B: Using SSH (recommended)

```bash
# Add remote
git remote add origin git@github.com:YOUR_USERNAME/glm-code-graph-demo.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 5: Verify

1. Go to your GitHub repository
2. You should see all files and the README
3. Click "Code" button to get your repository URL

## Quick Reference Commands

```bash
# Inside glm-token-test directory
cd "C:/Users/abina/AppData/Local/Temp/glm-token-test"

# View all files
ls -la

# Run verification
python count_bytes.py

# Commit changes
git add .
git commit -m "Your message"

# Push
git push
```

## Troubleshooting

### Git not found
- Make sure Git is installed
- Restart your terminal
- Check PATH environment variable

### Authentication errors
- Use Personal Access Token for HTTPS: https://github.com/settings/tokens
- Or use SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### Push rejected
- Pull latest changes first: `git pull origin main`
- Merge conflicts? Resolve them and commit again

## Alternative: Use GitHub CLI

Install GitHub CLI: https://cli.github.com/

```bash
gh auth login
git push
```

## Next Steps

After pushing to GitHub:

1. **Share the repository**
   - Copy the URL: `https://github.com/YOUR_USERNAME/glm-code-graph-demo`
   - Share with others

2. **Customize**
   - Change the repository description
   - Add topics/tags (e.g., "glm-4", "code-review", "token-optimization")

3. **Add your changes**
   - Modify any files
   - Commit and push: `git add . && git commit -m "Update" && git push`

4. **Invite collaborators**
   - Go to Settings → Collaborators
   - Add people who can edit

## Need Help?

If you encounter any issues:
1. Check the troubleshooting section above
2. Visit GitHub's help docs: https://docs.github.com
3. Search for common Git errors online
