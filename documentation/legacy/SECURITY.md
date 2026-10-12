# Security Guide

⚠️ **IMPORTANT SECURITY INFORMATION** ⚠️

## Critical Security Issue - API Key Exposure

An OpenAI API key was exposed in the `.env.example` file that was committed to the repository. Follow the steps below to secure your account.

---

## 🔴 Immediate Actions Required

### Step 1: Rotate Your API Key (URGENT)

Your exposed API key needs to be revoked immediately:

1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Log in to your account
3. Find the exposed key (or all keys to be safe)
4. Click **Delete** or **Revoke**
5. Create a new API key
6. Update your local `.env` file with the new key

**After creating new key**:

```bash
# Update your local .env file
# DO NOT commit this file to Git!
OPENAI_API_KEY=sk-your-new-key-here
```

### Step 2: Clean Git History

Remove the exposed key from repository history:

```bash
# Option A: Remove entire file from history (Recommended for production)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Force push to update remote
git push origin --force --all
git push origin --force --tags

# Option B: Remove only the line with key (Advanced)
# Use BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/
```

### Step 3: Protect Repository

Prevent this from happening again:

```bash
# Create .gitignore (already created)
cat .gitignore | grep -E "^\.env"

# Verify .env files are ignored
git status | grep ".env"
# Should output nothing
```

---

## 📋 Best Practices for Secrets Management

### What to NEVER Commit

```
❌ NEVER commit:
   - .env (actual environment file with real values)
   - passwords, API keys, tokens
   - database credentials
   - private keys, certificates
   - AWS access keys, database URLs with passwords
```

### What to ALWAYS Commit

```
✅ ALWAYS commit:
   - .env.example (template with placeholders)
   - .gitignore (prevents accidental commits)
   - SECURITY.md (this file)
   - Documentation and configuration structure
```

### File Structure

Correct structure for your project:

```
aiforus/
├── .env                    # ❌ NEVER commit (in .gitignore)
├── .env.local             # ❌ NEVER commit (in .gitignore)
├── .env.example           # ✅ COMMIT (template only)
├── .gitignore             # ✅ COMMIT (security rules)
├── SECURITY.md            # ✅ COMMIT (this file)
├── config.yaml            # ✅ COMMIT (no secrets)
└── ...
```

---

## 🔐 Managing Secrets Securely

### Local Development

```bash
# 1. Copy template to actual file
cp .env.example .env

# 2. Edit .env with YOUR actual API keys
nano .env        # Linux/macOS
notepad .env     # Windows

# 3. Verify .env is in .gitignore
cat .gitignore | grep "^.env$"

# 4. Verify git won't commit it
git status | grep ".env"  # Should NOT show .env
```

### Production Deployment

**Option A: Environment Variables via Platform**

```bash
# AWS Lambda
export OPENAI_API_KEY=sk-...
export GOOGLE_MAPS_API_KEY=...

# Heroku
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set GOOGLE_MAPS_API_KEY=...

# Google Cloud
gcloud secrets create openai-api-key --data-file=-
gcloud secrets create google-maps-api-key --data-file=-
```

**Option B: Secrets Manager**

```bash
# AWS Secrets Manager
aws secretsmanager create-secret --name vision-assistant/openai --secret-string sk-...

# Google Secret Manager
gcloud secrets create openai-key --data-file=-

# Azure Key Vault
az keyvault secret set --vault-name visio-vault --name openai-key --value sk-...
```

**Option C: Docker Secrets**

```dockerfile
FROM python:3.11
# ...
RUN --mount=type=secret,id=openai_key \
    export OPENAI_API_KEY=$(cat /run/secrets/openai_key)
```

### GitHub Actions / CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy
on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Use GitHub Secrets (never hardcode!)
      - name: Deploy
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python app.py
```

Set repository secrets:

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add: `OPENAI_API_KEY` = `sk-...`
4. Add: `DATABASE_URL` = `postgresql://...`

---

## 🛡️ Security Checklist

- [ ] API key rotated (Step 1 above)
- [ ] Git history cleaned (Step 2 above)
- [ ] `.gitignore` created and committed
- [ ] `.env` file exists locally but NOT in Git
- [ ] `.env.example` only contains placeholders
- [ ] No hardcoded secrets in source code
- [ ] No secrets in comments or logs
- [ ] Team members aware of security practices
- [ ] CI/CD uses GitHub Secrets (not env files)

---

## 🔍 Finding Exposed Secrets

### Scan Repository for Secrets

```bash
# Install detection tools
pip install detect-secrets
npm install -g truffleHog

# Scan repository
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline

# Or use TruffleHog
truffleHog filesystem . --json
```

