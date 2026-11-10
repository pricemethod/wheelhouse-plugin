## How we check software work

Run the checks in layers, cheapest first. A story is done only when the layers it names pass **and** you have used the result yourself the way a real person would.

1. **Logic checks:** small automatic tests of the rules and calculations.
2. **Output checks:** tests of what the screen or file actually says (labels, numbers, messages).
3. **Rule-enforcing checks:** tests that read the project itself and fail if a house rule is broken (for example, a hand-made one-off where a shared piece must be used).
4. **Break it on purpose:** after adding a new check, deliberately break the thing it protects and confirm the check fails, then put it back. A check that cannot fail proves nothing.
5. **Pinned real sample:** where numbers matter, save a small real example and test against it.
6. **Compare with an independent source:** read the same facts another way and compare, rather than only checking that the project agrees with itself.
7. **Try it for real:** run it, click through it at phone width and desktop width, and use a real phone or a real reader before calling it finished.
8. **Before the log entry:** run the whole set, note anything odd even if it did not block, and write down what you actually did.
