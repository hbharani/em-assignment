"""
Document loading functionality for the backlog manager
"""

from pathlib import Path


def load_docs() -> dict[str, str]:
    """Load all markdown files from docs/ and README.md (hardcoded paths)"""
    script_dir = Path(__file__).parent.parent
    repo_root = script_dir.parent
    docs_dir = repo_root / "docs"

    docs_content = {}

    # Load top-level README.md first
    readme_path = repo_root / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
                docs_content["README.md"] = content
                print(f"📖 Loaded: README.md")
        except Exception as e:
            print(f"⚠️  Failed to load README.md: {e}")

    # Recursively find all .md files in docs/
    if docs_dir.exists():
        for md_file in docs_dir.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Use relative path as key
                    rel_path = md_file.relative_to(docs_dir)
                    key = f"docs/{rel_path}"
                    docs_content[key] = content
                    print(f"📖 Loaded: {key}")
            except Exception as e:
                print(f"⚠️  Failed to load {md_file}: {e}")
    else:
        print(f"⚠️  docs/ directory not found at {docs_dir}")

    return docs_content
