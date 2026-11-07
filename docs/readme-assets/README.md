# README animation

The event-routing and method-context SVGs are authored with [animdiagram](https://github.com/praveenvijayan/animdiagram) (skill version 1.1), using its MIT-licensed template, timeline compiler, and validator. The license is retained in [animdiagram-LICENSE.txt](animdiagram-LICENSE.txt). Event routing describes the planned model; method context describes the existing proof of concept.

The tool is an authoring dependency only. Readers and SOH runtime users need no installation. The SVG uses CSS keyframes, contains no JavaScript or external resources, and has a reduced-motion fallback.

To edit, obtain animdiagram separately, edit event-routing.spec.json and the static portions of event-routing.svg, then run:

```sh
python /path/to/animdiagram/scripts/timeline.py docs/readme-assets/event-routing.spec.json --inject docs/readme-assets/event-routing.svg
python /path/to/animdiagram/scripts/check.py docs/readme-assets/event-routing.svg
```

The 12-second loop contains seven packets: Event 1 reaches the dispatcher at 0.9s and A at 1.8s; Event 2 reaches the dispatcher at 4.4s and B at 5.3s; Event 3 reaches the dispatcher at 7.9s and A/B simultaneously at 8.8s. The final caption ends at 9.9s, leaving a quiet reset. Timing is illustrative, not measured performance. The single accent represents an active event. Inactive routes stay gray.

The building-block overview remains static. This animation omits response aggregation and failures, and does not claim concurrent routing is implemented.

Validation: animdiagram check.py passed with no warnings. Chromium verified A-only, B-only, simultaneous A+B, idle reset, reduced-motion behavior, and changing frames when embedded in an img. Larger node labels are intentional for README readability.

## Method-context walkthrough

`method-context.svg` and `method-context.spec.json` use the same compiler commands above with the filename replaced. Five scenes demonstrate explain, generate tests, modify/undecided, unclear-method, and missing-file outcomes. Green denotes added context; amber denotes no added context. The SVG includes the flow boundary and labels Laya questions separately from tools.

The full walkthrough deliberately exceeds animdiagram's small-explainer budget: 29 seconds and 26 sequential packets across five examples. Its validator reports these two budget warnings and no errors. This preserves the requested branches in one view instead of hiding steps or speeding the examples up. There is a 3.6-second idle period at the end. Timing is illustrative, not a performance claim.

Chromium checked all five scene outcomes, reduced motion, changing frames as an embedded image, and a mobile viewport. The source contract was checked against `src/flows/first_method_context.py`. Source verification, output budgets and session checks share one box; their detailed behavior is documented in `docs/flows/method-context.md`.
