# AI Code Review Comment Generator

This is a final-year-presentable AI project that uses an LLM API to review code diffs and generate developer-friendly review comments. It is designed as a practical software engineering assistant for identifying bugs, security issues, maintainability problems, and missing tests before code is merged.

The project works first through prompt engineering and includes a fine-tuning-ready dataset format so it can later be improved with custom training examples.

## Project Objective

Manual code review takes time and depends heavily on reviewer experience. Beginner developers often miss edge cases, unsafe patterns, or testing gaps. This project helps by analyzing a code diff and returning structured review feedback with severity levels and suggested fixes.

## Key Features

- Web interface for pasting and reviewing code diffs
- Command-line mode for reviewing `.patch` files
- OpenAI-compatible LLM API integration
- Structured review output with severity, category, location, issue, and fix
- Starter JSONL dataset for future fine-tuning
- Sample code diff included for testing
- GitHub-safe environment variable setup

## Tech Stack

- Python
- Flask
- OpenAI Python SDK
- HTML and CSS
- OpenAI-compatible chat completion API

## Folder Structure

```text
code_review_comment_generator/
  app.py
  README.md
  requirements.txt
  .env.example
  .gitignore
  data/
    train_examples.jsonl
  examples/
    sample_diff.patch
  static/
    style.css
  templates/
    index.html
```

## System Architecture

```text
User
  |
  v
Web UI / CLI
  |
  v
Diff Input Processor
  |
  v
Prompt Builder
  |
  v
LLM API
  |
  v
Structured Review Output
```

## How It Works

1. The user enters a code diff in the web UI or provides a patch file in CLI mode.
2. The backend creates a review prompt with strict output rules.
3. The prompt is sent to an LLM through an API.
4. The model returns review findings in a structured format.
5. The app displays the result to the user.

## Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Set environment variables:

```powershell
$env:AI_API_KEY="your_api_key_here"
$env:AI_BASE_URL="https://api.hke-cai.com/inference/v1"
$env:AI_MODEL="deepseek/deepseek-v4-pro"
```

Do not upload your real API key to GitHub. The project uses `.env.example` only as a template.

## Run Web App

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5001
```

## Run CLI Mode

```powershell
python app.py --diff examples/sample_diff.patch
```

## Example Input

```diff
+    print("updating", user_id, email)
     db.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
```

## Example Output

```text
Summary:
- The diff introduces a logging statement that may expose user data.

Findings:
- Severity: P2
  Category: security
  Location: update_email near print statement
  Issue: Email and user id are printed directly, which can leak sensitive data.
  Fix: Remove the print statement or use safe structured logging without sensitive fields.
```

## Fine-Tuning Dataset

The file `data/train_examples.jsonl` contains examples in chat fine-tuning format:

```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"Review this diff: ..."},{"role":"assistant","content":"...ideal review..."}]}
```

To make this project stronger, collect real diffs and ideal human review comments. A good final dataset should contain at least 100-500 high-quality examples.

## Evaluation Ideas

- Compare AI review comments with human review comments
- Count how many real bugs are detected
- Measure false positives
- Score output clarity and usefulness
- Compare base model output with fine-tuned model output

## Future Scope

- GitHub pull request integration
- File upload support
- JSON output mode
- Review history database
- Fine-tuned model comparison
- Multi-language code review support

## Presentation Summary

This project demonstrates how LLMs can support software development by automating first-pass code review. It combines prompt engineering, API integration, structured output generation, and fine-tuning data preparation.
