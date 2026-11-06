scratch write test

written 2026-11-06T17:10Z to prove whether a bridge PUT can land at all right now.

If this file is absent from the branch, every PUT is dying in flight and the bridge body is the only thing worth fixing. If it is present, the pipe works and the earlier loss was five concurrent writes torn down together.
