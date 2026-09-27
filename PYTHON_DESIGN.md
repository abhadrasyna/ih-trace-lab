# Python Design Reference

> Loaded on trigger only: designing or reviewing a new domain/orchestration class in a Python project scaffolded from here. Not resident in `AGENTS.md` — this doc exists precisely because it is not
> needed every session, only when a class is actually being shaped.

## Governing frame: Zen of Python (PEP 20)

Never violate it. In particular for the rules below: "Explicit is better than implicit," "Simple is better than complex," and "Flat is better than nested" are not style preferences here — a
deeply nested `if`/`elif` chain inside a decision method is a Zen violation *and* the concrete OCP violation described below. If a change makes a function harder to read top-to-bottom, or adds
another branch to logic that already branches, stop before writing it.

Full text: `python -c "import this"` or https://peps.python.org/pep-0020/

## SOLID — as checkable triggers, not an essay

Each principle below is a trigger: a concrete thing you're about to do, and what to do instead. Stated this way because a generic "follow SOLID" reminder does not change behavior at the point of
the edit — a named trigger does.

- **SRP — trigger:** you're adding a method to a class whose existing methods already cover a different concern (entry logic next to persistence next to notification). **Do instead:** new class for
  the new concern; the original class keeps only its original responsibility.
- **OCP — trigger:** you're adding a new `elif`/`case` branch to an existing decision method to handle a new variant (a new roll condition, a new entry signal). **Do instead:** extract the decision
  into a `Protocol`, make the existing branches separate implementers, add the new variant as a new implementer. Nothing existing is edited.
- **LSP — trigger:** a subclass overrides a method and narrows what inputs it accepts, or returns something the base type's callers don't expect. **Do instead:** if the subclass can't honor the
  base `Protocol`'s contract, it isn't a substitutable implementer of that `Protocol` — split the interface instead of special-casing the subtype at call sites.
- **ISP — trigger:** a `Protocol`/interface has grown methods that only some implementers use, so others implement stubs or raise `NotImplementedError`. **Do instead:** split into smaller
  `Protocol`s; a class implements only the ones it actually needs.
- **DIP — trigger:** a class constructs its own collaborator directly (`self.store = SqliteStore()`) instead of receiving it. **Do instead:** inject the collaborator via `__init__`, typed as a
  `Protocol`, not a concrete class — this is what makes the class testable without a real DB/broker/network call.

## Concrete example: the seam that would have prevented a 1000+ LOC strategy file

A strategy/domain-orchestration class holds sequencing only. Each decision it makes is a separate injected collaborator:

```
StrategyOrchestrator          # sequencing only — check entry, size, monitor, check exit/roll
├── EntryRule (Protocol)      # decides when/whether to enter
├── ExitRule (Protocol)       # decides when/whether to exit
├── RollPolicy (Protocol)     # decides roll timing/strike selection
├── PositionSizer             # Greeks-aware sizing, pure function over inputs
└── LegStore (Protocol)       # persistence
```

The orchestrator structurally cannot grow past a few hundred lines — it has nowhere to put strategy-specific logic. A new strategy variant is a new `EntryRule`/`RollPolicy` implementation, not a
fork of an existing file, and not a new branch inside one.

## Named patterns worth knowing by name (not the full catalogue)

- **Strategy** — the seam above. Interchangeable algorithms behind a common `Protocol`, selected at construction/config time. This is what Python's `Protocol`-based DI *is*, once named.
- **Factory Method** — trigger: a constructor is branching on a `strategy_type`/config string to decide which concrete classes to build. Do instead: a factory function/class owns that branching once,
  callers just ask for "the strategy for config X."
- **Template Method** — the `StrategyOrchestrator`'s fixed sequence (entry → size → monitor → exit/roll) is the template; each step delegates to an injected Strategy object rather than containing
  logic itself.
- **Decorator** — trigger: adding a conditional guard (e.g., a max-loss check) by editing an existing class's method. Do instead: wrap the base object in a decorator implementing the same
  `Protocol`, which the base object never knows about — same OCP shape, applied to cross-cutting concerns.
- **Observer** — only reach for this if something already needs to react to state changes (a P&L tracker, a notifier) and a direct call/return value is getting awkward. Don't introduce it
  preemptively — an unused Observer is complexity Zen already tells you to avoid ("Simple is better than complex").

## When these rules don't resolve the situation at hand

Consult, in order of relevance to the concrete problem:

- Clean Code in Python — https://testdriven.io/blog/clean-code-python/
- Design Patterns in Python — https://refactoring.guru/design-patterns/python

These are references for edge cases, not required reading before writing a class — the rules above should resolve the common cases on their own.

## When this doc stops being enough: consider an MCP instead

This file is static reference — read, then applied by judgment. That's the right shape as long as following it stays a matter of the model reading a rule and self-applying it. It stops being
the right shape the moment you want *active, programmatic enforcement* rather than reference — e.g., a `check_design(class_code)` tool that actually parses a class and flags "this method has a
4th branch on decision logic, extract a `Protocol` implementer" or "this constructor builds its own collaborator instead of receiving it" as a structural/AST check, not a judgment call.

That's a materially different thing from this doc — closer to a linter than a style guide — and worth building only once there's evidence the doc-based approach isn't enough: code review keeps
catching the same violation shape (an OCP/DIP trigger from above) after the doc already states it, meaning the guidance isn't being self-applied reliably and needs to become an enforced check
instead of reference prose. Don't build the MCP preemptively — it's real infrastructure (a server process, a tool schema, ongoing maintenance) for a problem you don't have evidence of yet.
