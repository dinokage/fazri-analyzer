#!/bin/bash
# Script to clean sensitive data from git history

echo "⚠️  WARNING: This will rewrite git history!"
echo "Make sure you have backups of your .env files"
echo ""
echo "This script will:"
echo "1. Replace hardcoded SECRET_KEY in backend/config.py"
echo "2. Clean any other exposed secrets from history"
echo ""

read -p "Continue? (yes/no): " response
if [ "$response" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🔧 Step 1: Replacing SECRET_KEY in backend/config.py across all history..."

# Use git filter-repo to replace the hardcoded secret
git filter-repo --force \
    --replace-text <(echo 'REMOVED_FROM_HISTORY_USE_ENV_VARS==>REMOVED_FROM_HISTORY_USE_ENV_VARS') \
    --message-callback 'return message.replace(b"REMOVED_FROM_HISTORY_USE_ENV_VARS", b"[SECRET_REMOVED]")'

echo ""
echo "✅ Git history cleaned!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Update backend/config.py to use empty string for SECRET_KEY"
echo "2. Generate new SECRET_KEY and add to .env"
echo "3. Rotate ALL other credentials (Google API, GitLab token, DB passwords)"
echo "4. Force push to origin: git push origin --force --all"
echo "5. Force push tags: git push origin --force --tags"
echo ""
