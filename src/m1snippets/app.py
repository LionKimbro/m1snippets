"""Tkinter snippet manager persisted as one M1 transport unit."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import uuid

import lionscliapp as app


BASIC_ASPECT = "tag:m1lattice.net,2026:aspect/basic"

g = {
    "root": None,
    "main-window": None,
    "editor-id": None,
    "status": "",
    "series-id": None,
    "created": None,
    "transport-id": None,
}

snippets = {}
transport_entities = {}
events = []
widgets = {}
reg = {
    "snippet-id": None,
    "snippet": None,
}


def utc_now_text():
    """Return an M1-compatible UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_data_path():
    """Return the M1 transport path inside lionscliapp's project folder."""
    return app.get_path("snippets.m1", "p")


def make_blank_snippet():
    """Create the in-memory representation of a fresh text snippet."""
    return {
        "id": str(uuid.uuid4()),
        "title": "",
        "name": "",
        "tags": [],
        "hook": "",
        "text": "",
        "created": utc_now_text(),
    }


def load_snippets():
    """Load snippet basic aspects and preserve all other M1 entity data."""
    path = get_data_path()
    snippets.clear()
    transport_entities.clear()
    g["series-id"] = None
    g["created"] = None
    g["transport-id"] = None

    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    header = data.get("m1")
    if not isinstance(header, dict) or header.get("version") != "3.0":
        raise ValueError(f"{path} is not an M1 Transport Specification 3.0 file.")
    if not isinstance(data.get("entities", {}), dict):
        raise ValueError(f"{path} has an invalid entities map.")

    g["series-id"] = header.get("series_id")
    g["created"] = header.get("created")
    g["transport-id"] = header.get("id")
    transport_entities.update(data["entities"])

    for entity_id, contribution in transport_entities.items():
        if not isinstance(contribution, dict):
            continue
        basic = contribution.get(BASIC_ASPECT)
        if not isinstance(basic, dict) or basic.get("typehint") != "text":
            continue
        tags = basic.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        snippets[entity_id] = {
            "id": entity_id,
            "title": string_value(basic.get("title")),
            "name": string_value(basic.get("name")),
            "tags": [string_value(tag) for tag in tags],
            "hook": string_value(basic.get("hook")),
            "text": string_value(basic.get("notes")),
            "created": string_value(basic.get("date")),
        }


def string_value(value):
    """Return a safe display string for a loose M1 basic field."""
    return value if isinstance(value, str) else ""


def save_snippets():
    """Atomically re-emit the complete M1 transport file."""
    path = get_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    series_id = g["series-id"] or str(uuid.uuid4())
    created = g["created"] or utc_now_text()
    data = {
        "m1": {
            "id": str(uuid.uuid4()),
            "series_id": series_id,
            "version": "3.0",
            "created": created,
            "timestamp": utc_now_text(),
            "title": "Snippets",
            "description": "Snippet records maintained by m1-snippets.",
        },
        "entities": transport_entities,
    }

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix="snippets-", suffix=".tmp", delete=False
    ) as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
        temporary_path = Path(file.name)
    temporary_path.replace(path)

    g["series-id"] = series_id
    g["created"] = created
    g["transport-id"] = data["m1"]["id"]


def update_snippet_entity(snippet):
    """Apply one snippet's basic aspect without discarding unknown aspects."""
    entity = transport_entities.setdefault(snippet["id"], {})
    if not isinstance(entity, dict):
        entity = {}
        transport_entities[snippet["id"]] = entity
    entity[BASIC_ASPECT] = {
        "typehint": "text",
        "title": snippet["title"],
        "name": snippet["name"],
        "tags": snippet["tags"],
        "hook": snippet["hook"],
        "notes": snippet["text"],
        "date": snippet["created"],
    }


def get_matching_snippets(query):
    """Return snippets matching every whitespace-separated search term."""
    terms = [term.casefold() for term in query.split()]
    matches = []
    for snippet in snippets.values():
        if all(snippet_matches_term(snippet, term) for term in terms):
            matches.append(snippet)
    matches.sort(key=lambda item: (item["created"], item["id"]), reverse=True)
    if not terms:
        return matches[:50]
    return matches


def snippet_matches_term(snippet, term):
    """Test one term against title, name, or individual tag."""
    if term in snippet["title"].casefold() or term in snippet["name"].casefold():
        return True
    return any(term == tag.casefold() for tag in snippet["tags"])


def post_event(event):
    """Queue a semantic UI event for the routine update cycle."""
    events.append(event)


def update_cycle():
    """Advance the tiny window machine and schedule its next heartbeat."""
    while events:
        handle_event(events.pop(0))
    g["root"].after(50, update_cycle)


