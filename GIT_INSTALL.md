# Git Installation Guide

## Step 1: Download Git

Download the latest version from: https://git-scm.com/download/win

## Step 2: Run the Installer

1. Open the downloaded file: `Git-3.x.x.x-64-bit.exe`
2. Click "Next" through all installation steps
3. **Important choices during installation:**

   **Default editor:**
   - Choose: "Git Bash" or "Nano"
   - Or let Git detect your default

   **PATH environment:**
   - Choose: "Git from the command line and also from 3rd-party software"
   - This is recommended

   **HTTPS transport backend:**
   - Choose: "Use the OpenSSL library"

   **Credential helper:**
   - Choose: "Windows Credential Manager"
   - Or "None" (you'll use GitHub login)

   **Line ending conversions:**
   - Choose: "Checkout Windows-style, commit Unix-style line endings"

   **Terminal emulator:**
   - Choose: "Use Git Bash"

4. Click "Install" and wait for completion
5. Click "Finish" when done

## Step 3: Verify Installation

Open Command Prompt or PowerShell and run:
```bash
git --version
```

You should see: `git version 2.x.x.x`

## Step 4: Initialize the Repository

Once Git is installed, run these commands in your terminal:

```bash
cd "C:/Users/abina/AppData/Local/Temp/glm-token-test"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: GLM Code Graph token reduction demonstration"

# Create GitHub repository (you'll do this manually on GitHub.com)
# Then add remote and push:
git remote add origin https://github.com/YOUR_USERNAME/glm-code-graph-demo.git
git branch -M main
git push -u origin main
```

## Step 5: Login to GitHub (When asked)

When you run `git push`, Git will ask for credentials. You have options:

**Option A: HTTPS with Personal Access Token (Easiest)**
1. Go to: https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo` (full control of private repositories)
4. Copy the token
5. When Git asks for username: use your GitHub username
6. When Git asks for password: paste the token

**Option B: SSH (Recommended for frequent use)**
1. Generate SSH key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Copy public key: `cat ~/.ssh/id_ed25519.pub`
3. Add to GitHub: https://github.com/settings/ssh/new
4. Test connection: `ssh -T git@github.com`
5. Use SSH URL: `git@github.com:YOUR_USERNAME/glm-code-graph-demo.git`

## Step 6: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `glm-code-graph-demo`
3. Description: "Token reduction demonstration for GLM Code Graph"
4. Select **Private** (as requested)
5. Click "Create repository"
6. Copy the repository URL

## Step 7: Push to GitHub

```bash
cd "C:/Users/abina/AppData/Local/Temp/glm-token-test"

# Add remote
git remote add origin YOUR_GITHUB_REPO_URL

# Push
git push -u origin main
```

## Troubleshooting

### Git not found after installation
- Restart your terminal/command prompt
- Restart your computer

### Authentication errors
- Make sure you're using the token (not your password)
- Check that the token has the `repo` scope

### Push rejected
- Make sure you've created the GitHub repository first
- Check the repository URL is correct

---

**You're all set!** Once Git is installed and you've created your GitHub repository, just run the push command.
