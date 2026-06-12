## On the techstack

When planning an implementation or when working on specifications, assume the following set of technologies, unless instructed otherwise:

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- go 1.26+
- rust & cargo

IMPORTANT: Do not use Javascript or Typescript if it can be avoided !

## On interface and type definitions in documentation

When defining interfaces, records, or data types in documentation and
specifications, use **language-neutral pseudocode**, not JavaScript/TypeScript
syntax. The conventions are:

- `interface Foo:` for behavioral contracts (methods).
- `record Foo:` for data structures (fields only).
- `→` for return types (not `: ReturnType`).
- `list[T]` instead of `T[]`.
- `map[K, V]` instead of `Record<K, V>`.
- `stream[T]` for async/iterable streams.
- `T or null` instead of `T | null`.
- `optional` suffix instead of `?` sigils.
- `--` for inline comments.
- Indentation-based nesting, no curly braces.
