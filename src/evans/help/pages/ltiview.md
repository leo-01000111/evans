# ltiview

Compare one or more systems on the axes of an analysis pane, side by side with the loop.

## Syntax

    ltiview
    ltiview(sys)
    ltiview(sys1, sys2, ...)

## Description

`ltiview(sys)` switches to the Analyse workspace and draws `sys` in the first plot pane (a step response, Bode plot, root locus or any other pane that draws curves), next to the system the pane already shows. The pane keeps its kind: to see another response, change what the pane shows, or put another plot pane beside it. If no pane draws curves, the first pane becomes a step response.

`ltiview(sys1, sys2, ...)` draws several systems at once. They are named `sys1`, `sys2` and so on, in the order given, and the legend shows those names. Each call replaces what the first plot pane compares, and the systems it named stay in the **Compare** menu of every plot pane, so you can tick them in another pane too. The same menu lists the loop's other systems (G, L, T, S) and every snapshot.

`ltiview` with no argument compares the current loop in the first plot pane: the plant G, the open loop L and the closed loop T.

The command returns a short description of the request, such as `<ltiview: sys1, sys2>`, which the console displays when the line has no semicolon. In a script run without the app nothing opens; the request is recorded and the line still runs. Evans does not take MATLAB's leading plot-type argument (`ltiview('step', G)`): choose the response with the pane's own menu instead.

## Example

```matlab
G = tf(1, [1 3 3 1]);
C = pidtune(G, 'pi');
T = feedback(C*G, 1);
ltiview(G, T)
```

## See also

[step](step) · [bode](bode) · [sisotool](sisotool) · [pidtuner](pidtuner)
