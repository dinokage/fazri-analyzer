# 🔐 CRITICAL: Credential Rotation Guide

## ⚠️ IMMEDIATE ACTION REQUIRED

The following credentials were exposed in your `.env` file and MUST be rotated immediately:

### 1. Google API Key (CRITICAL)
**Exposed Key:** `[REDACTED - Check your .env.backup file]`

**Actions Required:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Find the API key `[REDACTED - Check your .env.backup file]`
3. **DELETE** this key immediately
4. Create a NEW API key
5. Restrict the new key to only required APIs (Gemini API)
6. Add IP restrictions if possible
7. Update your `backend/.env` file with the new key

### 2. GitLab Personal Access Token (CRITICAL)
**Exposed Token:** `[REDACTED - Check your .env.backup file]`

**Actions Required:**
1. Go to https://gitlab.com/-/profile/personal_access_tokens
2. **REVOKE** the token `[REDACTED - Check your .env.backup file]`
3. Create a NEW personal access token with minimal required scopes
4. Update your `backend/.env` file with the new token

### 3. Database Passwords (HIGH PRIORITY)
**Exposed Passwords:**
- Neo4j: `[REDACTED]`
- PostgreSQL: `[REDACTED]`

**Actions Required:**
1. Change Neo4j password:
   ```bash
   docker exec -it <neo4j_container> cypher-shell
   ALTER CURRENT USER SET PASSWORD FROM '[REDACTED]' TO 'NEW_STRONG_PASSWORD';
   ```

2. Change PostgreSQL password:
   ```bash
   docker exec -it <postgres_container> psql -U postgres
   ALTER USER postgres WITH PASSWORD 'NEW_STRONG_PASSWORD';
   ```

3. Update your `backend/.env` file with new passwords

### 4. SECRET_KEY (HIGH PRIORITY)
**Exposed Default:** `REMOVED_FROM_HISTORY_USE_ENV_VARS`

**Actions Required:**
1. A new SECRET_KEY has been generated: `GENERATE_NEW_SECRET_KEY_HERE`
2. Add this to your `backend/.env` file
3. Or generate a new one: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

## 📝 Updated .env File Template

Copy this to `backend/.env` and fill in the NEW credentials:

```bash
# SECURITY: NEVER commit this file to git!

# Neo4j Configuration
NEO4J_URI=neo4j://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=NEW_STRONG_PASSWORD_HERE

# PostgreSQL Configuration
POSTGRES_SERVER=postgres_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=NEW_STRONG_PASSWORD_HERE
POSTGRES_DB=ethos_iitg
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Application Settings
DEBUG=false
TESTING=false
LOG_LEVEL=INFO
SECRET_KEY=GENERATE_NEW_SECRET_KEY_HERE
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Origins (comma-separated) - LOCK THIS DOWN!
BACKEND_CORS_ORIGINS=http://localhost:3000

# Chatbot Configuration
GOOGLE_API_KEY=NEW_GOOGLE_API_KEY_HERE
USE_VERTEX_AI=false
VERTEX_PROJECT_ID=vantammayilu
VERTEX_LOCATION=us-central1
CHATBOT_MODEL=gemini-2.0-flash

# GitLab Integration
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=NEW_GITLAB_TOKEN_HERE
GITLAB_PROJECT_ID=fazri8594547/fazri-analyzer
```

---

## 🔒 Git History Cleanup

The hardcoded `SECRET_KEY` in `backend/config.py` was committed to git history.

**To clean git history:**

```bash
# WARNING: This rewrites git history!
# Make sure all team members are aware

cd /Users/dinokage/dev/fazri-analyzer
./clean_secrets.sh
```

After running the script:
1. Force push to remote: `git push origin --force --all`
2. Force push tags: `git push origin --force --tags`
3. Notify all team members to re-clone the repository

---

## ✅ Verification Checklist

- [ ] Google API key deleted and new one created
- [ ] GitLab token revoked and new one created
- [ ] Neo4j password changed
- [ ] PostgreSQL password changed
- [ ] New SECRET_KEY added to .env
- [ ] backend/.env updated with all new credentials
- [ ] CORS origins locked down to specific domains
- [ ] Git history cleaned (run clean_secrets.sh)
- [ ] Force pushed to remote repository
- [ ] Team members notified to re-clone
- [ ] Old credentials confirmed non-functional

---

## 🚨 Additional Security Measures

1. **Enable 2FA** on your Google Cloud and GitLab accounts
2. **Set up API key restrictions** in Google Cloud Console
3. **Limit GitLab token scopes** to minimum required
4. **Use environment-specific secrets** (dev, staging, prod)
5. **Set up secret scanning** in CI/CD pipeline
6. **Regular credential rotation** (every 90 days minimum)

---

## 📞 If Credentials Were Used Maliciously

If you suspect the exposed credentials were accessed:

1. Check Google Cloud audit logs for unauthorized API usage
2. Check GitLab access logs for unauthorized repository access
3. Review database logs for suspicious queries
4. Consider rotating ALL credentials, not just exposed ones
5. Enable monitoring and alerting on all services

---

**Last Updated:** 2026-03-22
**Status:** 🔴 CRITICAL - ACTION REQUIRED IMMEDIATELY
