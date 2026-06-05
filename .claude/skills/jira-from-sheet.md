---
name: jira-from-sheet
description: Create Jira issues in bulk from a Google Sheet or CSV file
trigger: Use when the user wants to create multiple Jira issues from a spreadsheet, Google Sheet, or CSV file
---

# Jira from Google Sheet

Create Jira issues in bulk by reading data from a Google Sheet or CSV file.

## How to Invoke This Skill

From Claude Code, type:
```
/jira-from-sheet
```

Or ask naturally:
```
Create Jira issues from this spreadsheet
Import issues from my CSV file
Bulk create Jira stories from this Google Sheet
```

## Prerequisites

- `jira` CLI tool installed and authenticated
- Access to the Google Sheet (either public link or exported CSV)

## Input Format

The spreadsheet should contain columns for Jira issue fields.

**Required Columns:**
- **Summary** - Issue title (required)

**Optional Columns:**
- **Issue Type** - Story, Task, Bug, Epic, etc. (default: Story)
- **Description** - Detailed description
- **Priority** - Highest, High, Medium, Low, Lowest
- **Labels** - Space-separated labels (script always adds "inbound-int-50")
- **Assignee** - Username or email (can also be set via --assignee flag for all issues)

**Example CSV:**
```csv
Issue Type,Summary,Description,Priority,Labels
Story,Add user authentication,Implement OAuth2 authentication,High,security auth
Task,Update documentation,Document new API endpoints,Medium,docs api
Bug,Fix login bug,Users stuck in redirect loop,Highest,bug login
```

**Notes:**
- Component is specified via command-line argument, not in CSV
- Sprint assignment is handled via command-line argument
- Epic linking is handled via --epic flag
- The script automatically adds "inbound-int-50" label to all issues

## Quick Start

**Recommended: Use the safe wrapper script**

```bash
cd /home/dphillip/claude/claude-jira
./safe-create.sh <csv_file> [sprint_id] [component]
```

The safe wrapper:
- ✅ Shows dry-run preview first
- ✅ Checks for existing issues
- ✅ Asks for confirmation
- ✅ Creates issues with duplicate prevention
- ✅ Exports each issue to YAML
- ✅ Runs automatic deduplication
- ✅ Saves detailed log

**Direct usage: Unified script (auto-detects format)**

```bash
python3 /home/dphillip/claude/claude-jira/jira-create.py <csv_file> [sprint_id] [component] [options]
```

**Basic Examples:**
```bash
# Auto-detects standard CSV or capacity planning format
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv

# Specify sprint and component
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv 12345 "My Component"

# Dry run mode (preview without creating)
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --dry-run
```

**Advanced Examples:**
```bash
# Download directly from Google Sheets
python3 /home/dphillip/claude/claude-jira/jira-create.py \
  --sheet "https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0"

# Create without adding to sprint
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --no-sprint

# Assign all issues to a specific user
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --assignee jdoe@redhat.com

# Link all issues to an epic
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --epic CNF-12345

# Use different project
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --project OCPBUGS

# Force specific format (auto-detect is default)
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --format capacity-planning

# Custom rate limiting (default 0.5s between requests)
python3 /home/dphillip/claude/claude-jira/jira-create.py issues.csv --rate-limit 1.0
```

**Available Options:**
- `--dry-run` - Preview issues without creating them
- `--sheet URL` - Download from Google Sheets URL
- `--project KEY` - Jira project key (default: CNF)
- `--no-sprint` - Don't add issues to a sprint
- `--assignee USER` - Assign all issues to a user
- `--epic EPIC-KEY` - Link all issues to an epic
- `--rate-limit SECONDS` - Seconds between API calls (default: 0.5)
- `--format TYPE` - Force format: auto (default), standard, or capacity-planning

## Implementation Steps

### 1. Get the Spreadsheet Data

**Option A: CSV Export**
- Ask the user to export the Google Sheet as CSV and provide the file path
- Read the CSV file using standard tools

**Option B: Public Google Sheet**
- Get the Google Sheet URL from the user
- Export as CSV using: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}`
- Download with `curl` or `wget`

**Option C: Use the Python script directly**
```bash
# Download from Google Sheets
curl -L "https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=GID" -o issues.csv

# Create issues
python3 /home/dphillip/claude/claude-jira/create-issues.py issues.csv
```

### 2. Using the Python Script

The script at `/home/dphillip/claude/claude-jira/create-issues.py` handles:
- CSV parsing with proper error handling
- Issue creation via `jira` CLI
- Sprint assignment
- Label management (always adds "inbound-int-50")
- Progress reporting
- Summary of created/failed issues

**Arguments:**
1. CSV file path (required)
2. Sprint ID (optional, default: 66887)
3. Component name (optional, default: "CNF Integration")

### 3. Manual Creation (if needed)

For each row in the spreadsheet:

```bash
# Basic issue creation
jira issue create \
  -pPROJECT_KEY \
  -t"Story" \
  -s"Issue summary" \
  -b"Issue description" \
  --no-input

# With additional fields
jira issue create \
  -pPROJECT_KEY \
  -t"Bug" \
  -s"Issue summary" \
  -b"Issue description" \
  -C"ComponentName" \
  -llabel1 \
  -llabel2 \
  -ausername \
  --no-input

# Add to sprint
jira sprint add SPRINT_ID ISSUE-KEY
```

### 4. Track Results

The Python script automatically:
- Logs created issue keys with links
- Reports any failures with error messages
- Provides a summary of created issues

## Example Workflow

```bash
# 1. Download the sheet as CSV
curl -L "https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv" -o issues.csv

# 2. Process each row (example with Python/bash)
# Parse CSV and create issues

# 3. Report results
echo "Created X issues successfully"
echo "Failed Y issues"
```

## Error Handling

- Validate all required fields before creating
- Skip rows with missing required data (log warnings)
- Continue on individual failures, don't stop the batch
- Provide detailed error messages with row numbers

## Output

Provide a summary table:
- Row number
- Created issue key (or error message)
- Link to created issue

## Usage Tips

- Always ask the user to confirm the field mapping before creating issues
- Consider doing a dry run first to show what would be created
- For large batches, consider rate limiting to avoid API throttling
