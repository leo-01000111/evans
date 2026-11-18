# sisotool

Design a compensator on the root locus: drag a closed-loop pole along it, and the analysis panes follow.

## Syntax

    sisotool
    sisotool(G)
    sisotool(G, C)

## Description

`sisotool(G)` loads `G` as the plant of the loop, switches to the Analyse workspace and opens its side panel on the **Design** tab, showing **Compensator**. The tab shows the root locus of the compensated loop, with the compensator's zeros and poles below it; **Gain**, the next view along, has the gain slider and buttons that set the gain for a damping ratio or an overshoot. Dragging the closed-loop pole marker along the locus sets the gain.

Every change applies at once: the compensator is written into the loop's controller block K2, so the panes beside the panel (step response, Bode, metrics and the rest) are the display, and a whole drag is one step of Edit ▸ Undo. **Reset** puts back the controller the loop had when the tab was opened. The sensor block H comes from the loop, and when the loop changes elsewhere (an undo, a preset, the Loop tab) the tab follows it.

`sisotool` with no argument opens the tab on the plant G already in the loop.

`sisotool(G, C)` also loads `C` as the controller K2, in the same undo step, so the tab starts from it: its gain, zeros and poles fill the fields. The designer tunes a gain `K` of 0 or more, so a compensator with a negative gain is refused with an error; move the sign into the plant, `sisotool(-G, -C)`.

The command returns a short description of the request, such as `<sisotool: plant>`. In a script run without the app nothing opens and the loop is not changed; the request is recorded and the line still runs.

## Example

```matlab
G = zpk([], [0 -2 -5], 10);
rlocus(G)
sisotool(G)
```

## See also

[rlocus](rlocus) · [margin](margin) · [pidtuner](pidtuner) · [ltiview](ltiview) · [lead](lead)
