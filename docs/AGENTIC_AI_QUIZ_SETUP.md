# ChuoSmart Agentic AI Quiz Setup

ChuoSmart can now generate module assessments through the Agentic AI Engine's OpenAI-compatible `POST /v1/chat/completions` endpoint. The gateway is preferred over the legacy Cerebras integration and deterministic fallback quizzes are disabled by default.

## 1. Deploy the Agentic AI Engine

Use the patched `agentic_ai_engine` project. Configure its service environment with at least:

```env
GATEWAY_API_KEY=<strong-random-shared-key>
GROQ_API_KEYS=<groq-key-or-comma-separated-keys>
GEMINI_API_KEYS=<gemini-key-or-comma-separated-keys>
OPENROUTER_API_KEYS=<openrouter-key-or-comma-separated-keys>
```

The model IDs are environment-configurable. The patched engine defaults are:

```env
GROQ_FAST_MODEL=openai/gpt-oss-20b
GROQ_BALANCED_MODEL=qwen/qwen3.8-27b
GROQ_REASONING_MODEL=openai/gpt-oss-120b
GEMINI_FAST_MODEL=gemini-3.5-flash-lite
GEMINI_BALANCED_MODEL=gemini-3.8-flash
GEMINI_REASONING_MODEL=gemini-3.8-flash
OPENROUTER_FREE_MODEL=openrouter/free
```

Start the gateway using the deployment method already supplied by the engine (or directly with Uvicorn):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify it before connecting ChuoSmart:

```bash
curl -fsS https://YOUR-AI-GATEWAY/health
```

## 2. Configure ChuoSmart

Set these variables in the ChuoSmart production service:

```env
AI_ASSESSMENT_PROVIDER=agentic
AGENTIC_AI_BASE_URL=https://agentic-ai-engine.onrender.com/v1
AGENTIC_AI_API_KEY=<same-value-as-GATEWAY_API_KEY>
AGENTIC_AI_ROUTE=structured
AGENTIC_AI_TIMEOUT_SECONDS=240
AI_ASSESSMENT_CONTEXT_LIMIT=12000
AI_ASSESSMENT_MAX_TOKENS=4000
AI_ASSESSMENT_ALLOW_DETERMINISTIC_FALLBACK=false
```

`CEREBRAS_API_KEY` is optional and is retained only for migration/backward compatibility. With `AI_ASSESSMENT_PROVIDER=agentic`, quiz generation goes directly to the agentic gateway.

## 3. Deploy and migrate ChuoSmart

After applying the patch and deploying the code:

```bash
python manage.py migrate
python manage.py check
```

Do not enable deterministic fallback in production. If the AI pool is temporarily unavailable, a quiz generation job should fail/retry rather than publishing a repeated template quiz to learners.

## 4. Replace every old fallback/non-AI module quiz

Preview what will be replaced:

```bash
python manage.py regenerate_all_quizzes --dry-run
```

Then regenerate every module quiz that is missing or has `ai_generated=False`:

```bash
python manage.py regenerate_all_quizzes --sleep 30
```

The command skips already confirmed AI-generated quizzes. A successfully regenerated quiz is marked `ai_generated=True`. If a free-provider rate limit interrupts the run, resolve/wait for the provider and rerun the command; already successful AI quizzes are skipped automatically.

By default the command stops at the first failure. To attempt every module and get a full list of failures at the end, add `--continue-on-error`:

```bash
python manage.py regenerate_all_quizzes --sleep 30 --continue-on-error
```

The command exits non-zero when any module failed, so it stays safe to use from cron.

If you intentionally want to regenerate every module assessment, including existing AI quizzes:

```bash
python manage.py regenerate_all_quizzes --force --sleep 30
```

## 5. Instructor module behavior

Instructors now have visible **Edit Module** and **Delete Module** controls on the course page. Deletion uses an explicit confirmation page and a POST request. Editing module metadata or module content queues fresh AI assessment generation so the assessment tracks corrected course material.

## 6. Production smoke test

After deployment, create or edit one small test module with factual lesson text. Confirm:

1. A quiz generation job is created.
2. The resulting quiz reaches `generation_status=ready`.
3. The quiz has the expected number of questions and `ai_generated=True`.
4. The questions reference the module content rather than generic repeated wording.
5. Instructor Edit Module saves successfully.
6. Instructor Delete Module displays confirmation and removes the chosen module after POST.

## 7. Troubleshooting `invalid_json` failures

Some reasoning models (`qwen3.8-27b`, `openai/gpt-oss-120b`) return their thinking
text — for example `User Safety: safe` — instead of the JSON body. The generator now:

- strips `<think>`/`<reasoning>` blocks and leading commentary before parsing,
- locates the JSON object with balanced-brace scanning so braces inside string
  values do not break extraction,
- recovers complete questions from a payload truncated by `max_tokens`,
- retries up to 3 times with a strict JSON-only repair prompt, growing
  `max_tokens` on each attempt, and
- logs `finish_reason` plus a 300-character payload preview.

If failures persist, raise the token budget and prefer a non-reasoning route:

```env
AI_ASSESSMENT_MAX_TOKENS=8000
AGENTIC_AI_ROUTE=structured
```
