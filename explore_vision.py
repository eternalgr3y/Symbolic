import os
import sys

def explore_docs():
    """Explore the documentation to understand the vision."""
    docs_path = "docs"
    
    if not os.path.exists(docs_path):
        print("No docs folder found. Let me check the current directory structure...")
        for item in os.listdir("."):
            if os.path.isdir(item):
                print(f"📁 {item}/")
                # Check if there are any markdown or text files
                try:
                    for subitem in os.listdir(item)[:5]:  # First 5 items
                        if subitem.endswith(('.md', '.txt', '.rst')):
                            print(f"   📄 {subitem}")
                except:
                    pass
            elif item.endswith(('.md', '.txt', '.rst', '.pdf')):
                print(f"📄 {item}")
        return
    
    print("🔍 Exploring documentation to understand the vision...")
    print("=" * 60)
    
    # Walk through docs directory
    for root, dirs, files in os.walk(docs_path):
        level = root.replace(docs_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}📁 {os.path.basename(root)}/")
        
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            if file.endswith(('.md', '.txt', '.rst', '.pdf')):
                print(f"{subindent}📄 {file}")
                
                # Try to read key files
                if file.lower() in ['readme.md', 'overview.md', 'vision.md', 'architecture.md']:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()[:2000]  # First 2000 chars
                            print(f"\n{subindent}--- Content Preview ---")
                            print(f"{subindent}{content[:500]}...")
                            print()
                    except:
                        pass

if __name__ == "__main__":
    explore_docs()