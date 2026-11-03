# V12.1 QA, development environment (not production verification)

- Node `--test TEST_V121_ARCADE.mjs`: **31/31 passed**, including 32 unique catalog entries, 12+12+8 routing, math/puzzle rule checks, safe 24 solver, date calculations, local planning logic, and Unicode/CSV escaping.
- Python `TEST_INSTALL_V121_ARCADE`: **7/7 passed** using temporary fixture directories (check-only, apply, repeat apply, CRLF preservation, unexpected file refusal, unexpected Python and HTML refusal).
- Python `TEST_V121_ARCADE`: **10/10 passed** using a minimal stub for Flask and V12.0 in this isolated container; must be rerun against the real bot Flask stack.
- Browser: Chromium was run at 390×844 using an inline bundle of the actual six JavaScript modules because sandbox navigation to HTTP/file URLs was restricted. All **32/32 activities mounted**, with **zero JavaScript page errors**. Additional clicks tested quiz completion, flashcard reveal, answer checking, question bank, daily schedule, scorecard PNG canvas, math estimator, Sudoku grid, 2048 moves, word-search board, reaction start, and Tamil switch. The result is a useful UI smoke test, **not a full real-network or Telegram in-app-browser test**.
- OpenAI cannot verify the user's existing project files or full regression tests from the isolated environment. Run the provided commands on Windows and do not push/deploy on any test failure.
- **No GitHub push, Render deployment or real Telegram phone download has been performed by this package.**
