import os

def print_tree(startpath='.', indent='', prefix=''):
    """Выводит красивую структуру папок и файлов."""
    try:
        items = sorted(os.listdir(startpath))
    except PermissionError:
        return
    
    # Исключаем скрытые папки и служебные
    items = [i for i in items if not i.startswith('.') and i not in ['__pycache__', '.venv', 'venv', 'node_modules']]
    
    for i, item in enumerate(items):
        path = os.path.join(startpath, item)
        is_last = (i == len(items) - 1)
        connector = '└── ' if is_last else '├── '
        
        if os.path.isdir(path):
            print(f"{prefix}{connector}{item}/")
            extension = '    ' if is_last else '│   '
            print_tree(path, indent, prefix + extension)
        else:
            print(f"{prefix}{connector}{item}")

print(" otcheti-system/")
print_tree('.')