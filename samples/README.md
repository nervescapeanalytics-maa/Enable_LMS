# Sample data for ZIP question importer

Contents:

- `physics_sample.zip`         ← drop this directly into Admin → Test sections → + Import ZIP
- `physics_sample/`            ← unzipped working copy you can edit then re-zip
- `physics_sample/README.md`   ← full column reference + step-by-step

Regenerate / re-edit:

    docker exec -w /tmp/samplebuild docker-api-1 python apps/scripts/build_physics_sample_zip.py

The builder is in `apps/scripts/build_physics_sample_zip.py` and is verified to import end-to-end through `assessments.importers.validate_rows()` with **0 errors / 5 cleaned rows**.
