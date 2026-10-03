# Design principles

> Code-level discipline applied while re-implementing legacy logic. This is the restated, project-agnostic form of a "Python design reference" doc used during a real refactor — keep it as a
> trigger-based reference loaded on demand, not a resident essay re-read every session.

## Governing frame: simplicity first

Whatever language-level style guide your ecosystem has (PEP 20 for Python, idiomatic-X for others), treat its core tenets as non-negotiable, not style preferences: explicit over implicit, simple over
complex, flat over nested. A deeply nested conditional chain inside a decision method is both a readability violation *and*, almost always, the concrete Open/Closed violation described below. If a
change makes a function harder to read top-to-bottom, or adds another branch to logic that already branches, stop before writing it — that feeling is the signal, not a thing to push through.

## SOLID — as checkable triggers, not an essay

A generic "follow SOLID" reminder does not change behavior at the point of an edit. A named trigger — a concrete thing you're about to do, and what to do instead — does. Use this table while writing
or reviewing a class, not as background reading:

- **SRP — trigger:** you're adding a method to a class whose existing methods already cover a different concern (entry logic next to persistence next to notification). **Do instead:** a new class for
  the new concern; the original class keeps only its own job.
- **OCP — trigger:** you're adding a new `elif`/`case`/`switch` branch to an existing decision method to handle a new variant. **Do instead:** extract the decision into an interface, make the existing
  branches separate implementers, add the new variant as a new implementer — nothing existing is edited.
- **LSP — trigger:** a subclass overrides a method that narrows accepted inputs or returns something the base type's callers don't expect. **Do instead:** if the subclass can't honor the base
  contract, it isn't substitutable — split the interface instead of special-casing the subtype at call sites.
- **ISP — trigger:** an interface has grown methods that only some implementers use, so others implement stubs or raise "not implemented." **Do instead:** split into smaller interfaces; a class
  implements only the ones it actually needs.
- **DIP — trigger:** a class constructs its own collaborator directly (e.g. `self.store = ConcreteStore()`) instead of receiving it. **Do instead:** inject the collaborator via the constructor, typed
  as an interface, not a concrete class — this is what makes the class testable without a real DB/network/external call.

### Why DIP is usually the first one to land

In a legacy-duplication refactor, the single highest-leverage design decision is almost always constructor injection of external-system collaborators (database clients, HTTP clients, cloud SDK
clients). Every duplicated "do the same external call three different ways in three different projects" problem traces back to each original constructing its own client internally. Fixing DIP first is
what makes every other principle's fix (testability in particular) possible without real network/DB access in tests.

## Concrete example: the seam that prevents an unbounded strategy file

A domain-orchestration class should hold sequencing only. Each decision it makes is a separate injected collaborator:

```
Orchestrator                  # sequencing only — e.g. check entry condition, size, monitor, check exit condition
├── EntryRule (interface)     # decides when/whether to start
├── ExitRule (interface)      # decides when/whether to stop
├── ReschedulePolicy (iface)  # decides retry/rollover timing and parameters
├── Sizer                     # pure function over inputs, no I/O
└── Store (interface)         # persistence
```

The orchestrator structurally cannot grow past a few hundred lines — it has nowhere to put variant-specific logic. A new variant is a new `EntryRule`/`ReschedulePolicy` implementation, not a fork of
an existing file, and not a new branch inside one.

## Named patterns worth knowing by name (not the full catalogue)

- **Strategy** — the seam above. Interchangeable algorithms behind a common interface, selected at construction/config time. This is what interface-based dependency injection *is*, once named.
- **Factory Method** — trigger: a constructor branches on a `type`/config string to decide which concrete class to build. Do instead: a factory function/class owns that branching once; callers just
  ask for "the implementation for config X."
- **Template Method** — a fixed sequence (e.g. entry → size → monitor → exit) is the template; each step delegates to an injected Strategy object rather than containing logic itself.
- **Decorator** — trigger: adding a conditional guard (e.g. a validation or rate-limit check) by editing an existing class's method. Do instead: wrap the base object in a decorator implementing the
  same interface, which the base object never knows about — same OCP shape, applied to cross-cutting concerns.
- **Observer** — only reach for this once something already needs to react to state changes (a tracker, a notifier) and a direct call/return value is getting awkward. Don't introduce it preemptively —
  an unused Observer is complexity the simplicity-first rule already tells you to avoid.

## When these rules don't resolve the situation at hand

Have a short, named escalation path (a couple of reference links or a senior reviewer) for edge cases — don't let "SOLID didn't obviously apply" become license to skip design thought. These rules
should resolve the common cases on their own; reserve escalation for genuine edge cases.

## When a static doc stops being enough: consider active enforcement instead

A written reference like this one is read, then applied by judgment. That is the right shape as long as following it stays a matter of a person (or an AI assistant) reading a rule and self-applying
it. It stops being the right shape the moment you want *active, programmatic enforcement* rather than reference — e.g., a lint rule or review-bot check that actually parses a class and flags "this
method has a 4th branch on decision logic, extract an interface implementer" or "this constructor builds its own collaborator instead of receiving it" as a structural/AST check, not a judgment call.

That is a materially different investment than a reference doc — closer to a linter/static-analysis rule than a style guide — and it's worth building only once there is *evidence* the doc-based
approach isn't enough: review keeps catching the same violation shape after the doc already states it, meaning the guidance isn't being self-applied reliably and needs to become an enforced check.
Don't build that enforcement preemptively; it's real infrastructure (a rule engine, a CI gate, ongoing maintenance) for a problem you don't have evidence of yet.
