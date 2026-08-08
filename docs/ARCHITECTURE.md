# Architecture

```
Original pixels + EditorState + masks/watermarks
                    │
             local renderer
              ├─ preview worker
              └─ full-resolution export worker

Prompt + preview + EditorState
                    │
             Provider Registry
                    │
          strict EditingPlan / Adapter
                    │
           executor → one history transaction
```

`EditorState` is the only editing state. Preview rendering never edits the source pixels. The UI works only with that state and delegates CPU-heavy rendering, export, AI calls, and JarvisArt startup/inference to workers.

JarvisArt has an additional native boundary: its localhost Lightroom-style output becomes `JarvisArtNativePlan`, then `JarvisArtAdapter`, then the common `EditingPlan`.
