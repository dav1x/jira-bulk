# How to Use the Jira Bulk Import Tool

## From Command Line

### Option 1: Safe Wrapper (Recommended)

```bash
./safe-create.sh "your-file.csv"
```

This will:
1. Show you a preview (dry-run)
2. Check for existing issues
3. Ask you to confirm
4. Create the issues
5. Export to YAML
6. Clean up duplicates
7. Save a log

### Option 2: Direct Script

```bash
python3 jira-create.py "your-file.csv"
```

Add `--dry-run` to preview first:
```bash
python3 jira-create.py "your-file.csv" --dry-run
```

## From Claude Code

### Option 1: Invoke the Skill

Type in the chat:
```
/jira-bulk:from-sheet path/to/your-file.csv
```

### Option 2: Ask Naturally

Just ask:
```
Create Jira issues from this CSV file
```
or
```
Import my Google Sheet into Jira
```
or
```
Bulk create stories from 5.0 Epic Assignment.csv
```

I'll recognize the request and invoke the skill automatically.

## What the Skill Does

When you invoke `/jira:from-sheet`, I will:

1. **Ask for the file path or Google Sheet URL**
   - You provide: `/path/to/file.csv` or a Google Sheets URL

2. **Detect the format**
   - Auto-detects if it's a standard CSV or capacity planning sheet

3. **Run dry-run first**
   - Shows you what would be created
   - You can review before proceeding

4. **Ask for confirmation**
   - You decide whether to proceed

5. **Create the issues**
   - Checks for duplicates before creating
   - Creates each issue in Jira
   - Exports to YAML files
   - Adds to sprint

6. **Clean up duplicates**
   - Runs deduplication automatically
   - Keeps the best version

7. **Report results**
   - Shows created issues
   - Shows YAML file locations
   - Shows log file location

## Example Session

```
You: /jira:from-sheet

Me: I'll help you create Jira issues from a spreadsheet. 
    
    What's the path to your CSV file or Google Sheets URL?

You: /home/dphillip/claude/claude-jira/5.0 Epic Assignment.csv

Me: [Runs dry-run and shows preview]
    
    Found 4 issues to create:
    1. Hyperconverged Control Plane Nodes...
    2. [Spike] Verify telco upgrade...
    3. CX-8 Precision Timing...
    4. Characterize Performance...
    
    Would you like to proceed? (yes/no)

You: yes

Me: [Creates issues, exports YAML, runs deduplication]
    
    ✓ Created 4 issues
    ✓ Exported 4 YAML files to ./jira-issues/
    ✓ No duplicates found
    
    Created issues:
    - CNF-24308: Hyperconverged Control Plane...
    - CNF-24322: [Spike] Verify telco...
    - CNF-24324: CX-8 Precision...
    - CNF-24327: Characterize Performance...
    
    YAML files saved to: ./jira-issues/
    Log saved to: creation-log-20260601-150134.txt
```

## Quick Reference

| Method | Command |
|--------|---------|
| **Claude skill** | `/jira:from-sheet` |
| **Safe wrapper** | `./safe-create.sh file.csv` |
| **Direct script** | `python3 jira-create.py file.csv` |
| **Dry-run** | Add `--dry-run` flag |
| **Help** | `python3 jira-create.py --help` |

## File Locations

After running:
- **YAML files**: `./jira-issues/CNF-XXXXX.yaml`
- **Log file**: `./creation-log-YYYYMMDD-HHMMSS.txt`
- **Input CSV**: Same location you provided

## Tips

✅ **Use the skill in Claude** - Most user-friendly  
✅ **Always dry-run first** - Preview before creating  
✅ **Check YAML files** - Verify exports worked  
✅ **Archive CSVs** - Move processed files to archive folder  
✅ **Version control YAML** - Commit to git for history  

## Troubleshooting

### "Skill not found"

The skill is defined in:
```
/home/dphillip/claude/claude-jira/.claude/skills/jira-from-sheet.md
```

Make sure you're in the `/home/dphillip/claude/claude-jira` directory or a subdirectory.

### Rate limit errors

Wait a few minutes and run:
```bash
python3 deduplicate.py --label inbound-int-50
```

### Duplicates created

Run the deduplication script:
```bash
python3 deduplicate.py --dry-run  # Preview first
python3 deduplicate.py            # Then run
```

## Need Help?

- Check `QUICK_START.md` for quick reference
- Check `README.md` for complete documentation
- Check `COMPLETE_WORKFLOW.md` for detailed workflow
- Run `python3 jira-create.py --help` for all options
