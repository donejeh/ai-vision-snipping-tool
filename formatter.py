import re
import tkinter as tk

# Regular expression pattern for inline bold text (e.g., **bold**)
BOLD_PATTERN = re.compile(r'\*\*(.*?)\*\*')

def insert_bold_text(text_widget, line, base_tag=None):
    """
    Inserts text into 'text_widget' while detecting **bold** segments.
    Optionally applies a base_tag (e.g., "heading" or "list") to the entire line.
    """
    start_idx = 0
    for match in BOLD_PATTERN.finditer(line):
        before_text = line[start_idx:match.start()]
        if before_text:
            text_widget.insert(tk.END, before_text, base_tag)
        bold_text = match.group(1)
        text_widget.insert(tk.END, bold_text, (base_tag, "bold") if base_tag else ("bold",))
        start_idx = match.end()
    if start_idx < len(line):
        text_widget.insert(tk.END, line[start_idx:], base_tag)

def format_and_insert_text(text_widget, content):
    """
    Parses the content with markdown-like formatting cues and inserts it
    into the provided Tkinter text widget.

    Supported formatting:
      - Code blocks wrapped in triple backticks (```).
      - Headings (lines starting with "### ").
      - Subheadings (lines starting with "## ").
      - List items (lines starting with "- ").
      - Inline bold text (enclosed in **).
    """
    text_widget.delete(1.0, tk.END)
    in_code_block = False
    code_lines = []

    for line in content.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                code_text = "\n".join(code_lines)
                text_widget.insert(tk.END, code_text + "\n", "code")
                in_code_block = False
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if stripped_line.startswith("### "):
            insert_bold_text(text_widget, stripped_line[4:].strip(), "heading")
            text_widget.insert(tk.END, "\n")
        elif stripped_line.startswith("## "):
            insert_bold_text(text_widget, stripped_line[3:].strip(), "subheading")
            text_widget.insert(tk.END, "\n")
        elif stripped_line.startswith("- "):
            insert_bold_text(text_widget, stripped_line, "list")
            text_widget.insert(tk.END, "\n")
        else:
            insert_bold_text(text_widget, line)
            text_widget.insert(tk.END, "\n")
