```
date: 2026-08-26
chatgpt: https://chatgpt.com/c/6a8fb1b6-02f8-83e8-bba4-b31b51304838
title: Initial Spec for m1snippets (addendum)
```

## Persistence Addendum

Replace the earlier JSON-file persistence design with the following.

### M1 data

Snippet data is stored as **M1 data**.

Do not invent or infer the M1 serialization format. The M1 data model / formatting conventions will be supplied separately.

Each snippet still conceptually contains:

```text
id
title
name
tags
hook
text
```

and each snippet should retain a stable identity across edits, according to the supplied M1 conventions.

The Snippets application should treat the M1 layer as the authoritative persistence representation.

### lionscliapp

Use **lionscliapp** as the application/CLI framework.

The command remains:

```text
snippets
```

Use the project/application directory supplied by lionscliapp for all persistent Snippets data.

Do not independently choose an OS-specific application-data directory, and do not build a separate configuration-directory mechanism. The project folder provided by lionscliapp is the application's storage home.

Use the existing lionscliapp conventions for application startup, project-folder discovery/creation, and CLI registration rather than recreating that machinery inside Snippets.

Everything else in the original Snippets UI and interaction specification remains unchanged.
