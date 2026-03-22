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
2. Delete the exposed API key (see .env.backup for value)
3. Create new key → Copy to clipboard

**GitLab Token** (1 min):
1. Visit: https://gitlab.com/-/profile/personal_access_tokens
2. Revoke the exposed token (see .env.backup for value)
3. Create new token → Copy to clipboard

### Step 3: Update .env File
```bash
cd backend
nano .env  # or your preferred editor
```

Replace these lines with your NEW values:
```bash
# Generate a new SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update these in .env
GOOGLE_API_KEY=<paste-new-key-here>
GITLAB_TOKEN=<paste-new-token-here>
NEO4J_PASSWORD=<generate-strong-password>
POSTGRES_PASSWORD=<generate-strong-password>
SECRET_KEY=<paste-generated-key-here>
```

### Step 4: Force Push Clean Repository
```bash
git push origin --force --all
git push origin --force --tags
```

### Step 5: Verify Security
```bash
# All of these should return nothing
git log --all -p | grep "your-secret-key-here"
git log --all -p | grep "AIzaSy"
git log --all -p | grep "glpat-"
```

---

## ✅ Checklist

- [ ] Ran `./clean_secrets.sh` and typed 'yes'
- [ ] Deleted old Google API key
- [ ] Created new Google API key
- [ ] Revoked old GitLab token
- [ ] Created new GitLab token
- [ ] Generated new SECRET_KEY
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

**Need to generate strong password?**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

**Time to complete:** ~10 minutes
**Status:** 🟢 Documentation sanitized - Ready to execute cleanup
