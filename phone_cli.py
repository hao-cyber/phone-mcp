#!/usr/bin/env python3
import click
import shlex
import subprocess
import json

def run_adb_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def get_total_count(content_uri, where=None):
    """Get total count of items for pagination
    
    Args:
        content_uri (str): Content provider URI to query
        where (str, optional): SQL WHERE clause for filtering
        
    Returns:
        tuple: (success, count/error_message)
            - If successful, returns (True, count)
            - If failed, returns (False, error_message)
            
    Example:
        success, result = get_total_count('content://sms/inbox')
        if success:
            total_count = result
        else:
            error_msg = result
    """
    command = f'adb shell content query --uri {content_uri} --projection count:count(*)'
    if where:
        command += f' --where "{where}"'
    success, output = run_adb_command(command)
    
    if not success:
        return False, f"Failed to get count: {output}"
        
    if not output or not output.strip():
        return False, "Empty response from content query"
        
    try:
        count = int(output.strip().split('count=')[1])
        return True, count
    except (IndexError, ValueError) as e:
        return False, f"Failed to parse count from output: {str(e)}"

@click.group()
def cli():
    """Phone MCP CLI tool for Android device control"""
    pass

@cli.command()
@click.option('--account-name', '-n', default='你的账户名', help='Account name for the contact')
@click.option('--account-type', '-t', default='com.google', help='Account type (default: com.google)')
def create_contact(account_name, account_type):
    """Create a new raw contact with specified account details"""
    command = (
        f'adb shell content insert --uri content://com.android.contacts/raw_contacts '
        f'--bind account_type:s:{shlex.quote(account_type)} '
        f'--bind account_name:s:{shlex.quote(account_name)}'
    )
    
    success, output = run_adb_command(command)
    result = {
        'success': success,
        'message': output
    }
    click.echo(json.dumps(result, ensure_ascii=False))
    if not success:
        exit(1)

@cli.command()
@click.option('--page', default=1, help='Page number (starts from 1)')
@click.option('--page-size', default=10, help='Number of items per page')
def get_contacts(page, page_size):
    """Get contacts with pagination support
    
    Returns a JSON object containing:
    - total_count: Total number of contacts
    - total_pages: Total number of pages
    - current_page: Current page number
    - page_size: Number of items per page
    - contacts: List of contacts in current page
    """
    # Get total count
    total_count = get_total_count('content://com.android.contacts/contacts')
    total_pages = (total_count + page_size - 1) // page_size
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages if total_pages > 0 else 1
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    command = (
        f'adb shell content query --uri content://com.android.contacts/contacts '
        f'--projection _id:display_name:has_phone_number '
        f'--limit {page_size} --offset {offset}'
    )
    
    success, output = run_adb_command(command)
    contacts = []
    if success and output:
        for line in output.strip().split('\n'):
            if 'Row:' in line:
                contact_data = line.split('Row:')[1].strip()
                contacts.append(contact_data)
    
    result = {
        'success': success,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'page_size': page_size,
        'contacts': contacts
    }
    click.echo(json.dumps(result, ensure_ascii=False))
    if not success:
        exit(1)

@cli.command()
@click.option('--page', default=1, help='Page number (starts from 1)')
@click.option('--page-size', default=10, help='Number of items per page')
def receive_text_messages(page, page_size):
    """Get received text messages with pagination support
    
    Returns a JSON object containing:
    - total_count: Total number of messages
    - total_pages: Total number of pages
    - current_page: Current page number
    - page_size: Number of items per page
    - messages: List of messages in current page
    """
    # Get total count
    total_count = get_total_count('content://sms/inbox')
    total_pages = (total_count + page_size - 1) // page_size
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages if total_pages > 0 else 1
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    command = (
        f'adb shell content query --uri content://sms/inbox '
        f'--projection _id:address:body:date:read '
        f'--sort "date DESC" '
        f'--limit {page_size} --offset {offset}'
    )
    
    success, output = run_adb_command(command)
    messages = []
    if success and output:
        for line in output.strip().split('\n'):
            if 'Row:' in line:
                message_data = line.split('Row:')[1].strip()
                messages.append(message_data)
    
    result = {
        'success': success,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'page_size': page_size,
        'messages': messages
    }
    click.echo(json.dumps(result, ensure_ascii=False))
    if not success:
        exit(1)

@cli.command()
@click.option('--page', default=1, help='Page number (starts from 1)')
@click.option('--page-size', default=10, help='Number of items per page')
def get_sent_messages(page, page_size):
    """Get sent text messages with pagination support
    
    Returns a JSON object containing:
    - total_count: Total number of messages
    - total_pages: Total number of pages
    - current_page: Current page number
    - page_size: Number of items per page
    - messages: List of messages in current page
    """
    # Get total count
    total_count = get_total_count('content://sms/sent')
    total_pages = (total_count + page_size - 1) // page_size
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages if total_pages > 0 else 1
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    command = (
        f'adb shell content query --uri content://sms/sent '
        f'--projection _id:address:body:date '
        f'--sort "date DESC" '
        f'--limit {page_size} --offset {offset}'
    )
    
    success, output = run_adb_command(command)
    messages = []
    if success and output:
        for line in output.strip().split('\n'):
            if 'Row:' in line:
                message_data = line.split('Row:')[1].strip()
                messages.append(message_data)
    
    result = {
        'success': success,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'page_size': page_size,
        'messages': messages
    }
    click.echo(json.dumps(result, ensure_ascii=False))
    if not success:
        exit(1)

@cli.command()
@click.option('--page', default=1, help='Page number (starts from 1)')
@click.option('--page-size', default=10, help='Number of items per page')
@click.option('--package-name', required=True, help='Package name of the app')
def get_app_shortcuts(page, page_size, package_name):
    """Get app shortcuts with pagination support
    
    Returns a JSON object containing:
    - total_count: Total number of shortcuts
    - total_pages: Total number of pages
    - current_page: Current page number
    - page_size: Number of items per page
    - shortcuts: List of shortcuts in current page
    """
    # Get total count with package filter
    where = f"package={shlex.quote(package_name)}"
    total_count = get_total_count('content://com.android.launcher3.settings/favorites', where)
    total_pages = (total_count + page_size - 1) // page_size
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages if total_pages > 0 else 1
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    command = (
        f'adb shell content query --uri content://com.android.launcher3.settings/favorites '
        f'--projection _id:title:intent:itemType '
        f'--where "{where}" '
        f'--limit {page_size} --offset {offset}'
    )
    
    success, output = run_adb_command(command)
    shortcuts = []
    if success and output:
        for line in output.strip().split('\n'):
            if 'Row:' in line:
                shortcut_data = line.split('Row:')[1].strip()
                shortcuts.append(shortcut_data)
    
    result = {
        'success': success,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'page_size': page_size,
        'shortcuts': shortcuts
    }
    click.echo(json.dumps(result, ensure_ascii=False))
    if not success:
        exit(1)

@cli.command()
def check():
    """Check device connection"""
    success, output = run_adb_command('adb devices')
    click.echo(output)

if __name__ == '__main__':
    cli() 