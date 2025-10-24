# Models Directory

**This folder is deprecated and retained only for archival/compatibility.**

All model code, documentation, and wrappers have been moved to the `/part of Backend/` directory. To reduce duplication we keep an index of archived files here and point consumers to the canonical microservice locations.

## Where to Find Model Information
- See `/part of Backend/README.md` for an overview of all model microservices.
- For model usage, environment, and API details, see the README and documentation in each `/part of Backend/[model]/` subfolder.

## Archived files index
- See `ARCHIVED_FILES_LIST.md` for the list of files that were moved and their new locations.

## Next steps
- If you maintain automation or scripts that reference files under `Backend/models/`, please update them to the corresponding `/part of Backend/` path. If you need a compatibility redirect, open an issue so we can add a pointer file or update the script.

## Archive and safe-move
A copy of the removed files from this folder was created at
`docs/archives/Backend_models/` during the recent reorganization. If you
want to remove the original Markdown files from `AI separator backend/models/` we
recommend using the PowerShell move snippet in `REMOVED_README.md`.

If you'd like me to perform the safe-move now and then re-run the
repository link-check to verify all references resolve to the canonical
`/part of Backend/` locations, reply with "MOVE". To leave the originals
in place, reply with "LEAVE".
