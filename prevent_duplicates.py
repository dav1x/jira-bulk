#!/usr/bin/env python3
"""
Helper functions for preventing duplicate issue creation.
Searches Jira BEFORE creating to find existing issues.
"""

import re
import subprocess
import time

def search_existing_issue(summary, project='CNF', status_filter=None, days_back=30):
    """
    Search for an existing issue with the same or very similar summary.

    Args:
        summary: Issue summary to search for
        project: Jira project key
        status_filter: Optional status filter (e.g., '~Closed' for not closed)
        days_back: Number of days to look back for recent issues (default: 30)

    Returns:
        Tuple of (issue_key, match_type) if found, else (None, None)
        match_type can be: 'exact', 'similar', or None
    """
    try:
        # Clean the summary for searching
        clean_summary = summary.strip()

        # FIRST: Search recent issues more thoroughly (within last N days)
        # This catches duplicates that might have slightly different wording
        jql_recent = f'project = {project} AND created >= -{days_back}d'

        if status_filter:
            jql_recent = f'project = {project} AND created >= -{days_back}d AND status {status_filter}'

        # Set COLUMNS to get full summary text (avoid truncation)
        import os
        env = os.environ.copy()
        env['COLUMNS'] = '500'

        result_recent = subprocess.run(
            ['jira', 'issue', 'list', '--jql', jql_recent, '--plain'],
            capture_output=True,
            text=True,
            timeout=15,
            env=env
        )

        if result_recent.returncode == 0:
            # Check recent issues first with stricter matching
            for line in result_recent.stdout.split('\n'):
                if not line.strip() or 'TYPE' in line or 'KEY' in line:
                    continue

                match = re.search(rf'{project}-\d+', line)
                if not match:
                    continue

                issue_key = match.group(0)

                # Parse tab-separated output
                # Format: TYPE\tKEY\t\tSUMMARY\t...\t...STATUS
                # Split by tab and filter out empty strings to handle multiple tabs
                parts = [p.strip() for p in line.split('\t') if p.strip()]
                # parts[0] = TYPE, parts[1] = KEY, parts[2] = SUMMARY, parts[3] = STATUS
                if len(parts) >= 3:
                    line_summary = parts[2]
                else:
                    # Fallback
                    parts = line.split(issue_key)
                    if len(parts) < 2:
                        continue
                    line_summary = parts[1].strip()
                    line_summary = re.sub(r'(To Do|In Progress|Done|Closed|Code Review|Review)$', '', line_summary).strip()

                # Check for exact match (normalized)
                if normalize_text(clean_summary) == normalize_text(line_summary):
                    return issue_key, 'exact'

                # For recent issues, use more aggressive similarity matching
                similarity = calculate_similarity(clean_summary, line_summary)
                if similarity > 0.85:  # Lower threshold for recent issues
                    return issue_key, 'similar'

        # SECOND: Broader search using Jira text search
        jql_parts = [f'project = {project}']

        if status_filter:
            jql_parts.append(f'status {status_filter}')

        # For JQL text search, extract key words and avoid special characters
        # that might cause issues with the ~ operator
        search_words = clean_summary.replace('"', '').replace('(', '').replace(')', '')
        search_words = search_words.replace('–', '-').replace('—', '-')
        # Take first meaningful chunk of words
        words = search_words.split()[:8]  # First 8 words usually enough for matching
        search_term = ' '.join(words)

        jql_parts.append(f'summary ~ "{search_term}"')

        jql = ' AND '.join(jql_parts)

        result = subprocess.run(
            ['jira', 'issue', 'list', '--jql', jql, '--plain'],
            capture_output=True,
            text=True,
            timeout=15,
            env=env
        )

        if result.returncode != 0:
            return None, None

        # Parse the output
        for line in result.stdout.split('\n'):
            if not line.strip() or 'TYPE' in line or 'KEY' in line:
                continue

            # Extract issue key
            match = re.search(rf'{project}-\d+', line)
            if not match:
                continue

            issue_key = match.group(0)

            # Get the summary from the line
            # Line format: TYPE\tKEY\t\tSUMMARY\t...\t...STATUS (tab-separated)
            # Split by tab and filter out empty strings to handle multiple tabs
            parts = [p.strip() for p in line.split('\t') if p.strip()]
            # parts[0] = TYPE, parts[1] = KEY, parts[2] = SUMMARY, parts[3] = STATUS
            if len(parts) >= 3:
                line_summary = parts[2]
            else:
                # Fallback: split by issue key
                parts = line.split(issue_key)
                if len(parts) < 2:
                    continue
                line_summary = parts[1].strip()
                # Remove status at the end
                line_summary = re.sub(r'(To Do|In Progress|Done|Closed|Code Review|Review)$', '', line_summary).strip()

            # Check for exact match (normalized)
            if normalize_text(clean_summary) == normalize_text(line_summary):
                return issue_key, 'exact'

            # Check for very similar (90%+ similarity)
            similarity = calculate_similarity(clean_summary, line_summary)
            if similarity > 0.9:
                return issue_key, 'similar'

        return None, None

    except Exception as e:
        print(f"    ⚠ Error searching for existing issue: {e}")
        return None, None

