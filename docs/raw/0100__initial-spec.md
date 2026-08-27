```
date: 2026-08-26
chatgpt: https://chatgpt.com/c/6a8fb1b6-02f8-83e8-bba4-b31b51304838
title: Initial Spec for m1snippets
```

# Snippets

**Python package:** `m1-snippets`
**CLI command:** `snippets`

Build a small desktop snippet manager in Python using **tkinter**. Keep the implementation simple, explicit, and procedural. Do not introduce application classes, manager/controller objects, frameworks, databases, or abstraction layers that are not needed.

The application has two windows: the **main/search window** and an **editor window**.

## Main Window

The main window has three vertical areas.

At the top:

```text
search: [................................................] [new]
```

The search field should receive keyboard focus when the program starts.

The center is a vertically scrollable list of matching snippets. Each snippet is shown approximately like:

```text
---------------------------------------------------------
 TITLE                                                   [edit]
 hook text...
---------------------------------------------------------
```

The title should be visually prominent, approximately 12pt. The hook should be smaller, approximately 8pt.

The results area should expand to fill available window space and have a vertical scrollbar.

At the bottom is a status bar. Initially it can simply show useful information such as:

```text
23 snippets
```

or:

```text
8 matches / 23 snippets
```

### Search

Search updates the result list as the user types.

Split the search string on whitespace. Empty terms are ignored.

All search terms are combined with **AND** semantics: every term must match the snippet somewhere.

For each individual term, it counts as a match if **any** of these are true:

* it is a case-insensitive substring of `title`
* it is a case-insensitive substring of `name`
* it exactly matches one tag, case-insensitively

Thus:

```text
python json
```

means that the snippet must match `python` somewhere in title/name/tags **and** must match `json` somewhere in title/name/tags.

An empty search displays all snippets.

Tags should be represented internally as individual strings rather than searched as one giant text field.

### Main-window actions

Clicking **[new]** opens an editor window containing a new blank snippet.

Clicking **[edit]** beside a result opens that snippet in the editor.

Double-clicking anywhere on a snippet result copies that snippet's `text` field to the system clipboard.

After copying, update the status bar with something like:

```text
Copied: My Snippet Title
```

No additional dialog should appear.

## Editor Window

The editor window looks approximately like:

```text
title: [.........................................................]
name:  [....................]
tags:  [.........................................................]
hook:  [.........................................................]

text:
[................................................................]
[................................................................]
[................................................................]
[................................................................]
                                                       [save]
```

The `title` entry should use a noticeably larger font than the other metadata fields.

`text` is a multiline tkinter Text widget with a vertical scrollbar and should expand when the editor window is resized.

The fields are:

```text
title
name
tags
hook
text
```

For editing purposes, `tags` should appear as a single whitespace-separated line. On save, split it on whitespace into individual tags.

### Save behavior

Pressing **[save]** saves the entry.

For a new snippet, create a new snippet record.

For an existing snippet, update that record.

After saving:

* persist the data
* refresh the main-window search results immediately
* keep the current search query intact
* close the editor window
* put a short confirmation in the main-window status bar

There is no need for autosave.

## Data

Use a small local JSON file. This application does not need a database.

Each snippet record should have at least:

```json
{
    "id": "<uuid>",
    "title": "...",
    "name": "...",
    "tags": ["...", "..."],
    "hook": "...",
    "text": "..."
}
```

Give every snippet a UUID when it is created. The UUID remains stable when the snippet is edited.

Choose a conventional per-user application-data location for the JSON file rather than storing it in the current working directory. Create the directory/file automatically on first use.

The JSON file can contain a simple array of snippet records.

Write changes safely: write the complete new JSON to a temporary file and then replace the old file rather than modifying the file incrementally.

## Interaction details

The program should behave like a lightweight utility rather than a document editor.

* Starting `snippets` should immediately show the main window.
* Search should be live; no Search button.
* Double-click means **copy**, not edit.
* `[edit]` means edit.
* `[new]` means create.
* `[save]` means persist the editor contents.
* Multiple editor windows do not need to be supported. If an editor is already open, reuse/focus it rather than opening another.
* Closing an editor without saving simply discards the unsaved changes.
* No delete feature is required for this spike.
* No tag-management UI is required.
* No settings window is required.
* No menus are required.
* No cloud synchronization is required.
* No rich text is required.
* No syntax highlighting is required.

## Packaging

Create an installable Python package named:

```text
m1-snippets
```

and expose this console command:

```text
snippets
```

so that after installation the user can launch the application simply by typing:

```text
snippets
```

Use the existing repository/package conventions if they exist. Otherwise use a straightforward modern `pyproject.toml` package layout.

## Implementation character

Keep this application deliberately small.

Prefer:

* ordinary dictionaries for snippet records
* ordinary functions for operations
* module-level application state where appropriate
* explicit tkinter callbacks
* obvious control flow
* a small number of source files

Avoid turning `Snippet`, `SnippetEditor`, `SnippetManager`, `SearchController`, etc. into application classes. tkinter's own classes are of course fine; our application code does not need to construct an object model around them.

This is a utility with five data fields, search, edit, save, and clipboard copy. **Build that utility, not a framework for hypothetical future snippet-management requirements.**
