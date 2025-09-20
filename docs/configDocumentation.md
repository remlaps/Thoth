# Configuration File Documentation

This document explains the purpose of the sections and parameters in the `config.ini` file.

---

## [ARLIAI]
This section configures the AI model and related parameters.

- **ARLIAI_MODEL**: Specifies the AI model to use. Options include `Qwen3-14B`, `gemini-2.0-flash`, etc.
- **ARLIAI_URL**: The API endpoint for the AI model.
- **INITIAL_BACKOFF_SECONDS**: Initial delay before retrying a failed request.
- **JITTER_FACTOR**: Adds randomness to retry delays to avoid collisions.
- **MAX_RETRIES**: Maximum number of retry attempts for failed requests.
- **SYSTEM_PROMPT_FILE**: Path to the system prompt file.
- **SYSTEM_PROMPT_TEMPLATE**: Path to the system prompt template.
- **USER_PROMPT_FILE**: Path to the user prompt file.
- **USER_PROMPT_TEMPLATE**: Path to the user prompt template.

---

## [STEEM]
This section configures the Steem blockchain interaction.

- **DEFAULT_START_BLOCK**: The starting block number for processing.
- **POSTING_ACCOUNT**: The account used for posting.
- **POSTING_KEY**: The private key for the posting account.
- **STEEM_API**: The API endpoint for Steem blockchain.
- **SDS_API**: The API endpoint for Steem Data Services.
- **STREAM_TYPE**: Determines the type of stream (`ACTIVE`, `HISTORY`, or `RANDOM`).

---

## [CONTENT]
This section defines content filtering and validation rules.

- **AUTHOR_WHITELIST_FILE**: Path to the author whitelist file.
- **EXCLUDE_TAGS**: Tags to exclude from processing.
- **INCLUDE_TAGS**: Tags to include for processing.
- **LANGUAGE**: Supported languages (e.g., `en`, `de`, `es`).
- **MAX_DOWNVOTES**: Maximum allowed downvotes.
- **MAX_MENTION_COUNT**: Maximum allowed mentions in a post.
- **MAX_TAG_COUNT**: Maximum allowed tags in a post.
- **MIN_FEED_REACH**: Minimum feed reach for a post.
- **MIN_RESTEEMS**: Minimum required resteems.
- **MIN_REPLIES**: Minimum required replies.
- **MIN_WORDS**: Minimum word count for a post.
- **REGISTRY_ACCOUNT**: Account used for registry purposes.
- **WHITELIST_REQUIRED**: Whether a whitelist is required.

---

## [AUTHOR]
This section defines author validation rules.

- **FOLLOWER_HALFLIFE_YEARS**: Half-life of followers for activity calculation.
- **LAST_BLURT_ACTIVITY_AGE**: Required days since last activity on Blurt.
- **LAST_HIVE_ACTIVITY_AGE**: Required days since last activity on Hive.
- **MAX_FOLLOWER_INACTIVITY_DAYS**: Maximum allowed inactivity days for followers.
- **MAX_INACTIVITY_DAYS**: Maximum allowed inactivity days for the author.
- **MIN_ACCOUNT_AGE**: Minimum account age in days.
- **MIN_ACTIVE_FOLLOWERS**: Minimum number of active followers.
- **MIN_ADJUSTED_FOLLOWERS_PER_MONTH**: Minimum adjusted followers per month.
- **MIN_FOLLOWERS**: Minimum number of followers.
- **MIN_FOLLOWERS_PER_MONTH**: Minimum followers gained per month.
- **MIN_FOLLOWER_MEDIAN_REP**: Minimum median reputation of followers.
- **MIN_REPUTATION**: Minimum reputation of the author.

---

## [BLOG]
This section configures blog post parameters.

- **CURATED_AUTHOR_WEIGHT**: Weight assigned to curated authors.
- **DELEGATOR_WEIGHT**: Weight assigned to delegators.
- **INELIGIBLE_DELEGATORS**: Delegators ineligible for rewards.
- **NUMBER_OF_DELEGATORS_PER_POST**: Maximum delegators per post.
- **NUMBER_OF_REVIEWED_POSTS**: Number of reviewed posts.
- **POSTING_ACCOUNT_WEIGHT**: Weight assigned to the posting account.
- **POST_TAGS**: Tags to include in blog posts.
- **PRO_BONO_DELEGATORS**: Delegators excluded from rewards for pro-bono support.
- **THOTH_OPERATOR**: Name of the operator.

---

## [ENGAGEMENT]
This section defines engagement metrics.

- **COMMENT_MAX**: Maximum comment score.
- **COMMENT_MIN**: Minimum comment score.
- **COMMENT_WEIGHT**: Weight assigned to comments.
- **ENGAGEMENT_THRESHOLD**: Threshold for engagement.
- **RESETEEM_MAX**: Maximum resteem score.
- **RESTEEM_MIN**: Minimum resteem score.
- **RESTEEM_WEIGHT**: Weight assigned to resteems.
- **VALUE_MAX**: Maximum value score.
- **VALUE_MIN**: Minimum value score.
- **VALUE_WEIGHT**: Weight assigned to value.
- **VOTE_COUNT_MAX**: Maximum vote count.
- **VOTE_COUNT_MIN**: Minimum vote count.
- **VOTE_COUNT_WEIGHT**: Weight assigned to vote count.

---

## [WALLET]
This section configures wallet-related parameters.

- **SCREENED_DELEGATEE_FILE**: Path to the screened delegatee file.
- **MAX_DELEGATION_PCT**: Maximum allowed delegation percentage.
- **MAX_SCREENED_DELEGATION_PCT**: Maximum delegation percentage for screened delegatees.
- **MIN_UNDELEGATED_SP**: Minimum undelegated Steem Power.

---