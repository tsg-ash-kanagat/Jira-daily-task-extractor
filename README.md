---

# Jira Daily Activity Logger

This script fetches daily activities from Jira. It fetches issues updated by the current user within the previous 3 months by default.

## Installation

1. Clone the repository or download the script file.
2. Install the required Python libraries by running:

    ```sh
    python3 -m venv .venv; source .venv/bin/activate
    pip install -r requirements.txt 
    ```

3. Create a `.env` file in the same directory as the script and add the following lines, replacing the placeholder values with your actual Jira credentials:

    ```env
    JIRA_SERVER=https://your-jira-instance.atlassian.net
    JIRA_USERNAME=email@jobins.jp
    JIRA_API_TOKEN=your-api-token
    ```

## Usage
This is a streamlit app.To run use "streamlit run jira_daily_activity_logger.py' from terminal.  

## Notes
Make sure to replace placeholder values in the `.env` file with your actual Jira credentials.