def handle_event(event):
    """Handle one queued semantic event."""
    event_type = event["type"]
    if event_type == "NEW_REQUESTED":
        open_editor(None)
    elif event_type == "EDIT_REQUESTED":
        open_editor(event["snippet-id"])
    elif event_type == "COPY_REQUESTED":
        copy_snippet(event["snippet-id"])
    elif event_type == "SAVE_REQUESTED":
        save_editor_contents()
    elif event_type == "DELETE_REQUESTED":
        delete_current_snippet()


def create_main_window():
    """Create the main search and result window."""
    window = tk.Toplevel(g["root"])
    window.title("Snippets")
    window.minsize(500, 350)
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)
    g["main-window"] = window

    top = ttk.Frame(window, padding=8)
    top.grid(row=0, column=0, sticky="ew")
    top.columnconfigure(1, weight=1)
    ttk.Label(top, text="search:").grid(row=0, column=0, sticky="w")
    search_text = tk.StringVar()
    search = ttk.Entry(top, textvariable=search_text)
    search.grid(row=0, column=1, padx=(6, 6), sticky="ew")
    ttk.Button(top, text="new", command=lambda: post_event({"type": "NEW_REQUESTED"})).grid(row=0, column=2)
    widgets["search"] = search
    search_text.trace_add("write", lambda name, index, mode: refresh_results())

    results_frame = ttk.Frame(window, padding=(8, 0, 8, 0))
    results_frame.grid(row=1, column=0, sticky="nsew")
    results_frame.columnconfigure(0, weight=1)
    results_frame.rowconfigure(0, weight=1)
    canvas = tk.Canvas(results_frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    result_list = ttk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=result_list, anchor="nw")
    result_list.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_window, width=event.width))
    widgets["result-list"] = result_list

    status = ttk.Label(window, anchor="w", padding=(8, 5))
    status.grid(row=2, column=0, sticky="ew")
    widgets["status"] = status
    window.protocol("WM_DELETE_WINDOW", close_application)
    search.focus_set()


def refresh_results():
    """Project current search matches into the vertically scrollable list."""
    result_list = widgets.get("result-list")
    if result_list is None or not result_list.winfo_exists():
        return
    for child in result_list.winfo_children():
        child.destroy()
    matches = get_matching_snippets(widgets["search"].get())
    for snippet in matches:
        add_result_row(result_list, snippet)
    query = widgets["search"].get().strip()
    if g["status"]:
        status = g["status"]
    elif query:
        status = f"{len(matches)} matches / {len(snippets)} snippets"
    else:
        status = f"{len(snippets)} snippets"
    widgets["status"].configure(text=status)


def add_result_row(parent, snippet):
    """Project a searchable snippet into one clickable result row."""
    row = tk.Frame(parent, background="#071b3a", padx=8, pady=7)
    row.pack(fill="x", pady=(0, 4))
    row.columnconfigure(0, weight=1)
    title = tk.Label(
        row,
        text=snippet["title"] or "(untitled)",
        background="#071b3a",
        foreground="white",
        font=("TkDefaultFont", 12),
        anchor="w",
    )
    title.grid(row=0, column=0, sticky="w")
    ttk.Button(
        row,
        text="edit",
        command=lambda snippet_id=snippet["id"]: post_event({"type": "EDIT_REQUESTED", "snippet-id": snippet_id}),
    ).grid(row=0, column=1, rowspan=2, padx=(8, 0))
    hook = tk.Label(
        row,
        text=snippet["hook"],
        background="#071b3a",
        foreground="#c9d7ef",
        font=("TkDefaultFont", 8),
        anchor="w",
    )
    hook.grid(row=1, column=0, sticky="w")
    for widget in (row, title, hook):
        widget.bind(
            "<Button-1>",
            lambda event, snippet_id=snippet["id"]: post_event({"type": "COPY_REQUESTED", "snippet-id": snippet_id}),
        )


