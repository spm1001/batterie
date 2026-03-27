# Sharing Scan Reference

Detailed triage guidelines for the sharing scanner.

## What It Detects

| Category | Risk | Examples |
|----------|------|----------|
| **email** | High/Medium | Work emails, colleague addresses |
| **path** | Medium | `/Users/username/`, GoogleDrive paths |
| **person_name** | High/Medium | Full names of colleagues |
| **company_term** | Low | Product names, team acronyms |
| **secret** | High | API keys, OAuth tokens |
| **git_history** | High/Medium | Sensitive files ever committed |

## Triage Guidelines

### HIGH Risk — Block sharing until resolved

**Emails (work domain):**
- Colleague's email → Replace with `jane.doe@example.com`
- Your work email in paths → Use `$USER` or placeholder

**Person names (full names):**
- Real colleague names → Anonymize: "Alice", "Bob"
- Your name is lower risk (you're the author)

**Secrets:**
- API keys, tokens → Remove and rotate immediately
- Git history secrets → Need `git filter-branch` or BFG

### MEDIUM Risk — Decide case-by-case

**Paths with username:**
- In examples → Replace with `~/` or `$HOME`
- In hardcoded logic → Refactor to use env vars

**Person names (first name only):**
- "Sameer" in personalized skill → Keep with disclaimer, or generalize
- Common names in examples → Usually fine

**Git history (now ignored):**
- File was committed but now gitignored → Safe if secret was rotated
- Check: `git log --all -- filename`

### LOW Risk — Acceptable for sharing

**Company terms:**
- Product names in examples → Fine if public knowledge
- Internal acronyms → Consider if they identify employer
- Team names → Usually fine with context

## Remediation Patterns

### Replace email with placeholder
```
# Before
from: real.colleague@company.com

# After
from: colleague@example.com
```

### Anonymize paths
```
# Before
~/Library/CloudStorage/GoogleDrive-your.email@company.com/

# After
~/Library/CloudStorage/GoogleDrive-YOUR_EMAIL/
```

### Remove from git history (if committed)
```bash
# Install BFG (faster than filter-branch)
brew install bfg

# Remove file from all history
bfg --delete-files credentials.json
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (coordinate with collaborators!)
git push --force
```

## Custom Configuration

Create/edit `scan-config.json` to extend detection:

```json
{
  "email_domains_high_risk": ["@mycompany.com"],
  "company_terms": ["ProjectX", "SecretInitiative"],
  "person_names": ["Specific Colleague"],
  "path_usernames": ["myusername"]
}
```

## Exit Codes

- `0`: No high-risk findings
- `1`: High-risk findings detected (review required)
