# User guide

## Editing workflow

Open a JPG or PNG using **File → Open**, `Ctrl+O`, or drag a file into the application. The central canvas uses a reduced preview for responsive editing. Export always renders from the original pixels and current non-destructive `EditorState`.

Use the right panel for Basic, HSL, curves, colour grading, histogram, and AI. Sliders update the preview while dragging, ignore the mouse wheel, accept an exact numeric value, and reset to their default on double-click. A drag produces one history entry when released.

## Masks and watermarks

Use the **Masks** tab to add gradients, ranges, sky/subject/semantic masks, or a brush. Show Mask displays a red overlay. Each layer can be disabled, inverted, feathered, adjusted, renamed, or removed. The **Watermark** tab stores user assets in the local user configuration directory and adds them as non-destructive layers.

## Recovery

After each history refresh, the current edit state and bounded history are saved in the application settings, keyed by source file identity. When the same photo is opened later, choose **Restore** to continue or decline to start from the original. The photo itself is never overwritten.

## AI

Configure a provider in **File → Settings**. Use `Ctrl+Enter` to send; `Enter` makes a new line. AI applies one validated plan as one undoable transaction. Failures do not alter the photo. Cloud retry is always manual.
