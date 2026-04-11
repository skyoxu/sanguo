# Local Hard Checks Repair Guide

- status: `fail`
- failed_step: `run-dotnet`

## Next Actions

- Open summary.json and inspect the first failing step.
- Open the failing step log and then inspect the referenced artifact directory.
- Re-run the command after fixing the first failing step.

## Re-run

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin C:/Godot/Godot_v4.5.1-stable_mono_win64_console.exe --run-id local-hard-checks-20260411T110000
```
