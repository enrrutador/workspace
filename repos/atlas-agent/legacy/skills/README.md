# Legacy skills (not loaded)

These files are experiments from earlier Atlas versions. They are **not** part
of the build (`tsconfig.json` only includes `src/`) and nothing in `src/`
imports them, so editing them has no effect on the running agent.

They are kept for reference because some contain useful ideas (browser
automation, workflow engine, dev containers, desktop control). To activate one:

1. Move the implementation into `src/arms/tools/` or register it with
   `brainSkills` in `src/main.ts`.
2. Add it to the trust policy in `src/shield/trust_ladder.ts`.
3. Add tests under `tests/`.

Some files referenced by older docs (`remote_ssh.ts`, `remote_wsl.ts`) are not
tracked in this repository.
