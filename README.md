# m1snippets

A compact desktop snippet manager. Snippets are stored as M1 Lattice
transport data in the lionscliapp project directory.

Install the package, then run:

```text
snippets
```

The application creates and maintains `snippets.m1` in its `.snippets`
application folder. Each snippet is an M1 entity with the basic aspect:
`typehint: "text"`, metadata in the ordinary basic fields, and the snippet
body in `notes`.
