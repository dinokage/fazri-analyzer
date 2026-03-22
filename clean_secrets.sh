#!/bin/bash
# Script to clean sensitive data from git history

echo "⚠️  WARNING: This will rewrite git history!"
echo "Make sure you have backups of your .env files"
echo ""
echo "This script will:"
echo "1. Replace hardcoded SECRET_KEY in backend/config.py"
echo "2. Remove exposed credentials from markdown documentation files"
echo "3. Clean commit messages containing secrets"
echo ""

read -p "Continue? (yes/no): " response
if [ "$response" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🔧 Creating replacement patterns file..."

# Create a temporary file with all secret replacements
cat > /tmp/secrets_to_remove.txt << 'EOF'
[REDACTED - Check your .env.backup file]==>[REDACTED - Check your .env.backup file]
[REDACTED - Check your .env.backup file]==>[REDACTED - Check your .env.backup file]
[REDACTED]==>[REDACTED]
[REDACTED]==>[REDACTED]
GENERATE_NEW_SECRET_KEY_HERE==>GENERATE_NEW_SECRET_KEY_HERE
REMOVED_FROM_HISTORY_USE_ENV_VARS==>REMOVED_FROM_HISTORY_USE_ENV_VARS
EOF

echo "🔧 Step 1: Replacing secrets in all files across git history..."

# Use git filter-repo to replace all secrets
git filter-repo --force \
    --replace-text /tmp/secrets_to_remove.txt

echo ""
echo "🔧 Step 2: Cleaning commit messages..."

# Clean any secrets that might be in commit messages
git filter-repo --force \
    --message-callback '
message = message.replace(b"[REDACTED - Check your .env.backup file]", b"[GOOGLE_API_KEY_REDACTED]")
message = message.replace(b"[REDACTED - Check your .env.backup file]", b"[GITLAB_TOKEN_REDACTED]")
message = message.replace(b"[REDACTED]", b"[PASSWORD_REDACTED]")
message = message.replace(b"[REDACTED]", b"[PASSWORD_REDACTED]")
message = message.replace(b"GENERATE_NEW_SECRET_KEY_HERE", b"[SECRET_KEY_REDACTED]")
message = message.replace(b"REMOVED_FROM_HISTORY_USE_ENV_VARS", b"[SECRET_REMOVED]")
return message
'

# Clean up temporary file
rm /tmp/secrets_to_remove.txt

echo ""
echo "✅ Git history cleaned successfully!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Verify cleanup: git log --all -p | grep -E '(AIzaSy|glpat-|Pressword)'"
echo "   (should return nothing)"
echo "2. Rotate ALL credentials immediately (see CREDENTIAL_ROTATION_GUIDE.md)"
echo "3. Update backend/.env with new credentials"
echo "4. Force push to origin:"
echo "   git push origin --force --all"
echo "   git push origin --force --tags"
echo "5. Notify team members to re-clone the repository"
echo ""
echo "🔐 Security Reminders:"
echo "- Delete old Google API key at https://console.cloud.google.com/apis/credentials"
echo "- Revoke old GitLab token at https://gitlab.com/-/profile/personal_access_tokens"
echo "- Change database passwords in Docker containers"
echo "- Generate new SECRET_KEY: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
echo ""
