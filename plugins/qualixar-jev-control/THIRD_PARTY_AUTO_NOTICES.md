# Upstream use and provenance

The upgrade does not change the existing workbench's licence or redistribute model weights.

| Upstream | Pin | Use in this package | Licence |
|---|---|---|---|
| wy-coliney/jev-browser-use | f14b60e0ae1ee90cd73eb6650e30a666a84c021a | Adapted existing-tab accessibility parsing/action selection and bounded browser loop. Direct provider credentials replaced with private local IPC. Compact return format added. | MIT; original notice retained in licenses/jev-browser-use-MIT.txt and installed plugin |
| GhalebDweikat/winnow | 51d80b945c74c8384bc47fa817179f668289afd8 | Verbatim chunk.py under jev_auto/vendor; keep/omit policy adapted into sieve.py. No Claude-specific hooks or summarizer installed. | MIT; original notice retained in licences and vendored runtime docstring |
| mizorewww/laya-mlx | 0a859518634112655cb97c745dbf04f5191aaf13 | Optional separate installation; formatter-informed preflight rejects truncation. No MLX model implementation or weights bundled. | Apache-2.0; dependency and model notices remain with their downloads |

Original authors retain their copyrights. Qualixar adaptations are independently maintained.
The Laya-MLX port is not an official Convai Innovations or TypeSafe release.
The two MIT licences were read from their repositories. Dependency and model licences must remain present when distributing a separately built application.
