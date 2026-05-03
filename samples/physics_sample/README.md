# physics_sample.zip — README

This is a known-good starter pack for the **Enable-LMS ZIP question importer**.

## Files inside the ZIP
    questions.xlsx          # 5 sample physics questions
    images/q02_trajectory.png
    images/q04_circuit.png

## Column reference
| Column | Required | Notes |
|---|---|---|
| question_code | Recommended | Unique within the test, e.g. PHY-001. Auto-generated as Q001… if blank. |
| question_text | YES | The question itself. |
| question_type | Recommended | One of: MCQ_SINGLE, MCQ_MULTI, NUMERICAL, TRUE_FALSE, FILL_BLANK, SUBJECTIVE. Defaults to MCQ_SINGLE. Aliases: MCQ→MCQ_SINGLE, TF→TRUE_FALSE, NUM→NUMERICAL, FILL→FILL_BLANK. |
| option_a..option_e | YES for MCQ types | One choice per cell. Leave blank for non-MCQ. |
| correct_answer | YES | Letter for single (B), comma list for multi (B,D), or literal value for numerical/fill. |
| positive_marks | YES | Numeric (e.g. 4). |
| negative_marks | Optional | Numeric. Defaults to 0. |
| difficulty | Optional | EASY / MEDIUM / HARD. |
| question_image | Optional | Filename inside images/ (case-insensitive). |
| option_a_image..option_e_image | Optional | Filenames inside images/ for picture-option choices. |
| answer_explanation | Optional | Shown to student after submission. |
| tags | Optional | Comma list — useful for filtering. |
| question_order | Optional | Number — printing order. |

## Question-type cheat sheet
- **MCQ_SINGLE**: one correct option; correct_answer = single letter (A/B/C/D/E).
- **MCQ_MULTI**: 2+ correct options; correct_answer = comma list (A,C).
- **TRUE_FALSE**: model as MCQ_SINGLE with option_a=True, option_b=False, option_c/d filled with placeholder text (e.g. "N/A"). The current validator requires all four option cells to be non-empty.
- **NUMERICAL / FILL_BLANK / SUBJECTIVE**: the current validator still requires all four option columns to be non-empty — fill them with placeholder text (e.g. "—") and put the actual expected answer in `correct_answer`.

## Step-by-step
1. Edit `questions.xlsx` — keep the header row exactly as it is.
2. Add/replace pictures under `images/`. Match the filenames you put in `question_image` / `option_*_image` (case-insensitive).
3. Re-zip the **contents** (not the parent folder). The ZIP root must be:
       questions.xlsx
       images/...
4. Admin → **Test sections** → **+ Import ZIP** → pick the target test → upload.
5. Watch **ZIP Import History** at the bottom for ✓ Success or ⚠ Rejected with a one-line reason.

## Common pitfalls
- Both a packed `option` column **and** `option_a` column at the same time → keep only one of those styles.
- Image filenames don't match the spreadsheet cells (case is ignored, but extension matters).
- ZIP includes a top-level folder, e.g. `physics_sample/questions.xlsx`. Re-zip *the files*, not the parent folder.
- correct_answer for MCQ_SINGLE is multi-letter (B,C). Use MCQ_MULTI for that.

## Re-uploads
The importer matches existing rows by `question_code` within the same test. Re-uploading the file with edited content updates those questions in place — it does not create duplicates. Rows with new codes are inserted.
