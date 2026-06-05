#!/usr/bin/env python3
"""Export Jira issue details to YAML format."""

import json
import re
import subprocess
import yaml
from datetime import datetime

def get_issue_details_json(issue_key):
    """Get issue details in JSON format from jira CLI."""
    try:
        result = subprocess.run(
            ['jira', 'issue', 'view', issue_key, '--raw'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        # Parse JSON output
        data = json.loads(result.stdout)
        return data

    except Exception as e:
        print(f"Error getting details for {issue_key}: {e}")
        return None

def get_issue_details_text(issue_key):
    """Get issue details in text format as fallback."""
    try:
        result = subprocess.run(
            ['jira', 'issue', 'view', issue_key],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        output = result.stdout

        # Parse key information from text output
        details = {
            'key': issue_key,
            'summary': '',
            'type': '',
            'status': '',
            'assignee': 'Unassigned',
            'reporter': '',
            'priority': '',
            'labels': [],
            'components': [],
            'description': '',
            'created': '',
            'updated': '',
        }

        lines = output.split('\n')
        for i, line in enumerate(lines):
            # Extract summary (usually in first few lines with issue key)
            if issue_key in line and not details['summary']:
                # Try to extract summary after the key
                parts = line.split(issue_key)
                if len(parts) > 1:
                    summary = parts[1].strip()
                    # Remove emoji and status indicators
                    summary = re.sub(r'[🚧✅⭐🐞👷💭🧵⌛🔑️]', '', summary).strip()
                    summary = re.sub(r'(To Do|In Progress|Done|Closed|Code Review)', '', summary).strip()
                    details['summary'] = summary

            # Extract type
            if '⭐ Story' in line or 'Story' in line:
                details['type'] = 'Story'
            elif '🐞 Bug' in line or 'Bug' in line:
                details['type'] = 'Bug'
            elif 'Task' in line:
                details['type'] = 'Task'

            # Extract status
            if 'To Do' in line:
                details['status'] = 'To Do'
            elif 'In Progress' in line:
                details['status'] = 'In Progress'
            elif 'Done' in line or 'Closed' in line:
                details['status'] = 'Closed'

            # Extract description (starts with #)
            if line.strip().startswith('# '):
                desc_lines = []
                for j in range(i, len(lines)):
                    if lines[j].strip().startswith('#') or (lines[j].strip() and not lines[j].startswith(' ')):
                        desc_lines.append(lines[j].strip())
                    elif not lines[j].strip():
                        break
                details['description'] = '\n'.join(desc_lines)
                break

        return details

    except Exception as e:
        print(f"Error getting text details for {issue_key}: {e}")
        return None

def export_to_yaml(issue_key, output_dir='.'):
    """Export a Jira issue to YAML file."""

    # Try JSON first (more reliable)
    data = get_issue_details_json(issue_key)

    if data:
        # Extract relevant fields from JSON
        fields = data.get('fields', {})

        yaml_data = {
            'key': issue_key,
            'id': data.get('id'),
            'self': data.get('self'),
            'type': fields.get('issuetype', {}).get('name', 'Unknown'),
            'summary': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'status': fields.get('status', {}).get('name', 'Unknown'),
            'priority': fields.get('priority', {}).get('name', '') if fields.get('priority') else '',
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
            'reporter': fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else '',
            'created': fields.get('created', ''),
            'updated': fields.get('updated', ''),
            'labels': fields.get('labels', []),
            'components': [c.get('name') for c in fields.get('components', [])],
            'fix_versions': [v.get('name') for v in fields.get('fixVersions', [])],
            'project': {
                'key': fields.get('project', {}).get('key', ''),
                'name': fields.get('project', {}).get('name', ''),
            },
        }

        # Add custom fields if they exist
        custom_fields = {}
        for key, value in fields.items():
            if key.startswith('customfield_') and value:
                custom_fields[key] = value

        if custom_fields:
            yaml_data['custom_fields'] = custom_fields

    else:
        # Fallback to text parsing
        details = get_issue_details_text(issue_key)
        if not details:
            return None

        yaml_data = details

    # Add metadata
    yaml_data['exported_at'] = datetime.now().isoformat()
    yaml_data['exported_by'] = 'claude-jira bulk import tool'

    # Write to YAML file
    filename = f"{output_dir}/{issue_key}.yaml"

    try:
        with open(filename, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return filename
    except Exception as e:
        print(f"Error writing YAML file: {e}")
        return None

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: jira_yaml_export.py ISSUE-KEY [output_dir]")
        sys.exit(1)

    issue_key = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'

    filename = export_to_yaml(issue_key, output_dir)

    if filename:
        print(f"✓ Exported to: {filename}")
    else:
        print("✗ Failed to export")
