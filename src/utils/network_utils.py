import requests
import time
import concurrent.futures
from urllib.parse import urlparse


def retry_with_backoff(func, max_retries=3, delay=1, backoff=2, 
                       exceptions=(requests.exceptions.RequestException,)):
    """Retry function with exponential backoff."""
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(current_delay)
                current_delay *= backoff
    
    raise last_exception


def validate_mod_urls(mods, progress_callback=None, timeout=3, max_workers=10):
    """Validate URLs in parallel, categorize by domain (github/gdrive/other/failed)."""
    results = {
        'github': [],
        'google_drive': [],
        'other': {},
        'failed': []
    }
    
    def check_url(mod, index):
        """Check a single URL. Returns (index, category, mod, domain, status, error)."""
        if progress_callback:
            progress_callback(index + 1, len(mods), mod.get('name', 'Unknown'))
        
        url = mod.get('download_url', '')
        if not url:
            return (index, 'failed', mod, None, 0, 'No download URL')
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
        except (ValueError, AttributeError):
            domain = 'unknown'
        
        is_github = 'github.com' in domain
        is_gdrive = 'drive.google.com' in domain or 'drive.usercontent.google.com' in domain
        
        try:
            try:
                response = requests.head(url, timeout=timeout, allow_redirects=True)
                if response.status_code == 403:
                    raise requests.exceptions.RequestException("HEAD blocked, trying GET")
            except (requests.exceptions.RequestException, requests.exceptions.Timeout):
                response = requests.get(url, timeout=timeout, allow_redirects=True, 
                                       headers={'Range': 'bytes=0-0'}, stream=True)
                response.close()
            
            if 200 <= response.status_code < 300:
                if is_github:
                    return (index, 'github', mod, domain, response.status_code, None)
                elif is_gdrive:
                    return (index, 'google_drive', mod, domain, response.status_code, None)
                else:
                    return (index, 'other', mod, domain, response.status_code, None)
            else:
                return (index, 'failed', mod, domain, response.status_code, f'HTTP {response.status_code}')
        except requests.exceptions.Timeout:
            return (index, 'failed', mod, domain, 0, 'Timeout (3s)')
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if len(error_msg) > 50:
                error_msg = error_msg[:47] + '...'
            return (index, 'failed', mod, domain, 0, error_msg)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(check_url, mod, i) for i, mod in enumerate(mods)]
        
        for future in concurrent.futures.as_completed(futures):
            index, category, mod, domain, status, error = future.result()
            
            if category == 'github':
                results['github'].append(mod)
            elif category == 'google_drive':
                results['google_drive'].append(mod)
            elif category == 'other':
                if domain not in results['other']:
                    results['other'][domain] = []
                results['other'][domain].append(mod)
            elif category == 'failed':
                results['failed'].append({
                    'mod': mod,
                    'status': status,
                    'error': error
                })
    
    if results['failed']:
        retry_candidates = []
        permanent_failures = []
        
        for fail in results['failed']:
            if fail['status'] == 0:
                retry_candidates.append(fail)
            else:
                permanent_failures.append(fail)
        
        if retry_candidates:
            if progress_callback:
                progress_callback(len(mods), len(mods), f"Retrying {len(retry_candidates)} failed...")
            
            results['failed'] = permanent_failures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                retry_futures = [executor.submit(check_url, fail['mod'], i) 
                                for i, fail in enumerate(retry_candidates)]
                
                for future in concurrent.futures.as_completed(retry_futures):
                    index, category, mod, domain, status, error = future.result()
                    
                    if category == 'github':
                        results['github'].append(mod)
                    elif category == 'google_drive':
                        results['google_drive'].append(mod)
                    elif category == 'other':
                        if domain not in results['other']:
                            results['other'][domain] = []
                        results['other'][domain].append(mod)
                    elif category == 'failed':
                        results['failed'].append({
                            'mod': mod,
                            'status': status,
                            'error': error
                        })
    
    return results