### Audit Recent Commits

```bash
# Check what was committed recently
git log --oneline -10

# See what changed
git show <commit-hash>

# Search for patterns (API keys)
git log -p | grep -i "sk-proj"
git log -p | grep -i "api_key"
```

---

## 📚 Environment Variables Explained

### Why Use `.env` Files?

✅ **Advantages**:

- Separates configuration from code
- Different values for dev/staging/production
- Easy to change without code changes
- Secure (not in version control)
- Works with Docker, cloud platforms

❌ **What NOT to do**:

- Hardcode in source files
- Commit to repository
- Store in public configurations
- Share via email or chat

### .env.example Purpose

The `.env.example` file is a **template**:

```bash
# .env.example (IN REPOSITORY)
OPENAI_API_KEY=sk-your-key-here       # Placeholder
GOOGLE_MAPS_API_KEY=your-key-here     # Placeholder
DATABASE_URL=sqlite:///database.db    # Example connection

# .env (NOT in repository - locally created)
OPENAI_API_KEY=sk-proj-fJKlHNevQ...   # Your actual key
GOOGLE_MAPS_API_KEY=AI23ksd...        # Your actual key
DATABASE_URL=postgresql://user:pass@localhost/db
```

**Workflow**:

1. Developer receives `.env.example` from repo
2. Creates own `.env` file locally
3. Fills in actual values
4. Never commits `.env` to Git
5. When deploying: use platform-specific secrets management

---

## 🚨 If Secrets Are Exposed

### Immediate Steps (In Order)

1. **STOP** - Don't panic, but be quick
2. **REVOKE** - Immediately disable exposed credential
3. **CLEAN** - Remove from Git history
4. **RESET** - Create new credentials
5. **UPDATE** - Deploy with new credentials
6. **VERIFY** - Confirm old credentials don't work
7. **AUDIT** - Check for unauthorized access

### Check for Misuse

```bash
# For OpenAI API
# Visit: https://platform.openai.com/account/api-keys
# Check Usage tab for suspicious activity

# Review API logs
# Check if calls were made from unexpected IP addresses

# For database credentials
# Check logs for failed authentication attempts
# Change database password immediately
```

### Post-Incident

1. **Document** what happened
2. **Review** security policies
3. **Update** team training
4. **Monitor** for future exposure
5. **Implement** detection tools

---

## 🔧 Tools for Secret Management

### Local Development

- **direnv**: Auto-load `.env` files
- **python-dotenv**: Load from `.env` in Python
- **docker-compose**: Build with secrets

### Production

- **GitHub Actions Secrets** - For CI/CD
- **AWS Secrets Manager** - For AWS deployment
- **Google Secret Manager** - For GCP deployment
- **HashiCorp Vault** - For enterprise
- **1Password / LastPass** - Team secret sharing

### Detection & Scanning

- **detect-secrets** - Scan for secrets
- **TruffleHog** - Find secrets in Git history
- **SAST Tools** - Static code analysis
- **Pre-commit hooks** - Prevent commits

---

## 📖 Additional Resources

### Security Standards

- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12 Factor App - Config](https://12factor.net/config)
- [CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)

### OpenAI Security

- [OpenAI API Security](https://platform.openai.com/docs/guides/security)
- [Managing API Keys](https://platform.openai.com/api-keys)

### Git Security

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

## ✅ Security Compliance

This project follows:

- ✅ OWASP Secure Coding Practices
- ✅ 12-Factor App Methodology
- ✅ CWE/OWASP Top 10 Guidelines
- ✅ GitHub Best Practices
- ✅ Industry Standard Secret Management

---

## 🤝 Team Communication

If you're sharing this project with others:

**Tell them to**:

1. Copy `.env.example` to `.env`
2. Fill in their own API keys (if they have them)
3. NEVER commit `.env` to Git
4. Run `git status` to verify before committing
5. Ask if unsure about which files to commit

**Sample message**:

```
⚠️ Security Reminder

When setting up this project:
1. Create .env file from .env.example template
2. Add your own API keys to .env
3. NEVER commit .env to the repository
4. Always use .gitignore to prevent accidents

If you accidentally commit secrets, tell the team immediately.
```

---

## 📞 Questions?

- **Local development**: See [INSTALLATION.md](./setup/INSTALLATION.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **General help**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Report security issues**: Create private security advisory (GitHub)

---

**Status**: ✅ Security Guide Complete  
**Last Updated**: 2026-02-09
**Version**: 1.0.0

⛔ **REMEMBER**: Never commit `.env` files. Never hardcode secrets. Always use `.env.example` as template.
