# Quick Start Guide

## The Simple Workflow (Recommended)

```bash
# Use the safe wrapper - it handles everything!
./safe-create.sh "your-spreadsheet.csv"

# Or use the Claude Code skill
/jira-bulk:from-sheet "your-spreadsheet.csv"
```

That's it! The script:
- ✅ **Auto-detects** CSV format (standard or capacity planning)
- ✅ Shows you a preview (dry-run)
- ✅ Checks for existing issues
- ✅ Asks for confirmation
- ✅ Checks each issue before creating (skip if exists)
- ✅ Creates the issues
- ✅ Exports each issue to YAML file (in `jira-issues/` folder)
- ✅ Automatically detects and resolves duplicates
- ✅ Saves a log file

**YAML files are saved in:** `./jira-issues/PROJECT-XXXXX.yaml` (same location as your CSV)

## Direct Usage

You can also use the unified script directly:

```bash
# Standard CSV or capacity planning sheet (auto-detected)
python3 jira-create.py issues.csv

# Preview first
python3 jira-create.py issues.csv --dry-run

# With custom settings
python3 jira-create.py issues.csv 12345 "My Component"

# Download from Google Sheets
python3 jira-create.py --sheet "https://docs.google.com/spreadsheets/d/..."

# All options
python3 jira-create.py issues.csv \
  --project MYPROJECT \
  --no-sprint \
  --assignee user@example.com \
  --epic PROJECT-1000
```

## If Duplicates Were Created

```bash
# Preview which duplicates will be resolved
python3 deduplicate.py --dry-run

# Resolve duplicates (keeps the one with most info)
python3 deduplicate.py
```

## File Formats

### Both formats supported automatically!

**Standard CSV:**
```csv
Issue Type,Summary,Description,Priority,Labels
Story,Add authentication,Implement OAuth2,High,security auth
Task,Update docs,Document API,Medium,docs
```

**Capacity Planning CSV:**
```csv
Domain & Planning Leads,,Approval
...
Feature,Feature Name,Feature Owner,Epics,Bucket
TELCO-123,HCI Support,Owner,CNF-20465,Customer Committed
```

The script **auto-detects** which format you're using!

## Common Commands

```bash
# List active sprint
jira sprint list --state active --plain

# Check recent issues
jira issue list -pMYPROJECT -linbound-int-50 --plain | tail -20

# View an issue
jira issue view PROJECT-12345

# Close an issue
jira issue move PROJECT-12345 "Closed" --comment "Duplicate"

# Search YAML files
grep -l "status: To Do" jira-issues/*.yaml
```

## Tips

✅ **Always use safe-create.sh** for production  
✅ **Export CSV with date in filename** (e.g., `issues-2026-06-01.csv`)  
✅ **Archive processed files** to avoid re-importing  
✅ **Check the sprint before importing** to see what's already there  
✅ **Use dry-run liberally** - it's fast and safe  
✅ **Version control YAML files** - commit jira-issues/ to git  

## Entry Points

### Main Entry Point (Recommended)
```bash
./safe-create.sh your-file.csv
```

### Direct Script (Advanced)
```bash
python3 jira-create.py your-file.csv [options]
```

### Deduplication (If Needed)
```bash
python3 deduplicate.py --label inbound-int-50
```

**That's it! Just 3 scripts instead of 6!**

## Help

```bash
# Script help
python3 jira-create.py --help

# Deduplication help
python3 deduplicate.py --help

# Jira CLI help
jira --help
jira issue --help
```