def normalize_text(text):
    """Normalize text for comparison by removing/replacing special characters."""
    # Replace various quote styles with standard quote (including Unicode variants)
    # chr(8220) = " (left double quote), chr(8221) = " (right double quote)
    # chr(8216) = ' (left single quote), chr(8217) = ' (right single quote)
    normalized = text.replace(chr(8220), '"').replace(chr(8221), '"')
    normalized = normalized.replace(chr(8216), "'").replace(chr(8217), "'")
    normalized = normalized.replace('"', '"').replace('"', '"').replace('„', '"')
    normalized = normalized.replace("'", "'").replace("'", "'")
    # Replace various dashes with standard dash
    # chr(8211) = – (en dash), chr(8212) = — (em dash)
    normalized = normalized.replace(chr(8211), '-').replace(chr(8212), '-')
    normalized = normalized.replace('–', '-').replace('—', '-').replace('−', '-')
    # Remove other punctuation for comparison
    normalized = normalized.replace('(', '').replace(')', '').replace('[', '').replace(']', '')
    return normalized.lower().strip()

def calculate_similarity(s1, s2):
    """Calculate similarity ratio between two strings."""
    # Simple character-level similarity
    if not s1 or not s2:
        return 0.0

    # Normalize both strings first
    norm_s1 = normalize_text(s1)
    norm_s2 = normalize_text(s2)

    # Check exact match after normalization
    if norm_s1 == norm_s2:
        return 1.0

    # Remove common words that don't matter
    stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'for', 'with', 'from', 'to', 'aka']

    def clean_text(text):
        words = text.split()
        return ' '.join([w for w in words if w not in stop_words])

    clean_s1 = clean_text(norm_s1)
    clean_s2 = clean_text(norm_s2)

    # Use Levenshtein-like approach
    if clean_s1 == clean_s2:
        return 1.0

    # Count matching words
    words1 = set(clean_s1.split())
    words2 = set(clean_s2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)

def check_before_create(summary, project='CNF', require_confirmation=True):
    """
    Check for existing issues before creating. Returns decision on whether to create.

    Args:
        summary: Summary of issue to create
        project: Jira project
        require_confirmation: If True, ask user before creating when similar found

    Returns:
        Tuple of (should_create: bool, existing_key: str or None, reason: str)
    """
    # First check open issues
    existing_key, match_type = search_existing_issue(summary, project, status_filter='!= Closed')

    if existing_key and match_type == 'exact':
        return False, existing_key, f"Exact match found (open): {existing_key}"

    if existing_key and match_type == 'similar':
        if require_confirmation:
            print(f"    ⚠ Similar open issue found: {existing_key}")
            print(f"      New: {summary[:70]}")
            # For now, skip - in interactive mode we'd ask
            return False, existing_key, f"Similar match found (open): {existing_key}"
        return False, existing_key, f"Similar match found (open): {existing_key}"

    # Check closed issues too (maybe we shouldn't recreate recently closed ones)
    existing_key, match_type = search_existing_issue(summary, project, status_filter='= Closed')

    if existing_key and match_type == 'exact':
        # Found exact match in closed issues - could be intentional recreation
        # For now, warn but allow
        print(f"    ℹ️  Note: Exact match exists in closed issues: {existing_key}")
        return True, None, "Creating (exact match exists but is closed)"

    # No duplicates found
    return True, None, "No duplicates found"

if __name__ == '__main__':
    # Test the functions
    import sys

    if len(sys.argv) < 2:
        print("Usage: prevent-duplicates.py 'Issue Summary to Search'")
        sys.exit(1)

    summary = sys.argv[1]
    project = sys.argv[2] if len(sys.argv) > 2 else 'CNF'

    print(f"Searching for: {summary}")
    print(f"Project: {project}")
    print()

    existing_key, match_type = search_existing_issue(summary, project, status_filter='!= Closed')

    if existing_key:
        print(f"✓ Found {match_type} match: {existing_key}")
    else:
        print("✗ No existing issue found")
