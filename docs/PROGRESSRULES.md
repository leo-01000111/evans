# Progress rules

How to pick the next piece of work from `docs/ROADMAP.md`. Read this before choosing
what to do when Leon asks "what's next?", "squash some bugs" or anything similarly
open. Agreed with Leon on 2026-11-27.

The idea, in one line: **fix what is known, by severity; do not hunt for bugs without
end; the hunting has fixed places (the corpus checker, R9).** No phase waits for the
code to be bug-free, because that never happens.

## 1. Before choosing anything

1. Read the roadmap's "At a glance" table, then only the sections the choice needs.
   It is a long file: grep for headings and `- [ ]` and do not read it whole.
2. Read `## Questions for Leon` at the end. An item that depends on an open question
   is not picked until Leon answers it.
3. Respect every *Decided* note and every hold (e.g. "after the 2026-11-26 hold",
   "until Leon says it is a bug fix"). A decision is not reopened in a coding session.
   Check the memory for holds and freezes that are still in force.

## 2. The order

Take the first tier that has an open item that can be done now. Within a tier, prefer
the smaller item (**S** before **M** before **L**) and items in an area already loaded
in this session.

1. **Silent wrong answers.** Anything that returns a wrong result without an error:
   Phase 0, and any `[ ]` elsewhere described as a wrong result, a dropped option or
   a lost type. These jump the queue whenever they are found, including in front of
   a feature in progress (finish or park the feature's current step first).
2. **Crashes and raw Python errors.** A traceback, a numpy or scipy message, or a
   Python exception name where MATLAB would give its own error (the "Crashes and raw
   Python errors" lists, Phase 4). The user sees that something failed, so these come
   second.
3. **What blocks 1.0, in the order the roadmap gives:** the corpus checker (Phase 6),
   then Phase 8's R7 → R8 → R9, then the tag. Phase 8's two "left over" items go
   with R9.
4. **Bugs in the area a tier-3 package touches.** Known `[ ]` bugs in the files that
   package will edit are batched into it, since the context is already loaded.
5. **Everything else before 1.0,** by the "Next" column of the glance table.
6. **After 1.0** (Phase 8.4 and the rest): one feature per batch, plus the known bugs
   in the area it touches. Phase 5 and anything large in Phase 7 need Leon's scope
   decision first.

Never start an item marked as a new feature while a hold covers it, even if its tier
comes up.

## 3. Sweeps

- No open-ended bug sweep. The planned ones are the corpus checker (Phase 6) and R9's
  sweep, and they run where the order puts them.
- A bug found in passing (while writing a help page, fixing something else, reading
  code) is written into the roadmap at once under the right phase, with its repro, the
  expected result and the cause if known, as the help-page lists are. It is then
  ranked by section 2, not fixed on the spot unless it is tier 1 or a few lines in a
  file already open.
- A known bug that is not worth fixing is closed on purpose: move it to
  `docs/HISTORY.md` with the reason ("won't fix, because…"). Nothing stays open
  undecided.

## 4. How a bug fix is done

1. A failing test first that reproduces the roadmap's example (silent wrong answers
   go next to `tests/golden/test_confident_liars.py`).
2. The fix, compared against MATLAB's documented behaviour.
3. The help page that describes today's behaviour is revised in the same change
   (`src/evans/help/pages/*.md`; the roadmap item says which page).
4. The item leaves the roadmap for `docs/HISTORY.md`, and the phase's open count and
   the "At a glance" table are updated.

## 5. Batching and size

- Follow `CLAUDE.md`'s "Working with an LLM in this repo": at most about two sessions
  at once, small related fixes batched, the full suite once per batch in the
  background before committing.
- A tier-1 or tier-2 list (a whole "found while writing help pages" batch) is one
  batch. An **L** item or any R package gets its own session.
- After a batch, stop and ask Leon before starting the next big item. Offer the next
  item by this order; Leon may pick something else, and that is his call.
