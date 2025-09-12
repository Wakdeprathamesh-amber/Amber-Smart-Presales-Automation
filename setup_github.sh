#!/bin/bash

# Amber Smart Presales - GitHub Setup Script
# This script helps set up the repository for GitHub deployment

echo "🚀 Setting up Amber Smart Presales for GitHub deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
else
    echo "✅ Git repository already initialized"
fi

# Add all files
echo "📁 Adding files to git..."
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "ℹ️  No changes to commit"
else
    echo "💾 Committing changes..."
    git commit -m "Initial commit: Amber Student Smart Presales POC with bulk upload and calling features"
fi

# Check if remote origin exists
if git remote get-url origin >/dev/null 2>&1; then
    echo "✅ Remote origin already configured"
    echo "📍 Current remote: $(git remote get-url origin)"
else
    echo "⚠️  No remote origin configured"
    echo "To add a remote origin, run:"
    echo "git remote add origin https://github.com/yourusername/amber-smart-presales.git"
    echo "git push -u origin main"
fi

echo ""
echo "🎉 Setup complete! Next steps:"
echo "1. Create a GitHub repository"
echo "2. Add the remote origin: git remote add origin <your-repo-url>"
echo "3. Push to GitHub: git push -u origin main"
echo "4. Deploy to Render using the instructions in DEPLOYMENT.md"
echo ""
echo "📚 See DEPLOYMENT.md for detailed deployment instructions"
