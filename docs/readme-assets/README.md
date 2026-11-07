# README animation

The event-routing SVG is authored with [animdiagram](https://github.com/praveenvijayan/animdiagram) (skill version 1.1), using its MIT-licensed template, timeline compiler, and validator. The license is retained in [animdiagram-LICENSE.txt](animdiagram-LICENSE.txt). SOH's diagram and timing specification describe its planned routing model.

The tool is an authoring dependency only. Readers and SOH runtime users need no installation. The SVG uses CSS keyframes, contains no JavaScript or external resources, and has a reduced-motion fallback.

To edit, obtain animdiagram separately, edit event-routing.spec.json and the static portions of event-routing.svg, then run:

```sh
python /path/to/animdiagram/scripts/timeline.py docs/readme-assets/event-routing.spec.json --inject docs/readme-assets/event-routing.svg
python /path/to/animdiagram/scripts/check.py docs/readme-assets/event-routing.svg
```

The 12-second loop contains seven packets: Event 1 reaches the dispatcher at 0.9s and A at 1.8s; Event 2 reaches the dispatcher at 4.4s and B at 5.3s; Event 3 reaches the dispatcher at 7.9s and A/B simultaneously at 8.8s. The final caption ends at 9.9s, leaving a quiet reset. Timing is illustrative, not measured performance. The single accent represents an active event. Inactive routes stay gray.

The static building-block overview and current POC diagram remain separate. This animation omits response aggregation and failures, and does not claim concurrent routing is implemented.

Validation: animdiagram check.py passed with no warnings. Chromium verified A-only, B-only, simultaneous A+B, idle reset, reduced-motion behavior, and changing frames when embedded in an img. Larger node labels are intentional for README readability.
