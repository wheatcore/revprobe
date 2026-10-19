# Contributing

Thanks for helping improve RevProbe. Open an issue describing the document change or assistant behavior before a larger change. For a bug, include a small sanitized old/new document pair, the generated probe, the response, and the expected verdict. Never include API keys or private documents.

Run `python -m unittest discover -s tests -v` before a pull request. Keep the core dependency-free, add a test for behavior changes, and document any change to the JSON schemas or exit codes. New verdict logic should preserve `inconclusive` when evidence is insufficient.
