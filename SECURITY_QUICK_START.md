# 🚨 Security Quick Start - READ THIS FIRST

## ⚡ 3-Minute Action Plan

### Step 1: Clean Git History (NOW)
```bash
cd /Users/dinokage/dev/fazri-analyzer
./clean_secrets.sh
# Type 'yes' when prompted
```

### Step 2: Rotate Credentials (IMMEDIATELY)

**Google API Key** (2 min):
1. Visit: https://console.cloud.google.com/apis/credentials
2. Delete key: `[REDACTED - Check your .env.backup file]`
3. Create new key → Copy to clipboard

**GitLab Token** (1 min):
1. Visit: https://gitlab.com/-/profile/personal_access_tokens
2. Revoke: `[REDACTED - Check your .env.backup file]`
3. Create new token → Copy to clipboard

### Step 3: Update .env File
```bash
cd backend
nano .env  # or your preferred editor
```

Replace these lines:
```bash
# OLD - DELETE THESE
GOOGLE_API_KEY=[REDACTED - Check your .env.backup file]
GITLAB_TOKEN=[REDACTED - Check your .env.backup file]
NEO4J_PASSWORD=[REDACTED]
POSTGRES_PASSWORD=[REDACTED]
SECRET_KEY=REMOVED_FROM_HISTORY_USE_ENV_VARS

# NEW - PASTE YOUR NEW VALUES
GOOGLE_API_KEY=<paste-new-key-here>
GITLAB_TOKEN=<paste-new-token-here>
NEO4J_PASSWORD=<generate-strong-password>
POSTGRES_PASSWORD=<generate-strong-password>
SECRET_KEY=GENERATE_NEW_SECRET_KEY_HERE
```

### Step 4: Force Push Clean Repository
```bash
git push origin --force --all
git push origin --force --tags
```

### Step 5: Verify Security
```bash
# Should return nothing
git log --all -p | grep "your-secret-key-here"

# Should return nothing  
git log --all -p | grep "AIzaSyBj"

# Should return nothing
git log --all -p | grep "glpat-"
```

---

## ✅ Checklist

- [ ] Ran `./clean_secrets.sh` and typed 'yes'
- [ ] Deleted old Google API key
- [ ] Created new Google API key
- [ ] Revoked old GitLab token
- [ ] Created new GitLab token
- [ ] Updated backend/.env with new credentials
- [ ] Changed database passwords
- [ ] Force pushed to origin
- [ ] Verified secrets removed from git history

---

## 📚 Detailed Guides

- **Full Details**: See `GIT_CLEANUP_SUMMARY.md`
- **Rotation Steps**: See `CREDENTIAL_ROTATION_GUIDE.md`
- **Template**: See `backend/.env.example`

---

## 🆘 Quick Fixes

**Script won't run?**
```bash
chmod +x clean_secrets.sh
```

**Force push rejected?**
```bash
# You may need to disable branch protection temporarily
git push origin --force-with-lease --all
```

**Lost your new SECRET_KEY?**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

**Time to complete:** ~10 minutes
**Status:** 🔴 CRITICAL - Do not deploy until complete
