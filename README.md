# Mutual Fund Facts-Only RAG (Milestone 1)

This implementation includes:
- URL source configuration for the ICICI Prudential fund set
- A scraping pipeline that fetches, cleans, and chunks content
- A fact extraction pipeline for key FAQ fields
- Processed output artifacts for downstream RAG ingestion
- A GitHub Actions scheduler configured for daily runs at 9:15 AM IST

## Project Structure

- `LIP2urls.csv`: configured source URLs (section-based input file)
- `app/scrape_sources.py`: scraper + text extraction + chunk creation
- `app/extract_key_facts.py`: extracts key facts from chunks
- `app/build_faq_dataset.py`: builds chatbot-ready JSON for 5 ICICI Prudential direct-growth funds
- `data/raw/<run_id>/`: raw HTML and cleaned text snapshots
- `data/processed/sources_snapshot.jsonl`: source-level scrape status and metadata
- `data/processed/chunks.jsonl`: chunked text for retrieval/indexing
- `data/processed/key_facts.json`: structured extracted facts by scheme
- `data/processed/key_facts.md`: human-readable extracted facts summary
- `data/processed/scrape_run.json`: run summary
- `.github/workflows/scrape-sources.yml`: daily scheduler workflow

## Local Setup

1. Create and activate Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run scraper:
   - `python app/scrape_sources.py --only-active`
   - Optional: `python app/scrape_sources.py --source-file LIP2urls.csv --only-active`
4. Extract key fields:
   - `python app/extract_key_facts.py`
5. Build chatbot JSON output:
   - `python app/build_faq_dataset.py`

## Scheduler

GitHub Actions workflow:
- File: `.github/workflows/scrape-sources.yml`
- Cron: `45 3 * * *` (UTC) = `9:15 AM IST` daily
- Runs both scraping and key fact extraction
- Also supports manual trigger via `workflow_dispatch`

## Notes

- The URL list comes from the architecture document and `data/sources.csv`.
- The URL list is read from `LIP2urls.csv`.
- Duplicate URLs across funds are fetched once per run and reused.
- Failed source fetches are recorded with error details in `sources_snapshot.jsonl`.
- Key extracted fields: `expense_ratio` (numeric % from source text), `nav`, `exit_load`, `minimum_sip`, `lock_in_elss`, `riskometer`, `benchmark`, `statement_download`.

## Resolving merge conflicts for generated FAQ files

If GitHub shows conflicts in:
- `app/build_faq_dataset.py`
- `data/processed/fund_faq_data.json`

Use this CLI flow:

1. Update local base and switch to your branch:
   - `git fetch origin`
   - `git checkout <your-branch>`
   - `git merge origin/main`
2. Resolve conflicts in `app/build_faq_dataset.py` by keeping the latest extractor functions and removing all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
3. Regenerate JSON from the resolved script:
   - `python app/build_faq_dataset.py`
4. Stage and complete the merge:
   - `git add app/build_faq_dataset.py data/processed/fund_faq_data.json`
   - `git commit`
5. Push:
   - `git push origin <your-branch>`

Tip: prefer regenerating `data/processed/fund_faq_data.json` from the resolved Python script instead of manually merging JSON content.
This repository also sets a merge rule in `.gitattributes` to prefer the current branch version of `data/processed/fund_faq_data.json`, then regenerate after merge.
