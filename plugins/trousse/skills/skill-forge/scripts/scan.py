#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Sharing Scanner - Detect PII and secrets before making repos public.

Scans for:
- Email addresses (especially work domains)
- Hardcoded paths with usernames
- Company-specific terms
- Secrets in git history
- Common secret patterns (API keys, tokens)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Finding:
    """A single privacy/security finding."""
    category: str  # email, path, company_term, secret, git_history
    risk: str  # high, medium, low
    file: str
    line: Optional[int]
    match: str
    context: str  # surrounding text
    reason: str


@dataclass
class ScanResult:
    """Results from scanning a repository."""
    repo: str
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)


# Default patterns - can be overridden via config
DEFAULT_CONFIG = {
    "email_domains_high_risk": [],  # Add your work domains here, e.g., ["@company.com"]
    "email_domains_medium_risk": ["@company.com", "@corp."],
    "path_usernames": [],  # Add usernames to detect in paths
    "company_terms": [],  # Add your company-specific terms here
    "person_names": [],  # Add your colleagues' names here
    "secret_patterns": [
        r"GOCSPX-[A-Za-z0-9_-]+",  # Google OAuth client secret
        r"sk-[A-Za-z0-9]{48}",  # OpenAI API key
        r"ghp_[A-Za-z0-9]{36}",  # GitHub PAT
        r"xox[baprs]-[A-Za-z0-9-]+",  # Slack tokens
    ],
    "exclude_dirs": [
        ".git", ".venv", "venv", "node_modules", "__pycache__",
        ".bon", ".claude"
    ],
    "exclude_files": [
        "*.pyc", "*.lock", "*.db", ".DS_Store"
    ],
    "include_extensions": [
        ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
        ".sh", ".bash", ".toml", ".txt", ".html", ".css"
    ]
}


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load config, merging with defaults."""
    config = DEFAULT_CONFIG.copy()
    if config_path and config_path.exists():
        with open(config_path) as f:
            user_config = json.load(f)
            for key, value in user_config.items():
                if isinstance(value, list) and key in config:
                    config[key] = list(set(config[key] + value))
                else:
                    config[key] = value
    return config


def should_scan_file(path: Path, config: dict) -> bool:
    """Check if file should be scanned based on config."""
    # Check excluded directories
    for part in path.parts:
        if part in config["exclude_dirs"]:
            return False

    # Check excluded file patterns
    for pattern in config["exclude_files"]:
        if path.match(pattern):
            return False

    # Check included extensions
    if path.suffix.lower() in config["include_extensions"]:
        return True

    # Include extensionless files that might be scripts
    if not path.suffix and path.is_file():
        return True

    return False


def get_context(lines: list[str], line_num: int, context_size: int = 1) -> str:
    """Get surrounding lines for context."""
    start = max(0, line_num - context_size)
    end = min(len(lines), line_num + context_size + 1)
    return "\n".join(lines[start:end]).strip()


def scan_file(path: Path, config: dict) -> list[Finding]:
    """Scan a single file for privacy/security issues."""
    findings = []

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
    except Exception as e:
        return []

    file_str = str(path)

    # Email patterns
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    for i, line in enumerate(lines, 1):
        for match in re.finditer(email_pattern, line):
            email = match.group()
            risk = "low"
            reason = "Email address found"

            for domain in config["email_domains_high_risk"]:
                if domain.lower() in email.lower():
                    risk = "high"
                    reason = f"Work email domain ({domain})"
                    break
            else:
                for domain in config["email_domains_medium_risk"]:
                    if domain.lower() in email.lower():
                        risk = "medium"
                        reason = f"Corporate email pattern ({domain})"
                        break

            # Skip example.com, test emails
            if any(x in email.lower() for x in ["example.com", "test.", "@test", "placeholder"]):
                continue

            findings.append(Finding(
                category="email",
                risk=risk,
                file=file_str,
                line=i,
                match=email,
                context=get_context(lines, i-1),
                reason=reason
            ))

    # Path patterns with usernames
    for username in config["path_usernames"]:
        pattern = rf'/Users/{username}|/home/{username}|GoogleDrive-[^/]*{username}'
        for i, line in enumerate(lines, 1):
            for match in re.finditer(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    category="path",
                    risk="medium",
                    file=file_str,
                    line=i,
                    match=match.group(),
                    context=get_context(lines, i-1),
                    reason=f"Hardcoded path with username '{username}'"
                ))

    # Company terms (case-sensitive for acronyms, insensitive for names)
    for term in config["company_terms"]:
        # Case-sensitive for short terms (likely acronyms)
        if len(term) <= 4:
            pattern = rf'\b{re.escape(term)}\b'
            flags = 0
        else:
            pattern = rf'\b{re.escape(term)}\b'
            flags = re.IGNORECASE

        for i, line in enumerate(lines, 1):
            for match in re.finditer(pattern, line, flags):
                findings.append(Finding(
                    category="company_term",
                    risk="low",
                    file=file_str,
                    line=i,
                    match=match.group(),
                    context=get_context(lines, i-1),
                    reason=f"Company-specific term '{term}'"
                ))

    # Person names
    for name in config["person_names"]:
        pattern = rf'\b{re.escape(name)}\b'
        for i, line in enumerate(lines, 1):
            for match in re.finditer(pattern, line, re.IGNORECASE):
                # Higher risk if it's not just a common word
                risk = "high" if " " in name else "medium"  # Full names are higher risk
                findings.append(Finding(
                    category="person_name",
                    risk=risk,
                    file=file_str,
                    line=i,
                    match=match.group(),
                    context=get_context(lines, i-1),
                    reason=f"Person name '{name}'"
                ))

    # Secret patterns
    for pattern in config["secret_patterns"]:
        for i, line in enumerate(lines, 1):
            for match in re.finditer(pattern, line):
                findings.append(Finding(
                    category="secret",
                    risk="high",
                    file=file_str,
                    line=i,
                    match=match.group()[:20] + "...",  # Truncate actual secret
                    context="[REDACTED]",
                    reason="Potential secret/API key pattern"
                ))

    return findings


def scan_git_history(repo_path: Path, config: dict) -> list[Finding]:
    """Check git history for potentially sensitive files."""
    findings = []

    sensitive_files = [
        "credentials.json", "token.json", ".env", "secrets.",
        "api_key", "private_key", ".pem", ".key"
    ]

    try:
        result = subprocess.run(
            ["git", "log", "--all", "--pretty=format:", "--name-only", "--diff-filter=A"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            files_ever_added = set(result.stdout.strip().split("\n"))
            for filename in files_ever_added:
                if not filename:
                    continue
                for sensitive in sensitive_files:
                    if sensitive.lower() in filename.lower():
                        # Check if still in gitignore
                        gitignore_check = subprocess.run(
                            ["git", "check-ignore", "-q", filename],
                            cwd=repo_path,
                            capture_output=True
                        )
                        currently_ignored = gitignore_check.returncode == 0

                        # Check if file was actually committed (not just added then removed before commit)
                        commit_check = subprocess.run(
                            ["git", "log", "--oneline", "--all", "--", filename],
                            cwd=repo_path,
                            capture_output=True,
                            text=True
                        )
                        was_committed = bool(commit_check.stdout.strip())

                        if was_committed:
                            risk = "high" if not currently_ignored else "medium"
                            findings.append(Finding(
                                category="git_history",
                                risk=risk,
                                file=filename,
                                line=None,
                                match=filename,
                                context=f"Currently ignored: {currently_ignored}",
                                reason=f"Sensitive file '{sensitive}' in git history"
                            ))
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        pass

    return findings


def scan_repo(repo_path: Path, config: dict) -> ScanResult:
    """Scan an entire repository."""
    result = ScanResult(repo=str(repo_path))

    if not repo_path.exists():
        result.errors.append(f"Path does not exist: {repo_path}")
        return result

    # Scan files
    for path in repo_path.rglob("*"):
        if path.is_file() and should_scan_file(path, config):
            result.files_scanned += 1
            try:
                findings = scan_file(path, config)
                result.findings.extend(findings)
            except Exception as e:
                result.errors.append(f"Error scanning {path}: {e}")

    # Scan git history
    if (repo_path / ".git").exists():
        git_findings = scan_git_history(repo_path, config)
        result.findings.extend(git_findings)

    return result


def format_findings(result: ScanResult, format_type: str = "text") -> str:
    """Format scan results for output."""
    if format_type == "json":
        return json.dumps({
            "repo": result.repo,
            "files_scanned": result.files_scanned,
            "findings": [asdict(f) for f in result.findings],
            "errors": result.errors
        }, indent=2)

    # Text format
    lines = [f"\n{'='*60}", f"SCAN: {result.repo}", f"{'='*60}"]
    lines.append(f"Files scanned: {result.files_scanned}")

    if result.errors:
        lines.append(f"\nErrors: {len(result.errors)}")
        for err in result.errors[:5]:
            lines.append(f"  - {err}")

    # Group by risk
    high = [f for f in result.findings if f.risk == "high"]
    medium = [f for f in result.findings if f.risk == "medium"]
    low = [f for f in result.findings if f.risk == "low"]

    lines.append(f"\nFindings: {len(result.findings)} total")
    lines.append(f"  HIGH: {len(high)}  MEDIUM: {len(medium)}  LOW: {len(low)}")

    for risk_level, findings in [("HIGH", high), ("MEDIUM", medium), ("LOW", low)]:
        if findings:
            lines.append(f"\n--- {risk_level} RISK ---")
            # Dedupe by file+match
            seen = set()
            for f in findings:
                key = (f.file, f.match)
                if key in seen:
                    continue
                seen.add(key)

                rel_path = Path(f.file).name
                if f.line:
                    lines.append(f"  [{f.category}] {rel_path}:{f.line}")
                else:
                    lines.append(f"  [{f.category}] {rel_path}")
                lines.append(f"    Match: {f.match}")
                lines.append(f"    Reason: {f.reason}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan repos for sharing risks")
    parser.add_argument("paths", nargs="+", help="Paths to scan (repos or directories)")
    parser.add_argument("--config", type=Path, help="Config file (JSON)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--risk", choices=["all", "high", "medium"], default="all",
                        help="Minimum risk level to report")
    args = parser.parse_args()

    config = load_config(args.config)

    all_results = []
    for path_str in args.paths:
        path = Path(path_str).expanduser().resolve()
        result = scan_repo(path, config)

        # Filter by risk level
        if args.risk == "high":
            result.findings = [f for f in result.findings if f.risk == "high"]
        elif args.risk == "medium":
            result.findings = [f for f in result.findings if f.risk in ["high", "medium"]]

        all_results.append(result)
        print(format_findings(result, args.format))

    # Exit with error if high-risk findings
    high_count = sum(len([f for f in r.findings if f.risk == "high"]) for r in all_results)
    if high_count > 0:
        print(f"\n⚠️  Found {high_count} HIGH risk items. Review before sharing.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
