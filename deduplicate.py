#!/usr/bin/env python3
"""Find and resolve duplicate Jira issues, keeping the one with the most information."""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict

def get_issue_details(issue_key):
    """Get full details of a Jira issue."""
    try:
        result = subprocess.run(
            ['jira', 'issue', 'view', issue_key, '--comments', '100'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        output = result.stdout

        # Parse the output to extract details
        details = {
            'key': issue_key,
            'summary': '',
            'description': '',
            'status': '',
            'assignee': '',
            'labels': [],
            'links': 0,
            'comments': 0,
            'epic': '',
            'created': '',
        }

        # Extract information from output
        lines = output.split('\n')
        in_description = False
        description_lines = []

        for line in lines:
            if 'Summary:' in line or issue_key in line:
                # Try to extract summary
                parts = line.split(issue_key)
                if len(parts) > 1:
                    details['summary'] = parts[1].strip()
            elif 'Status:' in line or '🚧' in line or '✅' in line:
                if 'To Do' in line:
                    details['status'] = 'To Do'
                elif 'Done' in line or 'Closed' in line:
                    details['status'] = 'Closed'
                elif 'In Progress' in line:
                    details['status'] = 'In Progress'
            elif 'Assignee:' in line or '👷' in line:
                if 'Unassigned' not in line:
                    details['assignee'] = 'assigned'
            elif 'linked' in line:
                match = re.search(r'(\d+)\s+linked', line)
                if match:
                    details['links'] = int(match.group(1))
            elif 'comments' in line or '💭' in line:
                match = re.search(r'(\d+)\s+comments?', line)
                if match:
                    details['comments'] = int(match.group(1))
            elif line.strip().startswith('# '):
                in_description = True
                description_lines.append(line)
            elif in_description and line.strip():
                description_lines.append(line)

        details['description'] = '\n'.join(description_lines)

        return details

    except Exception as e:
        print(f"Error getting details for {issue_key}: {e}")
        return None

def calculate_information_score(details):
    """Calculate a score based on how much information an issue contains."""
    if not details:
        return 0

    score = 0

    # Description length
    desc_len = len(details.get('description', ''))
    score += min(desc_len, 500) / 10  # Cap at 50 points for description

    # Has assignee
    if details.get('assignee'):
        score += 10

    # Number of links
    score += details.get('links', 0) * 20

    # Number of comments
    score += details.get('comments', 0) * 15

    # Prefer non-closed issues
    if details.get('status') != 'Closed':
        score += 30

    # Epic link
    if details.get('epic'):
        score += 10

    return score

def find_duplicates_in_sprint(sprint_id=None, label=None, project='CNF'):
    """Find duplicate issues by matching summaries."""
    # Build search command
    cmd = ['jira', 'issue', 'list', f'-p{project}', '--plain']

    if label:
        cmd.append(f'-l{label}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Error listing issues: {result.stderr}")
            return {}

        # Parse output and group by summary
        issues_by_summary = defaultdict(list)

        for line in result.stdout.split('\n'):
            if not line.strip() or 'TYPE' in line or 'KEY' in line:
                continue

            # Extract issue key
            match = re.search(r'CNF-\d+', line)
            if not match:
                continue

            issue_key = match.group(0)

            # Try to extract summary (everything after the key and status)
            parts = line.split(issue_key)
            if len(parts) < 2:
                continue

            # Clean up the summary
            summary = parts[1].strip()
            # Remove status indicators
            summary = re.sub(r'(To Do|In Progress|Done|Closed)', '', summary).strip()
            # Remove emoji and special chars
            summary = re.sub(r'[🚧✅⭐🐞👷💭🧵⌛🔑️]', '', summary).strip()

            if summary:
                issues_by_summary[summary.lower()].append(issue_key)

        # Filter to only duplicates (2+ issues with same summary)
        duplicates = {k: v for k, v in issues_by_summary.items() if len(v) > 1}

        return duplicates

    except Exception as e:
        print(f"Error finding duplicates: {e}")
        return {}

def get_issue_number(issue_key):
    """Extract the numeric part of an issue key for age comparison."""
    match = re.search(r'-(\d+)$', issue_key)
    return int(match.group(1)) if match else 0

def resolve_duplicates(duplicate_groups, dry_run=False):
    """For each group of duplicates, keep the one with most info and close the others."""

    kept = []
    closed = []

    for summary, issue_keys in duplicate_groups.items():
        print(f"\n{'='*80}")
        print(f"Found {len(issue_keys)} duplicates: {summary[:60]}...")

        # Sort by issue number (oldest first) to show chronologically
        issue_keys_sorted = sorted(issue_keys, key=get_issue_number)
        print(f"Issues: {', '.join(issue_keys_sorted)}")
        print()

        # Get details for all issues
        issues_with_scores = []
        failed_issues = []

        for key in issue_keys_sorted:
            print(f"  Analyzing {key}...", end=' ')
            details = get_issue_details(key)
            if details:
                score = calculate_information_score(details)
                issues_with_scores.append((key, details, score))
                print(f"Score: {score:.1f}")
            else:
                print("Failed to get details (rate limit?)")
                failed_issues.append(key)
                # Add small delay before trying next one
                import time
                time.sleep(1)

        # If we couldn't get details for any issues, skip this group
        if not issues_with_scores:
            print("  ⚠ Could not analyze any issues - skipping this group")
            print("  💡 Try running again in a few minutes when rate limits reset")
            continue

        # If some failed, prefer keeping the oldest successful one
        # Sort by: score (desc), then by issue number (asc - older is lower)
        issues_with_scores.sort(key=lambda x: (-x[2], get_issue_number(x[0])))

        # Keep the one with highest score (and oldest if tied)
        keep_key, keep_details, keep_score = issues_with_scores[0]
        print(f"\n  ✓ KEEPING: {keep_key} (score: {keep_score:.1f}, created first among scored issues)")
        print(f"    Status: {keep_details.get('status')}")
        print(f"    Description: {len(keep_details.get('description', ''))} chars")
        print(f"    Links: {keep_details.get('links')}, Comments: {keep_details.get('comments')}")

        # Warn if we failed to get details for some issues
        if failed_issues:
            print(f"  ⚠ WARNING: Could not analyze {len(failed_issues)} issues: {', '.join(failed_issues)}")
            print(f"    These might be older and have more info - verify manually!")

        kept.append(keep_key)

        # Close the others
        for close_key, close_details, close_score in issues_with_scores[1:]:
            print(f"\n  ✗ CLOSING: {close_key} (score: {close_score:.1f})")
            print(f"    Status: {close_details.get('status')}")

            if dry_run:
                print(f"    [DRY RUN] Would close with link to {keep_key}")
            else:
                try:
                    # Close the issue
                    comment = f"Duplicate of {keep_key} - closing as the other issue has more information"
                    result = subprocess.run(
                        ['jira', 'issue', 'move', close_key, 'Closed', '--comment', comment],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        print(f"    ✓ Closed successfully")
                        closed.append(close_key)
                    else:
                        print(f"    ✗ Failed to close: {result.stderr}")
                except Exception as e:
                    print(f"    ✗ Error closing: {e}")

    return kept, closed

def main():
    parser = argparse.ArgumentParser(
        description='Find and resolve duplicate Jira issues, keeping the one with most information'
    )
    parser.add_argument('--sprint', help='Sprint ID to search in')
    parser.add_argument('--label', default='inbound-int-50', help='Label to filter by (default: inbound-int-50)')
    parser.add_argument('--project', default='CNF', help='Jira project (default: CNF)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without closing issues')

    args = parser.parse_args()

    print("="*80)
    print("JIRA DUPLICATE RESOLVER")
    print("="*80)
    if args.dry_run:
        print("[DRY RUN MODE - No issues will be closed]")
    print(f"Project: {args.project}")
    if args.label:
        print(f"Label: {args.label}")
    print()

    print("Searching for duplicates...")
    duplicates = find_duplicates_in_sprint(args.sprint, args.label, args.project)

    if not duplicates:
        print("✓ No duplicates found!")
        return

    print(f"\nFound {len(duplicates)} sets of duplicates ({sum(len(v) for v in duplicates.values())} total issues)")

    kept, closed = resolve_duplicates(duplicates, dry_run=args.dry_run)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    if args.dry_run:
        print(f"Would keep:  {len(kept)} issues")
        print(f"Would close: {len(closed)} issues")
    else:
        print(f"Kept:   {len(kept)} issues - {', '.join(kept)}")
        print(f"Closed: {len(closed)} issues - {', '.join(closed)}")

if __name__ == '__main__':
    main()
