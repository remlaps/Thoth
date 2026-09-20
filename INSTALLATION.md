# Thoth — Installation & Configuration Guide

This guide is written for **developers and operators** who want to install, configure, and run a Thoth AI curation bot instance on the Steem blockchain.

> **Version note:** This guide matches Thoth **0.1.14-beta**. The project is under active development — after every upgrade, review `config/config.ini`, especially settings related to post screening and beneficiary rewards.

> **Secret note:** Every key, password, or token shown in this document is an *obvious placeholder* (e.g., `your_wallet_password_here`). Never paste real API keys, wallet passwords, or posting keys into `config/config.ini`, `config/config.template`, or any file you intend to commit.

> **Untested note:** These installation instructions have **not been tested** end-to-end on a clean machine. They are provided as guidance and may require adjustments for your operating system, Python version, or existing dependency state. Validate each step in a disposable environment — and run with `DRY_RUN = True` — before pointing a fresh install at a live Steem account.

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Steem account & wallet setup](#2-steem-account--wallet-setup)
3. [Installation](#3-installation)
4. [Configuration overview](#4-configuration-overview)
5. [Environment variables and secrets](#5-environment-variables-and-secrets)
6. [Full parameter reference](#6-full-parameter-reference)
7. [Beneficiary weight constraints](#7-beneficiary-weight-constraints)
8. [LLM model switching (rate-limit resilience)](#8-llm-model-switching-rate-limit-resilience)
9. [Running Thoth](#9-running-thoth)
10. [Verifying your setup](#10-verifying-your-setup)
11. [Security checklist](#11-security-checklist)
12. [Troubleshooting & notes](#12-troubleshooting--notes)

## 1. Prerequisites

- **Python 3.x** — Thoth depends on `steem-python` (`steem==1.0.2`), an older library. If you hit wheel or dependency issues, use an older Python release inside a dedicated virtual environment. For Windows specifics, see [Getting steem-python to run on Windows with the latest python version](https://steemit.com/steem-dev/@remlaps/getting-steem-python-to-run).
- **A Steem account with Steem Power (SP)** — the *posting account* that Thoth posts, replies, and votes as.
- **LLM API access** — an API key for a supported provider. Thoth is tested with **Google Gemini** and **ArliAI** (OpenAI-compatible chat/completions endpoints).
- **Node access** — a public Steem API node (leave `STEEM_API` blank for the library default) and, optionally, a [Steem Data Services](https://sds.steemworld.org) endpoint for community/resteem lookups.

## 2. Steem account & wallet setup

1. Create a Steem account (for example `@my-thoth-bot`) and record its **Posting key**.
2. Make sure the account holds enough Steem Power to post and upvote.
3. Decide how Thoth will authenticate:
   - **Wallet mode (recommended):** set up a local `steem-python` wallet for the account, and provide the wallet unlock password via the `UNLOCK` environment variable at run time.
   - **Key mode:** provide the Posting private key via the `POSTING_KEY` environment variable. Avoid storing real keys in configuration files.

## 3. Installation

```bash
# 1. Clone the repository
git clone https://github.com/remlaps/Thoth.git
cd Thoth

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate             # Windows
# source venv/bin/activate        # Linux / macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your config from the template
copy config\config.template config\config.ini    # Windows
# cp config/config.template config/config.ini    # Linux / macOS

# 5. Edit config\config.ini to match your environment (see Sections 4-6).
```

Generated runtime files (auto-copied prompt files, whitelists, delegation lists, state files) also live under `config\` and must not be committed — see the [Security checklist](#11-security-checklist).

## 4. Configuration overview

Thoth is configured through **two** mechanisms:

| Mechanism | Purpose | Examples |
|---|---|---|
| `config/config.ini` | All bot behavior | models, screening rules, scores, beneficiary weights, stream settings |
| Environment variables | Secrets (recommended) | `UNLOCK`, `POSTING_KEY`, `LLMAPIKEY` |

**Precedence rules:**

- **LLM API key:** the `LLMAPIKEY` environment variable takes priority; if it is not set, Thoth falls back to `LLM_API_KEY` in `config/config.ini`.
- **Steem authentication:** if the `UNLOCK` environment variable is set, Steem is initialized in wallet mode (no explicit keys). Otherwise the `POSTING_KEY` (from the environment or `config.ini`) is used directly.

## 5. Environment variables and secrets

| Variable | Required | Purpose |
|---|---|---|
| `UNLOCK` | One of `UNLOCK` / `POSTING_KEY` | Steem wallet unlock password (wallet mode) |
| `POSTING_KEY` | One of `UNLOCK` / `POSTING_KEY` | Posting private key when not using wallet mode |
| `LLMAPIKEY` | Required (or `LLM_API_KEY` in config) | LLM API key |

> **Critical:** never put real values in `config/config.ini`, `config/config.template`, or any committed file. `config/config.template` intentionally ships with the keys empty and commented out (header warning: *"DO NOT COPY KEYS into config.template"*) — keep it that way when submitting changes.

## 6. Full parameter reference

All settings live in `config/config.ini`, grouped by `[SECTION]`. The tables below list **every** parameter from `config/config.template` with a description and a **suggested starting value** (synchronized with the current reference configuration). Adjust values for your own risk tolerance and goals.

> **Weight convention:** in `[BLOG]`, weights are Steem *basis points* where `10000 = 100%`.

### `[LLM]` — AI model & prompt settings

| Parameter | Description | Suggested starting value |
|---|---|---|
| `LLM_API_KEY` | Fallback LLM API key if the `LLMAPIKEY` environment variable is not set. **Leave empty — use the environment variable.** | *(empty)* |
| `LLM_MODEL` | Comma-separated model list, tried in order (primary first). If the active model is rate-limited, Thoth can fall back to the next one. | `gemma-4-31b-it, gemini-3.5-flash-lite, gemini-2.5-flash` |
| `LLM_URL` | Base URL of the OpenAI-compatible chat/completions endpoint. Tested with Google Gemini and ArliAI. | Gemini: `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` · ArliAI: `https://api.arliai.com/v1/chat/completions` |
| `INITIAL_BACKOFF_SECONDS` | Initial delay (seconds) before retrying a failed LLM request; grows with each retry. | `15.0` |
| `JITTER_FACTOR` | Randomness added to retry delays to prevent synchronized retries. | `0.2` |
| `MAX_RETRIES` | Maximum number of retry attempts per LLM request. | `9` |
| `OUTPUT_LANGUAGE` | Language of Thoth's generated posts/replies. Options: `English`, `German`, `Spanish`. | `English` |
| `SYSTEM_PROMPT_FILE` | Path to the generated system prompt file used for curation. | `config\systemPrompt.txt` (auto-created from template on first run) |
| `SYSTEM_PROMPT_TEMPLATE` | Template base path; the bot appends `_<modelPrefix>.txt` (e.g., `...Template_gemini.txt`), so keep the model-specific template files available. Do **not** add a `.txt` suffix here. | `config\systemPromptTemplate` |
| `USER_PROMPT_FILE` | Path to the generated user prompt file used for curation. | `config\userPrompt.txt` (auto-created from template on first run) |
| `USER_PROMPT_TEMPLATE` | Template base path for the user prompt (model-suffixed, as above; no `.txt` suffix). | `config\userPromptTemplate` |
| `SKIP_AI_CURATION` | When `True`, skips real LLM calls and inserts dummy text instead (testing only). | `False` |
| `LLM_ENABLE_MODEL_SWITCHING` | When `True`, automatically switch to the next model in `LLM_MODEL` when the current model is rate-limited (HTTP 429/503). | `True` |
| `LLM_MODEL_SWITCHING_DRY_RUN` | When `True` (with switching enabled), log rate-limit events and which model *would* be used, but keep using the current model. | `False` |

### `[BLOG]` — post construction & beneficiary rewards

| Parameter | Description | Suggested starting value |
|---|---|---|
| `CURATED_AUTHOR_WEIGHT` | Beneficiary weight (basis points) each curated author receives on the overview post. | `660` (6.6%) |
| `DELEGATOR_WEIGHT` | Beneficiary weight each included delegator receives on the overview post. | `2100` (21%) |
| `NUMBER_OF_DELEGATORS_PER_POST` | Number of top delegators included as beneficiaries per reply post (max 5). | `2` |
| `NUMBER_OF_REVIEWED_POSTS` | Number of posts to find, review, and feature per run (max 5). | `5` |
| `POSTING_ACCOUNT_WEIGHT` | Beneficiary weight for the Thoth posting account itself. | `0` |
| `POST_TAGS` | Comma-separated tags applied to Thoth's posts. Replace the test tags before going live. | `thoth-test, thoth-trove, lifetime-rewards, passive-rewards, burnsteem25` |
| `IMAGE_FOR_INTRO` | URL of the featured image used in the overview post. | *(value provided in the template)* |
| `IMAGE_FOR_REPLIES` | URL of the featured image used in the reply posts. | *(value provided in the template)* |
| `INELIGIBLE_DELEGATORS` | Comma-separated delegators excluded from rewards (e.g., flagged accounts). | *(empty)* |
| `PRO_BONO_DELEGATORS` | Comma-separated delegators excluded from rewards for pro-bono support. | *(empty)* |
| `THOTH_OPERATOR` | Operator name/alias, published inside Thoth's posts. | *(empty — set to your handle/name)* |
| `MIN_CURATION_TIER` | Minimum quality tier required for curation: `excellent`, `good`, `fair`, `poor`, `reject`. | `fair` |
| `VOTE_DELAY_SECONDS` | Delay (seconds) before Thoth upvotes its own posts/replies. | `1800` |
| `VOTE_PERCENT` | Vote weight used when upvoting (percentage, 0–100). | `100` |

### `[AUTHOR]` — author validation & scoring rules

| Parameter | Description | Suggested starting value |
|---|---|---|
| `ENABLE_MEDIAN_REP_SCORING` | Enable median-follower-reputation scoring. Can be slow/API-heavy for accounts with many followers. | `True` |
| `FOLLOWER_HALFLIFE_YEARS` | Half-life (years) used to decay follower activity in the adjusted-followers metric. | `4` |
| `MIN_BLURT_INACTIVITY_HARD` | Minimum days since the author's last Blurt activity; more recent activity → hard rejection. | `3` |
| `MIN_HIVE_INACTIVITY_HARD` | Minimum days since the author's last Hive activity; more recent activity → hard rejection. | `10` |
| `TARGET_BLURT_INACTIVITY_DAYS` | Inactivity (days) that earns the maximum Blurt-inactivity score points. | `30` |
| `TARGET_HIVE_INACTIVITY_DAYS` | Inactivity (days) that earns the maximum Hive-inactivity score points. | `180` |
| `MAX_FOLLOWER_INACTIVITY_DAYS` | Days within which a follower counts as "active". | `60` |
| `MAX_INACTIVITY_DAYS` | Maximum author inactivity considered; beyond this, authors are treated as too dormant. | `950` |
| `MAX_INCLUDED_POSTS_PER_AUTHOR` | Maximum posts per author allowed in one run's included-posts list. | `1` |
| `MIN_ACCOUNT_AGE` | Minimum account age in days. **Not implemented** — loaded but not used in validation. | `30` |
| `MIN_ACTIVE_FOLLOWERS` | Minimum number of active followers required. **Not implemented** — loaded but not used in validation. | `30` |
| `MIN_ADJUSTED_FOLLOWERS_PER_MONTH` | Minimum adjusted follower growth per month. | `3` |
| `MIN_FOLLOWERS` | Minimum total follower count. | `200` |
| `MIN_FOLLOWERS_PER_MONTH` | Minimum followers gained per month. | `5` |
| `MIN_FOLLOWER_MEDIAN_REP` | Minimum median reputation of the author's followers. | `35` |
| `MIN_REPUTATION` | Minimum reputation of the author. | `56` |

### `[CONTENT]` — content screening rules

| Parameter | Description | Suggested starting value |
|---|---|---|
| `AUTHOR_WHITELIST_FILE` | Path to the author whitelist file. | `config\authorWhiteList.txt` |
| `WHITELIST_REQUIRED` | When `True`, only whitelisted authors pass screening. | `False` |
| `EXCLUDE_TAGS` | Comma-separated tags that cause instant rejection. | *(long list in the template — includes `actifit`, `contest`, `pornography`, `test`, etc.)* |
| `INCLUDE_TAGS` | Comma-separated tags that are enforced (posts must include them). | *(empty)* |
| `LANGUAGE` | Allowed post languages. Posts whose detected language is not in this list are rejected. | `de, en, es, fr, it, uk, pt, pl` |
| `MAX_TAG_COUNT` | Maximum number of tags a post may carry. | `10` |
| `MIN_WORDS` | Minimum word count for scoring (soft minimum). | `500` |
| `MIN_WORDS_HARD` | Hard minimum word count; posts below this are rejected outright. | `250` |
| `REGISTRY_ACCOUNT` | Account whose mute/tag history is consulted (currently used for mutes only). | `penny4thoughts` |
| `MAX_DOWNVOTES` | Maximum allowed downvotes. **Not implemented** — loaded but not used. | `5` |
| `MAX_MENTION_COUNT` | Maximum allowed mentions. **Not implemented** — loaded but not used. | `10` |
| `MAX_VOTING_SERVICE_PCT` | Maximum allowed voting-service usage %. **Not implemented** — loaded but not used. | `25` |
| `MIN_RESTEEMS` | Minimum required resteems. **Not implemented** — loaded but not used. | `0` |
| `MIN_REPLIES` | Minimum required replies. **Not implemented** — loaded but not used. | `0` |

### `[ENGAGEMENT]` — engagement scoring

Engagement is scored as a weighted average; `MIN`/`MAX` values define the normalization range for each metric. `MIN`/`MAX`/`WEIGHT` triples should be kept consistent.

| Parameter | Description | Suggested starting value |
|---|---|---|
| `COMMENT_MIN` / `COMMENT_MAX` | Range used to normalize the comment count. | `-2` / `19` |
| `COMMENT_WEIGHT` | Weight of the comment sub-score in the engagement score. | `3` |
| `ENGAGEMENT_THRESHOLD` | Minimum engagement score required to pass (used when engagement screening applies). | `12` |
| `RESTEEM_MIN` / `RESTEEM_MAX` | Range used to normalize the resteem count. | `-2` / `10` |
| `RESTEEM_WEIGHT` | Weight of resteems in the engagement score (resteem counts are fetched via `SDS_API`). | `3` |
| `VALUE_MIN` / `VALUE_MAX` | Range used to normalize post value (estimated payout). | `0.25` / `10.0` |
| `VALUE_WEIGHT` | Weight of post value in the engagement score. | `1` |
| `VOTE_COUNT_MIN` / `VOTE_COUNT_MAX` | Range used to normalize the vote count. | `20` / `500` |
| `VOTE_COUNT_WEIGHT` | Weight of votes in the engagement score. | `2` |
| `FEED_REACH_SCREENING_ENABLED` | When `True`, enable the feed-reach (audience size) screening rule. | `True` |
| `FEED_REACH_MIN` | Minimum feed reach required when feed-reach screening is enabled. | `150` |
| `FEED_REACH_MAX` | Upper bound used when scaling the feed-reach metric. | `50000` |
| `FEED_REACH_WEIGHT` | Weight of feed reach in the engagement score. | `2` |

### `[HISTORY]` — curation frequency limits

| Parameter | Description | Suggested starting value |
|---|---|---|
| `MAX_AUTHOR_PER_DAY` | Maximum times a given author can be curated within 24 hours. | `1` |
| `MAX_AUTHOR_PER_WEEK` | Maximum times a given author can be curated within 7 days. | `3` |
| `MAX_POST_PER_MONTH` | Maximum times a given post can be curated within a 30-day lookback. | `1` |
| `SKIP_ONCHAIN_HISTORY` | When `True`, skip broadcasting Thoth's state/history linked list to the blockchain via `custom_json`. | `True` |

### `[SCORING]` — quality scoring model

The **author** component uses the `MAX_*` scores for reputation, followers, age, activity, and inactivity; the **content** component uses `MAX_LENGTH_SCORE`, `MAX_TITLE_SCORE`, `MAX_TAG_SCORE`, and `MAX_LANGUAGE_SCORE`; the three component weights should sum to `1.0`.

> **Note:** `MAX_BLURT_INACTIVITY_SCORE` and `MAX_INFLUENCE_SCORE` are still read by the scoring engine but are no longer present in the reference configuration; when absent, the engine falls back to its built-in default of `10.0`. `MAX_NET_FOLLOWERS_SCORE` is present in the configuration but is not yet wired into the engine.

| Parameter | Description | Suggested starting value |
|---|---|---|
| `MAX_REPUTATION_SCORE` | Maximum points for author reputation. | `5.0` |
| `MAX_FOLLOWERS_PER_MONTH_SCORE` | Maximum points for follower growth rate. | `10.0` |
| `MAX_ADJUSTED_FOLLOWERS_SCORE` | Maximum points for half-life-adjusted follower growth. | `25.0` |
| `MAX_MEDIAN_REP_SCORE` | Maximum points for median follower reputation. | `20.0` |
| `MAX_AGE_SCORE` | Maximum points for account age. | `5.0` |
| `MAX_ACTIVITY_SCORE` | Maximum points for author activity. | `10.0` |
| `MAX_NET_FOLLOWERS_SCORE` | Maximum points for net followers (followers minus following). | `10.0` |
| `MAX_HIVE_INACTIVITY_SCORE` | Maximum points for Hive inactivity (peaks at `TARGET_HIVE_INACTIVITY_DAYS`). | `15.0` |
| `MAX_LENGTH_SCORE` | Maximum points for content length. | `25.0` |
| `MAX_TITLE_SCORE` | Maximum points for title length/quality. | `10.0` |
| `MAX_TAG_SCORE` | Maximum points for optimal tag usage. | `10.0` |
| `MAX_LANGUAGE_SCORE` | Maximum points for language readability. | `25.0` |
| `COMPONENT_AUTHOR_WEIGHT` | Weight of the author score component in the total score. | `0.60` |
| `COMPONENT_CONTENT_WEIGHT` | Weight of the content score component in the total score. | `0.25` |
| `COMPONENT_ENGAGEMENT_WEIGHT` | Weight of the engagement score component in the total score. | `0.15` |
| `TIER_EXCELLENT_MIN` | Total score threshold for the `excellent` tier. | `65.0` |
| `TIER_GOOD_MIN` | Total score threshold for the `good` tier. | `61.0` |
| `TIER_FAIR_MIN` | Total score threshold for the `fair` tier. | `58.0` |
| `TIER_POOR_MIN` | Total score threshold for the `poor` tier. | `45.0` |

### `[STEEM]` — blockchain connection & stream settings

| Parameter | Description | Suggested starting value |
|---|---|---|
| `POSTING_ACCOUNT` | The Steem account Thoth posts, replies, and votes as. | `social` *(replace with your account)* |
| `POSTING_KEY` | Fallback Posting private key. **Leave empty — use `UNLOCK` or the `POSTING_KEY` environment variable.** | *(empty)* |
| `DRY_RUN` | When `True`, run the full pipeline but skip on-chain posting, replies, and votes. Useful for testing. | `False` |
| `DEFAULT_START_BLOCK` | Block number to start from when no prior run history is found. | `3250000` |
| `STEEM_API` | Comma-separated Steem node URL(s). Blank = library default. | *(empty)* |
| `SDS_API` | Steem Data Services base URL (community and resteem lookups). | `https://sds.steemworld.org` |
| `STREAM_TYPE` | Which posts to sample: `ACTIVE` (recent posts), `HISTORY` (from last run), `RANDOM`, or `TIME_WEIGHTED_RANDOM`. | `TIME_WEIGHTED_RANDOM` |
| `STREAM_TIME_WEIGHT` | Time-bias for `TIME_WEIGHTED_RANDOM`: `0.0` = uniform random, larger values favor more recent blocks. | `0.8` |

### `[WALLET]` — delegation & power-down screening

These rules evaluate whether an *author* has healthy "skin in the game" before being curated.

| Parameter | Description | Suggested starting value |
|---|---|---|
| `DELEGATION_FILE` | Path to the screened-delegatee list (same file as `SCREENED_DELEGATEE_FILE`). | `config\delegationScreen.txt` |
| `SCREENED_DELEGATEE_FILE` | File listing accounts to which delegations count as "screened" (risk). | `config\delegationScreen.txt` |
| `UNCOUNTED_DELEGATEE_FILE` | File listing safe partners; delegations to these accounts are **not** penalized. | `config\delegationUncounted.txt` |
| `MAX_DELEGATION_PCT` | Maximum % of an author's SP that may be delegated away (net of safe delegations) before failing screening. | `50.0` |
| `MAX_SCREENED_DELEGATION_PCT` | Maximum % of SP delegated *to screened accounts* before the author is flagged. | `25.0` |
| `MAX_POWERDOWN_YEARLY_PCT` | Maximum yearly power-down rate (%) allowed before the author is flagged. | `260.0` |
| `MIN_UNDELEGATED_SP` | Minimum SP the author must keep undelegated. | `6.0` |

## 7. Beneficiary weight constraints

Steem enforces two hard limits on beneficiary settings. Review these carefully before changing anything in `[BLOG]`.

- **Weight limit:** the sum of all beneficiary weights on a post cannot exceed `10000` (which is 100%). The constraint for the overview post is:

  ```
  ( NUMBER_OF_DELEGATORS_PER_POST × DELEGATOR_WEIGHT )
  + ( NUMBER_OF_REVIEWED_POSTS × CURATED_AUTHOR_WEIGHT )
  + POSTING_ACCOUNT_WEIGHT
  ≤ 10000
  ```

  The reference config satisfies this: `(2 × 2100) + (5 × 660) + 0 = 7500` (75%).

- **Slot limit:** Steem allows a maximum of **8 beneficiaries** per post. Thoth always reserves one slot for `@null`, plus one more for the posting account when `POSTING_ACCOUNT_WEIGHT > 0`. So `NUMBER_OF_DELEGATORS_PER_POST + NUMBER_OF_REVIEWED_POSTS + (1 if POSTING_ACCOUNT_WEIGHT > 0 else 0) + 1 ≤ 8`. The reference config uses `2 + 5 + 0 + 1 = 8` — exactly at the limit. If you set `POSTING_ACCOUNT_WEIGHT > 0`, reduce one of the counts.

- **Value adjustments:** author and delegator weights are recalculated from these values for Thoth's *reply* posts, so replies may differ from the overview post.

## 8. LLM model switching (rate-limit resilience)

If `LLM_MODEL` lists multiple models, Thoth can automatically switch to the next one when the current model returns HTTP 429 (rate-limited) or 503 (overloaded). The reference config enables this (`LLM_ENABLE_MODEL_SWITCHING = True`). The following rollout is recommended when tuning it:

1. **Most conservative:** `LLM_ENABLE_MODEL_SWITCHING = False`. Thoth uses standard retry/backoff and never switches models.
2. **Observation / dry-run:** `LLM_ENABLE_MODEL_SWITCHING = True`, `LLM_MODEL_SWITCHING_DRY_RUN = True`. Thoth logs rate-limit events and which model it *would* switch to, but keeps using the current model.
3. **Live:** `LLM_ENABLE_MODEL_SWITCHING = True`, `LLM_MODEL_SWITCHING_DRY_RUN = False`. On rate-limit, Thoth automatically switches to the next model and retries.

When enabled, watch the logs for:
- `WARNING - Marking model as rate limited: <model-name>`
- `WARNING - Switching to next model: <new-model> (Rate limited models: [...])`
- `ERROR - No more models available. All models rate limited: [...]`

## 9. Running Thoth

Activate your virtual environment, set the required environment variables, and run from the project root:

```bat
:: Example run.bat (Windows)
@echo off
call C:\path\to\your\venv\Scripts\activate
REM Set the steering vars for this session only (use 'setx' only from a PRIVATE session if you want them persistent).
set UNLOCK=your_wallet_password_here
set LLMAPIKEY=your_llm_api_key_here
cd /d C:\path\to\your\Thoth\
python src\main.py
call deactivate
```

On Linux/macOS, equivalently:

```bash
export UNLOCK="your_wallet_password_here"
export LLMAPIKEY="your_llm_api_key_here"
source venv/bin/activate
python src/main.py
```

Prerequisites that must be satisfied at startup (the config validator checks these and **exits** if they are missing):

- `[LLM] LLM_MODEL` and `[LLM] LLM_URL` must be set.
- `LLMAPIKEY` env var **or** `[LLM] LLM_API_KEY` must be present.
- `[STEEM] POSTING_ACCOUNT` must be set.
- `UNLOCK` env var **or** `[STEEM] POSTING_KEY` must be present.

> Before a live run, test with `DRY_RUN = True` (posting/replies/votes are skipped) to confirm that screening and AI evaluation run cleanly.

Recommended production practice: run Thoth on a schedule (e.g., cron or Task Scheduler) rather than as a one-shot manual process.

## 10. Verifying your setup

- **`python tools\checkValidation.py @author`** (also accepts `@author/permlink`) — runs the production screening/scoring engine against a target author without needing live keys. Displays an author status summary, eligibility checks, history usage, wallet flags, and detailed score breakdowns.
- **`python tools\verify_hybrid_implementation.py`** — confirms the hybrid screening components are integrated and rule-precedence logic is correct.

## 11. Security checklist

- [ ] Never put real API keys, wallet passwords, or posting keys in `config/config.ini`, `config/config.template`, or any committed file.
- [ ] Keep the template's header warning intact and ship `config/config.template` **without keys** (both `LLM_API_KEY` and `POSTING_KEY` commented out / empty).
- [ ] Confirm `config/config.ini`, `.env`, `configBackups`, and the generated prompt/whitelist/delegation files are covered by `.gitignore` (they are in this repo).
- [ ] Prefer environment variables for secrets: set `UNLOCK` and `LLMAPIKEY` for the session only (`set`/`export`); avoid `setx` unless you understand it persists outside the shell.
- [ ] If a secret is ever committed or leaked, consider it compromised — rotate the affected key immediately.

## 12. Troubleshooting & notes

| Symptom | Likely cause / fix |
|---|---|
| `FATAL: LLM API key is missing or empty` | Set the `LLMAPIKEY` environment variable or `[LLM] LLM_API_KEY`. |
| `Either UNLOCK environment variable or [STEEM] POSTING_KEY must be set` | Provide a wallet unlock (`UNLOCK`) or a Posting key (`POSTING_KEY`). |
| SSL `CERTIFICATE_VERIFY_FAILED` on SDS calls | Update `certifi` (`pip install -U certifi`); the 0.1.13 release pins a CA bundle for these calls. |
| Beneficiary validation error at startup | Re-check the weight and slot limits in [Section 7](#7-beneficiary-weight-constraints). |
| Resteems reported as `0` | Resteem counts are fetched via `SDS_API` (`getResteems`); ensure `SDS_API` is reachable and configured. |
| No posts accepted | Review screening thresholds in `[AUTHOR]`, `[CONTENT]`, `[ENGAGEMENT]`, and `MIN_CURATION_TIER`; use `tools\checkValidation.py` to diagnose a specific author. |

**Parameters flagged "Not implemented"** (`MIN_ACCOUNT_AGE`, `MIN_ACTIVE_FOLLOWERS`, `MAX_DOWNVOTES`, `MAX_MENTION_COUNT`, `MAX_VOTING_SERVICE_PCT`, `MIN_RESTEEMS`, `MIN_REPLIES`) are loaded by the config but not yet used in validation. They are safe to leave at the suggested starting values.