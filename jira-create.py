#!/usr/bin/env python3
"""
Unified Jira bulk issue creation tool.
Handles both standard CSV and capacity planning sheet formats.
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time
import urllib.parse

# Import helper modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from prevent_duplicates import check_before_create
    DUPLICATE_CHECK_AVAILABLE = True
except ImportError:
    DUPLICATE_CHECK_AVAILABLE = False
    print("⚠ Warning: Duplicate prevention module not available")

try:
    from jira_yaml_export import export_to_yaml
    YAML_EXPORT_AVAILABLE = True
except ImportError:
    YAML_EXPORT_AVAILABLE = False
    print("⚠ Warning: YAML export module not available")


def download_google_sheet(url):
    """Download a Google Sheet as CSV."""
    sheet_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    gid_match = re.search(r'[#&]gid=(\d+)', url)

    if not sheet_match:
        print('✗ Could not extract sheet ID from URL')
        sys.exit(1)

    sheet_id = sheet_match.group(1)
    gid = gid_match.group(1) if gid_match else '0'

    csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
    output_file = f'/tmp/jira_import_{sheet_id}.csv'

    print(f'Downloading Google Sheet...')
    result = subprocess.run(['curl', '-sL', csv_url, '-o', output_file], capture_output=True)

    if result.returncode != 0:
        print(f'✗ Failed to download: {result.stderr.decode()}')
        sys.exit(1)

    print(f'✓ Downloaded to {output_file}\n')
    return output_file


def detect_csv_format(csv_file):
    """
    Detect if this is a capacity planning sheet or standard CSV.
    Returns: 'capacity-planning' or 'standard'
    """
    try:
        with open(csv_file, 'r') as f:
            # Read first few lines
            lines = [next(f, '') for _ in range(10)]

            # Check for capacity planning indicators
            for line in lines:
                if 'Feature Name' in line and 'Feature Owner' in line:
                    return 'capacity-planning'
                if 'Domain & Planning Leads' in line:
                    return 'capacity-planning'

            # Check for standard CSV
            if 'Summary' in lines[0] or 'Issue Type' in lines[0]:
                return 'standard'

            # Default to standard
            return 'standard'
    except Exception as e:
        print(f"Warning: Could not detect CSV format: {e}")
        return 'standard'


def create_jira_issue(summary, description, config, issue_type='Story', priority=None,
                     assignee=None, labels=None, dry_run=False, check_duplicates_before=True):
    """Create a Jira issue using the jira CLI."""

    # Check for existing issues BEFORE creating
    if check_duplicates_before and not dry_run and DUPLICATE_CHECK_AVAILABLE:
        should_create, existing_key, reason = check_before_create(
            summary, project=config['project'], require_confirmation=False
        )

        if not should_create:
            print(f'    ⚠ SKIPPING: {reason}')
            return f'SKIP:{existing_key}' if existing_key else 'SKIP:unknown'

        if existing_key:
            print(f'    ℹ️  {reason}')

    if dry_run:
        print(f'    [DRY RUN] Would create: {issue_type}')
        print(f'              Summary: {summary}')
        print(f'              Component: {config["component"]}')

        # Format labels for display
        label_list = []
        if labels:
            label_list = [label.strip() for label in labels.split(',') if label.strip()]
        # Add inbound-int-50 if not already present
        if 'inbound-int-50' not in label_list:
            label_list.insert(0, 'inbound-int-50')
        print(f'              Labels: {", ".join(label_list)}')

        if assignee:
            print(f'              Assignee: {assignee}')
        if config.get('sprint_id'):
            print(f'              Sprint: {config["sprint_id"]}')
        if config.get('epic'):
            print(f'              Epic: {config["epic"]}')
        return f'DRY-RUN-{hash(summary)}'

    # Build the command
    cmd = [
        'jira', 'issue', 'create',
        f'-p{config["project"]}',
        f'-t{issue_type}',
        f'-s{summary}',
        f'-b{description}',
        f'-C{config["component"]}',
        '--no-input'
    ]

    # Parse labels from CSV (comma-delimited)
    label_list = []
    if labels:
        label_list = [label.strip() for label in labels.split(',') if label.strip()]

    # Add inbound-int-50 if not already in the list
    if 'inbound-int-50' not in label_list:
        label_list.insert(0, 'inbound-int-50')

    # Add all labels to command
    for label in label_list:
        cmd.append(f'-l{label}')

    # Add assignee
    if assignee or config.get('assignee'):
        cmd.append(f'-a{assignee or config["assignee"]}')

    # Add priority
    if priority:
        cmd.append(f'-y{priority}')

    # Add epic link if specified
    if config.get('epic'):
        cmd.extend(['--custom', f'epic-link={config["epic"]}'])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout + result.stderr

        # Extract issue key
        match = re.search(r'CNF-\d+', output)
        if match:
            issue_key = match.group(0)
            print(f'    ✓ Created: https://redhat.atlassian.net/browse/{issue_key}')

            # Add to sprint if specified
            if config.get('sprint_id'):
                sprint_cmd = ['jira', 'sprint', 'add', str(config['sprint_id']), issue_key]
                subprocess.run(sprint_cmd, capture_output=True, check=False)
                print(f'    ✓ Added to sprint {config["sprint_id"]}')

            return issue_key
        else:
            print(f'    ✗ Could not extract issue key from: {output}')
            return None

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        print(f'    ✗ Failed: {error_msg}')
        return None


def process_standard_csv(csv_file, config, dry_run=False):
    """Process a standard CSV file with columns like Summary, Description, etc."""

    created = []
    failed = []
    duplicates = []
    yaml_files = []

    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)

            # Validate required columns
            required_cols = ['Summary']
            if not all(col in reader.fieldnames for col in required_cols):
                print(f'✗ CSV must have at least these columns: {", ".join(required_cols)}')
                print(f'  Found: {", ".join(reader.fieldnames)}')
                sys.exit(1)

            for i, row in enumerate(reader, 1):
                summary = row.get('Summary', '').strip()
                if not summary:
                    print(f'[{i}] ⚠ Skipping row with empty summary')
                    print()
                    continue

                issue_type = row.get('Issue Type', 'Story')
                description = row.get('Description', '')
                priority = row.get('Priority')
                assignee = row.get('Assignee')
                labels = row.get('Labels', '')

                print(f'[{i}] [{issue_type}] {summary}')

                issue_key = create_jira_issue(
                    summary, description, config,
                    issue_type=issue_type,
                    priority=priority,
                    assignee=assignee,
                    labels=labels,
                    dry_run=dry_run
                )

                if issue_key:
                    if issue_key.startswith('SKIP:'):
                        existing_key = issue_key.replace('SKIP:', '')
                        if existing_key and existing_key != 'unknown':
                            duplicates.append(existing_key)
                        else:
                            duplicates.append(summary[:40] + '...')
                    else:
                        created.append(issue_key)

                        # Export to YAML
                        if not dry_run and YAML_EXPORT_AVAILABLE:
                            time.sleep(1)
                            yaml_file = export_to_yaml(issue_key, config['yaml_output_dir'])
                            if yaml_file:
                                yaml_files.append(yaml_file)
                                print(f'    ✓ Exported to YAML: {os.path.basename(yaml_file)}')
                            else:
                                print(f'    ⚠ Failed to export YAML')
                else:
                    failed.append(summary)

                print()

                # Rate limiting
                if not dry_run and issue_key and not issue_key.startswith('SKIP:'):
                    time.sleep(config.get('rate_limit', 0.5))

    except FileNotFoundError:
        print(f'✗ File not found: {csv_file}')
        sys.exit(1)
    except KeyError as e:
        print(f'✗ Missing required column: {e}')
        sys.exit(1)

    return created, duplicates, failed, yaml_files


def process_capacity_planning_csv(csv_file, config, dry_run=False):
    """Process a capacity planning sheet CSV."""

    created = []
    failed = []
    skipped = 0
    duplicates = []
    yaml_files = []

    try:
        with open(csv_file, 'r') as f:
            # Skip metadata rows (first 6 rows)
            for _ in range(6):
                next(f)

            reader = csv.DictReader(f)

            for i, row in enumerate(reader, 1):
                feature_name = row.get('Feature Name', '').strip()

                # Skip empty rows
                if not feature_name:
                    skipped += 1
                    continue

                bucket = row.get('Bucket', '').strip()
                notes = row.get('Notes', '').strip()
                epic_ref = row.get('Epics', '').strip()

                # Parse labels from column K (Labels)
                # Labels are comma-delimited (e.g., "label1, label2, label3")
                labels_str = row.get('Labels', '').strip()
                labels = labels_str if labels_str else None

                # Build description
                description_parts = []
                if bucket:
                    description_parts.append(f"Bucket: {bucket}")
                if epic_ref:
                    description_parts.append(f"Related Epic: {epic_ref}")
                if notes:
                    description_parts.append(f"\nNotes: {notes}")

                description = "\n".join(description_parts) if description_parts else "Story from capacity planning sheet"

                print(f'[{i}] {feature_name[:70]}{"..." if len(feature_name) > 70 else ""}')

                issue_key = create_jira_issue(
                    feature_name, description, config,
                    issue_type='Story',
                    labels=labels,
                    dry_run=dry_run
                )

                if issue_key:
                    if issue_key.startswith('SKIP:'):
                        existing_key = issue_key.replace('SKIP:', '')
                        if existing_key and existing_key != 'unknown':
                            duplicates.append(existing_key)
                        else:
                            duplicates.append(feature_name[:40] + '...')
                    else:
                        created.append(issue_key)

                        # Export to YAML
                        if not dry_run and YAML_EXPORT_AVAILABLE:
                            time.sleep(1)
                            yaml_file = export_to_yaml(issue_key, config['yaml_output_dir'])
                            if yaml_file:
                                yaml_files.append(yaml_file)
                                print(f'    ✓ Exported to YAML: {os.path.basename(yaml_file)}')
                            else:
                                print(f'    ⚠ Failed to export YAML')
                else:
                    failed.append(feature_name)

                print()

                # Rate limiting
                if not dry_run and issue_key and not issue_key.startswith('SKIP:'):
                    time.sleep(0.5)

    except FileNotFoundError:
        print(f'✗ File not found: {csv_file}')
        sys.exit(1)

    return created, duplicates, failed, yaml_files, skipped


def main():
    parser = argparse.ArgumentParser(
        description='Unified Jira bulk issue creation from CSV or Google Sheets',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('csv_file', nargs='?', help='Path to CSV file')
    parser.add_argument('sprint_id', nargs='?', default='66887', help='Sprint ID (default: 66887)')
    parser.add_argument('component', nargs='?', default='CNF Integration', help='Component name (default: CNF Integration)')

    # Options
    parser.add_argument('--dry-run', action='store_true', help='Preview without creating')
    parser.add_argument('--sheet', help='Google Sheets URL')
    parser.add_argument('--project', default='CNF', help='Jira project key (default: CNF)')
    parser.add_argument('--no-sprint', action='store_true', help='Don\'t add to sprint')
    parser.add_argument('--assignee', help='Assign all issues to this user')
    parser.add_argument('--epic', help='Link all issues to this epic')
    parser.add_argument('--rate-limit', type=float, default=0.5, help='Seconds between requests (default: 0.5)')
    parser.add_argument('--format', choices=['auto', 'standard', 'capacity-planning'],
                       default='auto', help='CSV format (default: auto-detect)')

    args = parser.parse_args()

    # Determine CSV file
    if args.sheet:
        csv_file = download_google_sheet(args.sheet)
    elif args.csv_file:
        csv_file = args.csv_file
    else:
        parser.print_help()
        sys.exit(1)

    # Detect CSV format
    if args.format == 'auto':
        csv_format = detect_csv_format(csv_file)
        print(f'Detected format: {csv_format}')
    else:
        csv_format = args.format

    # Determine output directory for YAML files
    csv_dir = os.path.dirname(os.path.abspath(csv_file)) if csv_file else os.getcwd()
    yaml_output_dir = os.path.join(csv_dir, 'jira-issues')
    if not args.dry_run and YAML_EXPORT_AVAILABLE:
        os.makedirs(yaml_output_dir, exist_ok=True)

    # Build config
    config = {
        'project': args.project,
        'component': args.component,
        'sprint_id': None if args.no_sprint else args.sprint_id,
        'assignee': args.assignee,
        'epic': args.epic,
        'rate_limit': args.rate_limit,
        'yaml_output_dir': yaml_output_dir,
    }

    # Print header
    print(f'=== Creating Jira issues from {csv_file} ===')
    if args.dry_run:
        print('[DRY RUN MODE - No issues will be created]')
    print(f'Format: {csv_format}')
    print(f'Project: {config["project"]}')
    print(f'Component: {config["component"]}')
    if config['sprint_id']:
        print(f'Sprint: {config["sprint_id"]}')
    if config['assignee']:
        print(f'Assignee: {config["assignee"]}')
    if config['epic']:
        print(f'Epic: {config["epic"]}')
    if not args.dry_run and YAML_EXPORT_AVAILABLE:
        print(f'YAML output: {yaml_output_dir}')
    print()

    # Process based on format
    if csv_format == 'capacity-planning':
        created, duplicates, failed, yaml_files, skipped = process_capacity_planning_csv(
            csv_file, config, args.dry_run
        )
    else:
        created, duplicates, failed, yaml_files = process_standard_csv(
            csv_file, config, args.dry_run
        )
        skipped = 0

    # Print summary
    print('=== Summary ===')
    if args.dry_run:
        print(f'Would create: {len(created)} issues')
    else:
        print(f'Created: {len(created)} issues')
        if created:
            print('Issues:', ', '.join(created))

        if yaml_files:
            print(f'YAML files: {len(yaml_files)} exported to {yaml_output_dir}')

    if duplicates:
        print(f'Skipped (already exist): {len(duplicates)} issues')
        for dup in duplicates:
            print(f'  - {dup}')

    if skipped:
        print(f'Skipped: {skipped} empty rows')

    if failed:
        print(f'Failed: {len(failed)} issues')
        for f in failed:
            print(f'  - {f}')


if __name__ == '__main__':
    main()
