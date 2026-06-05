# Jira Bulk Issue Creation

Create Jira issues in bulk from CSV files or Google Sheets with automatic duplicate prevention.

**✨ Auto-detects CSV format** - Works with standard CSV or capacity planning sheets!
**✨ Duplicate detection** - Prevents creating duplicate issues
**✨ Custom labels** - Supports comma-delimited labels from CSV

## Quick Start

```bash
# Use the safe wrapper (recommended)
./safe-create.sh issues.csv

# Or use the unified script directly
python3 jira-create.py issues.csv [sprint_id] [component]

# Preview first with dry-run
python3 jira-create.py issues.csv --dry-run

# Using the Claude Code skill
/jira-bulk:from-sheet issues.csv
```

## Features

- ✅ Create issues from CSV or Google Sheets
- ✅ Automatic sprint assignment
- ✅ Component and label management
- ✅ Assignee support
- ✅ Epic linking
- ✅ Dry-run mode for previewing
- ✅ Rate limiting to avoid API throttling
- ✅ Detailed progress reporting
- ✅ Error handling and retry logic
- ✅ **Duplicate prevention** - Checks for existing issues BEFORE creating
- ✅ **YAML export** - Automatically exports each created issue to YAML file

## Prerequisites

- `jira` CLI tool installed and configured ([jira-cli](https://github.com/ankitpokhrel/jira-cli))
- Python 3.6+
- `curl` (for downloading from Google Sheets)

## Installation

The script is standalone and requires no additional dependencies beyond Python 3 and the `jira` CLI.

```bash
# Make executable
chmod +x create-issues.py

# Test it
./create-issues.py --help
```

## CSV Format

### Required Columns

- **Summary** - Issue title

### Optional Columns

- **Issue Type** - Story, Task, Bug, Epic, etc. (default: Story)
- **Description** - Detailed description
- **Priority** - Highest, High, Medium, Low, Lowest
- **Labels** - Comma-delimited labels (e.g., "label1, label2, label3")
- **Assignee** - Username or email

### Example CSV

```csv
Issue Type,Summary,Description,Priority,Labels
Story,Add user authentication,Implement OAuth2 authentication for user login,High,security auth
Task,Update API documentation,Document the new endpoints added in v2.0,Medium,docs api
Bug,Fix login redirect loop,Users get stuck in redirect loop after password reset,Highest,bug login
Story,Implement dark mode,Add dark mode theme toggle to user preferences,Low,enhancement ui
Task,Setup CI/CD pipeline,Configure GitHub Actions for automated testing,High,automation ci-cd
```

## Usage Examples

### Basic Usage

```bash
# Create issues with default settings
python3 jira-create.py issues.csv

# Specify sprint and component
python3 jira-create.py issues.csv 12345 "My Component"

# Dry run to preview what will be created
python3 jira-create.py issues.csv --dry-run
```

### Google Sheets

```bash
# Download from Google Sheets and create issues
python3 jira-create.py --sheet "https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0"

# With dry run
python3 jira-create.py --sheet "GOOGLE_SHEET_URL" --dry-run
```

### Advanced Options

```bash
# Create without adding to sprint
python3 jira-create.py issues.csv --no-sprint

# Assign all issues to a specific user
python3 jira-create.py issues.csv --assignee user@example.com

# Link all issues to an epic
python3 jira-create.py issues.csv --epic PROJECT-12345

# Use different project
python3 jira-create.py issues.csv --project MYPROJECT

# Custom rate limiting (seconds between API calls)
python3 jira-create.py issues.csv --rate-limit 1.0

# Combine multiple options
python3 jira-create.py issues.csv 12345 "Component Name" \
  --assignee user@example.com \
  --epic PROJECT-100 \
  --rate-limit 1.0
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `csv_file` | Path to CSV file | - |
| `sprint_id` | Sprint ID to add issues to | (optional) |
| `component` | Component name | (optional) |
| `--dry-run` | Preview without creating | false |
| `--sheet URL` | Google Sheets URL | - |
| `--project KEY` | Jira project key | CNF (configurable) |
| `--no-sprint` | Don't add to sprint | false |
| `--assignee USER` | Assign to user | - |
| `--epic EPIC-KEY` | Link to epic | - |
| `--rate-limit SEC` | Seconds between requests | 0.5 |

## YAML Export

Each created issue is automatically exported to a YAML file in the `jira-issues` folder (in the same directory as your CSV file).

**YAML files include:**
- Issue key, ID, and URL
- Summary and description
- Status, priority, assignee
- Labels and components
- Created/updated timestamps
- Custom fields
- Project information

**Example:**
```bash
python3 jira-create.py issues.csv
# Creates: ./jira-issues/PROJECT-12345.yaml, ./jira-issues/PROJECT-12346.yaml, etc.
```

**YAML file structure:**
```yaml
key: PROJECT-12345
type: Story
summary: Add user authentication
description: Implement OAuth2...
status: To Do
assignee: Unassigned
labels:
  - inbound-int-50
  - security
components:
  - My Component
exported_at: '2026-06-01T15:28:26.049513'
```

**Uses:**
- Documentation and tracking
- Backup of issue details
- Integration with other tools
- Audit trail
- Easy searching with grep/yaml tools

## How It Works

1. **Parse CSV** - Reads the CSV file and validates required columns
2. **Check Duplicates** - Searches Jira for existing issues with same summary
3. **Create Issues** - For each row, creates a Jira issue using the `jira` CLI
4. **Export to YAML** - Saves issue details to YAML file in `jira-issues/` folder
5. **Add Labels** - Automatically adds "inbound-int-50" plus any labels from the CSV
6. **Sprint Assignment** - Adds issues to the specified sprint (unless `--no-sprint`)
7. **Progress Reporting** - Shows real-time progress and summary at the end
8. **Rate Limiting** - Waits between requests to avoid API throttling

## Duplicate Detection & Resolution

If duplicates are created, use the deduplication tool to automatically keep the one with the most information:

```bash
# Find and resolve duplicates (dry-run first)
python3 deduplicate.py --dry-run

# Resolve duplicates for real
python3 deduplicate.py
```

The script:
- ✅ Finds issues with matching summaries
- ✅ Scores each based on: description length, links, comments, assignee, status
- ✅ Keeps the one with the highest score
- ✅ Closes the others with a comment linking to the keeper

**The safe-create.sh script automatically runs deduplication after creating issues!**

## Troubleshooting

### Duplicates Were Created

Run the deduplication tool:

```bash
python3 deduplicate.py --label inbound-int-50
```

It will keep the issue with the most information and close the rest.

### "Missing configuration file"

The `jira` CLI needs to be configured first:

```bash
jira init
```

### Rate Limiting / 429 Errors

If you hit API rate limits, increase the rate limit:

```bash
python3 create-issues.py issues.csv --rate-limit 2.0
```

### Invalid Priority

Priority values must match your Jira configuration. Common values:
- Highest
- High
- Medium
- Low
- Lowest

If in doubt, omit the Priority column.

### Component Not Found

Ensure the component exists in your project. You can list components:

```bash
jira component list -pCNF
```

## Claude Code Skill

This project includes a Claude Code skill `/jira-bulk:from-sheet` that provides:
- Automatic CSV format detection
- Dry-run preview before creation
- Interactive confirmation
- Duplicate prevention
- Progress reporting

**Usage:**
```bash
/jira-bulk:from-sheet path/to/file.csv
```

Or ask Claude:
> "Create Jira issues from this CSV file"

## Entry Points

### 🎯 Main Scripts (Use These)

1. **`./safe-create.sh`** ⭐ **RECOMMENDED**
   - Safe wrapper with dry-run, confirmation, and auto-deduplication
   - Use this for production

2. **`jira-create.py`** ⭐ **UNIFIED SCRIPT**
   - Auto-detects CSV format (standard or capacity planning)
   - Handles all issue creation
   - Use directly for advanced options

3. **`deduplicate.py`**
   - Post-creation duplicate cleanup
   - Run if duplicates slip through

### 🛠️ Helper Modules
- `prevent_duplicates.py` - Pre-creation duplicate checking (auto-imported)
- `jira_yaml_export.py` - YAML export (auto-imported)

### 📚 Documentation
- `README.md` - This file
- `QUICK_START.md` - Quick reference guide
- `HOW_TO_USE.md` - Detailed usage guide
- `CHANGELOG.md` - Version history

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues or questions, please file an issue in the repository.