def open_editor(snippet_id):
    """Summon the single editor window for a new or existing snippet."""
    editor = widgets.get("editor-window")
    if editor is not None and editor.winfo_exists():
        g["editor-id"] = snippet_id
        load_editor_fields()
        editor.deiconify()
        editor.lift()
        editor.focus_force()
        return

    g["editor-id"] = snippet_id
    window = tk.Toplevel(g["root"])
    window.title("Edit Snippet" if snippet_id else "New Snippet")
    window.minsize(550, 400)
    window.columnconfigure(1, weight=1)
    window.rowconfigure(4, weight=1)
    widgets["editor-window"] = window

    for row, field in enumerate(("title", "name", "tags", "hook")):
        ttk.Label(window, text=f"{field}:").grid(row=row, column=0, padx=(8, 4), pady=4, sticky="w")
        entry = ttk.Entry(window, font=("TkDefaultFont", 14) if field == "title" else None)
        entry.grid(row=row, column=1, padx=(0, 8), pady=4, sticky="ew")
        widgets[f"editor-{field}"] = entry
    ttk.Label(window, text="text:").grid(row=4, column=0, padx=(8, 4), pady=4, sticky="nw")
    text_frame = ttk.Frame(window)
    text_frame.grid(row=4, column=1, padx=(0, 8), pady=4, sticky="nsew")
    text_frame.columnconfigure(0, weight=1)
    text_frame.rowconfigure(0, weight=1)
    text = tk.Text(text_frame, wrap="word")
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    widgets["editor-text"] = text
    delete_button = ttk.Button(
        window,
        text="delete",
        command=lambda: post_event({"type": "DELETE_REQUESTED"}),
    )
    delete_button.grid(row=5, column=0, padx=8, pady=(0, 8), sticky="w")
    widgets["editor-delete"] = delete_button
    ttk.Button(window, text="save", command=lambda: post_event({"type": "SAVE_REQUESTED"})).grid(
        row=5, column=1, padx=8, pady=(0, 8), sticky="e"
    )
    window.protocol("WM_DELETE_WINDOW", close_editor)
    load_editor_fields()
    widgets["editor-title"].focus_set()


def load_editor_fields():
    """Project the selected snippet into the editor form."""
    snippet = snippets.get(g["editor-id"]) if g["editor-id"] else make_blank_snippet()
    for field in ("title", "name", "hook"):
        entry = widgets[f"editor-{field}"]
        entry.delete(0, "end")
        entry.insert(0, snippet[field])
    tags = widgets["editor-tags"]
    tags.delete(0, "end")
    tags.insert(0, " ".join(snippet["tags"]))
    text = widgets["editor-text"]
    text.delete("1.0", "end")
    text.insert("1.0", snippet["text"])
    delete_button = widgets["editor-delete"]
    delete_button.configure(state="normal" if g["editor-id"] else "disabled")


def save_editor_contents():
    """Commit the editor form to an M1 basic aspect and close it."""
    snippet = snippets.get(g["editor-id"])
    if snippet is None:
        snippet = make_blank_snippet()
    snippet["title"] = widgets["editor-title"].get()
    snippet["name"] = widgets["editor-name"].get()
    snippet["tags"] = widgets["editor-tags"].get().split()
    snippet["hook"] = widgets["editor-hook"].get()
    snippet["text"] = widgets["editor-text"].get("1.0", "end-1c")
    snippets[snippet["id"]] = snippet
    update_snippet_entity(snippet)
    save_snippets()
    g["status"] = f"Saved: {snippet['title'] or '(untitled)'}"
    close_editor()
    refresh_results()


def delete_current_snippet():
    """Remove the current snippet after an explicit confirmation."""
    snippet_id = g["editor-id"]
    if snippet_id is None:
        return
    snippet = snippets[snippet_id]
    title = snippet["title"] or "(untitled)"
    should_delete = messagebox.askyesno(
        "Delete Snippet",
        f"Delete {title}? This cannot be undone from Snippets.",
        parent=widgets["editor-window"],
        icon="warning",
    )
    if not should_delete:
        return
    del snippets[snippet_id]
    transport_entities.pop(snippet_id, None)
    save_snippets()
    g["status"] = f"Deleted: {title}"
    close_editor()
    refresh_results()


def copy_snippet(snippet_id):
    """Copy one snippet's text to the system clipboard."""
    snippet = snippets[snippet_id]
    g["main-window"].clipboard_clear()
    g["main-window"].clipboard_append(snippet["text"])
    g["status"] = f"Copied: {snippet['title'] or '(untitled)'}"
    refresh_results()


def close_editor():
    """Discard the current editor form and remove its runtime widgets."""
    window = widgets.pop("editor-window", None)
    if window is not None and window.winfo_exists():
        window.destroy()
    for field in ("title", "name", "tags", "hook", "text", "delete"):
        widgets.pop(f"editor-{field}", None)
    g["editor-id"] = None


def close_application():
    """End the Tk runtime."""
    g["root"].destroy()


def run_snippets():
    """Start the Tk application after lionscliapp has prepared its context."""
    load_snippets()
    root = tk.Tk()
    root.withdraw()
    g["root"] = root
    app.attach_tk(root)
    create_main_window()
    refresh_results()
    update_cycle()
    root.mainloop()


def main():
    """Declare and launch the lionscliapp command."""
    app.declare_app("snippets", "0.1.0")
    app.describe_app("A small desktop snippet manager backed by M1 transport data.")
    app.declare_projectdir(".snippets")
    app.set_flag("uses_tkinter", True)
    app.declare_cmd("", run_snippets)
    app.set_cmd_flag("", "tkinter", True)
    app.set_cmd_flag("", "single_instance", True)
    app.main()


if __name__ == "__main__":
    main()
