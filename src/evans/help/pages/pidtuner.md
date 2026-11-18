# pidtuner

Tune a PID controller for the loop, with one slider for response time, one for transient behaviour, and a readout of what each asks for.

## Syntax

    pidtuner
    pidtuner(G)
    pidtuner(G, type)

## Description

`pidtuner(G)` loads `G` as the plant of the loop, switches to the Analyse workspace and opens its side panel on the **Design** tab, showing **PID**. `pidtuner(G, type)` also chooses the controller type: `'P'`, `'PI'`, `'PD'` or `'PID'`, in either case. Without a type the tab keeps the type already chosen in it (PI the first time).

The sliders set the targets [pidtune](pidtune) takes as numbers. The response-time slider sets the target crossover frequency and the transient slider sets the target phase margin, from an aggressive, lightly damped loop to a cautious, well-damped one. The tab prints which crossover and margin were asked for and which were achieved, and when a target cannot be met it says why and leaves the controller alone.

Every change applies at once: the tuned controller is written into the loop's controller block K2, so the panes beside the panel (step response, Bode, metrics and the rest) show it, and a whole slider drag is one step of Edit ▸ Undo. **Reset** puts back the controller the loop had when the tab was opened. The tuning uses the loop's sensor H and feedforward K1, and when the loop changes elsewhere (an undo, a preset, the Loop tab) the tab follows it.

`pidtuner` with no argument opens the tab on the plant G already in the loop.

The command returns a short description of the request, such as `<pidtuner: plant>`. In a script run without the app nothing opens and the loop is not changed; the request is recorded and the line still runs. Evans does not check `type` at the console, so a misspelt type only shows up as an error when the tab opens.

## Example

```matlab
G = tf(1, [1 3 3 1]);
pidtuner(G, 'pid')
```

## See also

[pidtune](pidtune) · [pid](pid) · [sisotool](sisotool) · [ltiview](ltiview)
