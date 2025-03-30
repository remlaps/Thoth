
## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/remlaps/Thoth.git
    cd Thoth
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```
    *   The `requirements.txt` file should include:
        ```
        steem
        langdetect
        requests
        ```

3.  **Configure `config/config.ini`:**

    Most of these parameters can be copied from config/config.template, which is included in the distribution.

    *   **`ARLIAI`:**
        *   `ARLIAI_KEY`: Your API key for the AI model.
        *   `ARLIAI_MODEL`: The name of the AI model to use.
        *   `ARLIAI_URL`: The API endpoint for the AI model.
    *   **`STEEM`:**
        *   `POSTING_KEY`: Your Steem posting key (optional, but not recommended).
        *   `STEEM_API`: The Steem API endpoint (optional, defaults to public nodes).
        *   `STREAM_TYPE`: `RANDOM`, `ACTIVE`, or `HISTORY` (determines how Thoth streams blockchain data).
        *   `DEFAULT_START_BLOCK`: The block number to start streaming from (used for `RANDOM` and `HISTORY`).
    *   **`BLOG`:**
        *   `POSTING_ACCOUNT`: The Steem account Thoth will use to post.
        *   `POSTING_ACCOUNT_WEIGHT`: The weight assigned to the posting account in beneficiary rewards.
        *   `NUMBER_OF_REVIEWED_POSTS`: The number of posts to review per curation post.
        *   `CURATED_AUTHOR_WEIGHT`: The weight assigned to curated authors in beneficiary rewards.
    *   **`CONTENT`:**
        *   `MIN_WORDS`: The minimum word count for a post to be considered.
        *   `EXCLUDE_TAGS`: A comma-separated list of tags to exclude.
        *   `LANGUAGE`: A comma-separated list of target languages.
        *   `REGISTRY_ACCOUNT`: The account used for the blacklist registry.
    *   **`AUTHOR`:**
        *   `MIN_REPUTATION`: The minimum reputation score for an author.
        *   `MIN_FOLLOWERS`: The minimum number of followers for an author.
        *   `MIN_FOLLOWERS_PER_MONTH`: The minimum number of followers gained per month.
        *   `MAX_INACTIVITY_DAYS`: The maximum number of days an author can be inactive.
        * `MIN_FOLLOWER_MEDIAN_REP`: The minimum median reputation of an author's followers.
        * `LAST_HIVE_ACTIVITY_AGE`: The minimum number of days since an author's last Hive activity.

4.  **Set the `UNLOCK` environment variable (optional):**

    *   If you prefer to use the `steem-python` wallet, you can set the `UNLOCK` environment variable. Otherwise, you'll need to provide the posting key in `config.ini`.
    *   On Linux/macOS: `export UNLOCK=true`
    *   On Windows: `set UNLOCK=true`

## Usage

1.  **Run Thoth:**

    ```bash
    python src/main.py
    ```

    Thoth will start streaming blockchain data, screening posts, and generating curation reports. When it has collected enough posts, it will create a curation post on Steem.

## How It Works

1.  **Blockchain Streaming:** Thoth streams blockchain operations (comments) from a specified starting block.
2.  **Content Screening:** It filters out posts that are too short, edited, have blacklisted tags, are in the wrong language, or are from screened authors.
3.  **AI Curation:** It sends the remaining posts to the configured AI model for evaluation.
4.  **Curation Report:** The AI generates a curation report for each post, including key takeaways, target audience, and conversation starters.
5.  **Post Creation:** Thoth compiles the curated posts and AI reports into a single post on Steem.
6.  **Beneficiary Rewards:** It sets up beneficiary rewards to distribute to the authors of the curated posts and the posting account.

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on GitHub. If you'd like to contribute code, please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is provided as-is, without any warranty. Use at your own risk.
