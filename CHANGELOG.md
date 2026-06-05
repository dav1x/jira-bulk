# Changelog

## Version 3.0 - Labels Support (2026-06-04)

### 🎉 New Features

- **Comma-delimited labels** - Support for multiple labels from CSV (e.g., "label1, label2, label3")
- **Automatic label merging** - Combines CSV labels with default labels
- **Smart deduplication** - Avoids adding duplicate labels
- **Claude Code skill** - `/jira-bulk:from-sheet` command for easy invocation

### 🛠️ Improvements

- Enhanced CSV column parsing for capacity planning sheets
- Updated documentation for public release
- Added .gitignore and LICENSE files
- Removed internal references from documentation

### 📝 Documentation

- Sanitized all docs for GitHub
- Updated skill name to `jira-bulk:from-sheet`
- Generic examples (removed company-specific references)

## Version 2.0 - Complete Workflow (2026-06-01)

### 🎉 Major Features

#### ⭐ YAML Export

- **Automatic export** of all created issues to YAML files
- **Saves to:** `./jira-issues/` folder (created automatically)
- **Files:** One `.yaml` file per issue
- **Contains:** Full issue details - key, summary, description, status, assignee, labels, components, timestamps

#### ⭐ Duplicate Prevention

- **Pre-creation check** - Searches Jira BEFORE creating each issue
- **30-day lookback** - Checks recently created issues
- **Unicode normalization** - Handles special characters in summaries (curly quotes, em-dashes)
- **Action:** Skips creation if duplicate found

#### ⭐ Post-Creation Deduplication

- **Smarter scoring** - Keeps the issue with the most information
- **Better matching** - Handles variations in summaries
- **Safer** - Dry-run by default

### 🛠️ Improvements

#### Unified Script

- **Auto-detection** - Automatically detects CSV format (standard or capacity planning)
- **Single entry point** - `jira-create.py` handles all CSV formats
- **Safe wrapper** - `safe-create.sh` provides interactive workflow

#### Enhanced Duplicate Detection

- 30-day lookback window (increased from 14 days)
- Unicode character normalization
- Full summary text comparison (no truncation)
- Tab-separated output parsing improvements
- COLUMNS environment variable to prevent truncation

### 📝 Files

- `jira-create.py` - Unified creation script
- `prevent_duplicates.py` - Pre-creation duplicate checking
- `deduplicate.py` - Post-creation cleanup
- `jira_yaml_export.py` - YAML export functionality
- `safe-create.sh` - Safe wrapper script

## Version 1.0 - Initial Release (2026-06-01)

### Features

- CSV to Jira issue creation
- Capacity planning sheet support
- Sprint assignment
- Component and label management
- Dry-run preview mode
- Google Sheets download support
- Rate limiting
- Basic error handling
- Basic deduplication

### Files

- `jira-create.py` - Main script
- `deduplicate.py` - Deduplication tool
- `safe-create.sh` - Wrapper script
- `README.md` - Documentation
