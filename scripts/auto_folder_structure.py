import os

IGNORE_DIRS = {'.git', '__pycache__', 'venv'}

def generate_structure(root_dir, output_file="structure.txt", max_depth=2):
    lines = []

    root_dir = os.path.abspath(root_dir)

    for root, dirs, files in os.walk(root_dir):
        level = root.replace(root_dir, "").count(os.sep)

        # Remove ignored folders
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        # Stop going deeper than max_depth
        if level > max_depth:
            dirs[:] = []
            continue

        indent = "│   " * level
        folder_name = os.path.basename(root)

        lines.append(f"{indent}├── {folder_name}/")

        # Show files only within allowed depth
        if level < max_depth:
            sub_indent = "│   " * (level + 1)
            for file in files:
                lines.append(f"{sub_indent}├── {file}")

        # Prevent deeper traversal
        if level == max_depth:
            dirs[:] = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Structure saved to {output_file}")


if __name__ == "__main__":
    project_folder_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generate_structure(project_folder_path, max_depth=3)