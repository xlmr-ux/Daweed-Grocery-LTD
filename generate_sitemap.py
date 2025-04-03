import os
import sys
from django.urls import get_resolver
from django.conf import settings
import re

def get_all_urls():
    """Extract all URLs and their linked views from urlpatterns."""
    urls = []
    resolver = get_resolver()
    
    def process_patterns(patterns, prefix=''):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                process_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
            elif hasattr(pattern, 'callback'):
                urls.append({
                    'url': prefix + str(pattern.pattern),
                    'view': pattern.callback.__name__,
                    'module': pattern.callback.__module__
                })
    
    process_patterns(resolver.url_patterns)
    return urls

def find_template(view_function, module_name):
    """Find template path based on view and app name."""
    app_name = module_name.split('.')[0]
    possible_paths = [
        f"{app_name}/templates/{view_function.replace('_view', '')}.html",
        f"templates/{app_name}/{view_function.replace('_view', '')}.html",
        f"{app_name}/templates/{view_function}.html",
        f"templates/{view_function}.html"
    ]
    
    for path in possible_paths:
        full_path = os.path.join(settings.BASE_DIR, path)
        if os.path.exists(full_path):
            return path
    return "Template not found (admin views use built-in templates)"

def find_static_files(template_path):
    """Find CSS/JS files in templates."""
    if "not found" in template_path.lower():
        return {}
    
    full_path = os.path.join(settings.BASE_DIR, template_path)
    if not os.path.exists(full_path):
        return {}
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    css_files = re.findall(r'href=["\']({}.*?\.css)["\']'.format(settings.STATIC_URL), content)
    js_files = re.findall(r'src=["\']({}.*?\.js)["\']'.format(settings.STATIC_URL), content)
    return {'css': css_files, 'js': js_files}

def generate_report():
    report = []
    urls = get_all_urls()
    
    for entry in urls:
        # Skip admin patterns
        if 'django.contrib.admin' in entry['module']:
            continue
            
        template_path = find_template(entry['view'], entry['module'])
        static_files = find_static_files(template_path)
        
        report.append({
            'url': entry['url'],
            'view': f"{entry['module']}.{entry['view']}",
            'template': template_path,
            'static_dependencies': static_files
        })
    
    return report

if __name__ == "__main__":
    # Configure Django environment
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_path)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simple_multivendor_site.settings')
    
    try:
        import django
        django.setup()
        
        sitemap = generate_report()
        
        # Configure output for Windows console
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
        print("\n" + "="*50)
        print("Multivendor Site Structure Report")
        print("="*50 + "\n")
        
        for page in sitemap:
            print(f"URL: {page['url']}")
            print(f"View: {page['view']}")
            print(f"Template: {page['template']}")
            if page['static_dependencies'].get('css'):
                print("CSS Files:", ", ".join(page['static_dependencies']['css']))
            if page['static_dependencies'].get('js'):
                print("JS Files:", ", ".join(page['static_dependencies']['js']))
            print("-"*50)
        
        print(f"\nSitemap generated successfully! (Found {len(sitemap)} URLs)")
        
    except Exception as e:
        print(f"\nError generating sitemap: {str(e)}")
        print("Please verify:")
        print("1. You're running from the project root directory")
        print("2. All apps are properly installed in settings.py")
        print("3. The virtual environment is activated")
        sys.exit(1)