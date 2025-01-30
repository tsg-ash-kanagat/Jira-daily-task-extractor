import streamlit as st
import os
import logging
from datetime import datetime, timedelta
from jira import JIRA
from jira.exceptions import JIRAError
from dotenv import load_dotenv
import pytz
from tzlocal import get_localzone
import pandas as pd

# Configuration (load environment variables and set constants)
load_dotenv()
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_USERNAME = os.getenv('JIRA_USERNAME')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY') or "INFRAARCH"
START_DATE_FIELD_ID = "created"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezones
LOCAL_TZ = get_localzone()
TOKYO_TZ = pytz.timezone('Asia/Tokyo')

# JIRA Connection
try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    logger.debug(f"Successfully connected to JIRA at {JIRA_SERVER}")
except JIRAError as e:
    logger.error(f"JIRA connection error: {e}")
    st.error(f"JIRA connection error: {e}")
    st.stop()

# Streamlit Configuration (MUST be at the top)
st.set_page_config(layout="wide")

# Input elements (moved outside of main())
st.markdown("<h1 style='text-align: center;'>JIRA Task Viewer</h1>", unsafe_allow_html=True)

# Inject CSS to center the text input field and label
st.markdown(
    """
    <style>
        .stTextInput>label {
            display: flex;
            justify-content: center;
            font-size: 16px;
            font-weight: bold;
        }
        .stTextInput>div>div>input {
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Center the input field inside a column layout
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    date_str = st.text_input("Enter start date (MM/DD/YYYY, empty for 3 months ago):", key="date_input")

col4, col5, col6 = st.columns([1, .2, 1])
with col4:
    pass
with col5:
    submitted = st.button("Submit", key="submit_button")
with col6:
    cancelled = st.button("Quit Application", key="cancel_button")


def get_date_input(local_tz):
    """Processes date input and returns a dictionary."""

    if cancelled:
        #st.write("Application cancelled. Please close this tab.")  # Inform the user
        st.markdown(
            """
            <style>
                .center-text {
                    text-align: center;
                    font-size: 20px;
                    font-weight: bold;
                }
            </style>
            <div class="center-text">
                Application cancelled. Please close this tab.
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<script>window.close();</script>", unsafe_allow_html=True)  # Attempt to close tab
        st.stop()  # Stop script execution

    if submitted:
        if not date_str:  # Handle empty date string
            three_months_ago = datetime.now(local_tz) - timedelta(days=90)
            return {'date': three_months_ago.date(), 'submitted': True}
        try:
            input_date = datetime.strptime(date_str, '%m/%d/%Y').date()  # Correct date format
            return {'date': input_date, 'submitted': True}
        except ValueError:
            st.error("Invalid date format. Use MM/DD/YYYY.")

    return {'date': None, 'submitted': False}


def fetch_all_issues_since(start_date):
    """Fetch issues since start_date, handling None. Returns a list of JIRA issue objects or an empty list."""
    if start_date is None:
        return []

    jql_query = (
        f'assignee = currentUser() AND {START_DATE_FIELD_ID} >= "{start_date.strftime("%Y-%m-%d")}" '
        f'AND status != "Done" ORDER BY {START_DATE_FIELD_ID} ASC'
    )
    try:
        issues = jira.search_issues(jql_query, maxResults=False)
        return issues
    except JIRAError as e:
        logger.error(f"JIRA error fetching issues: {e}")
        st.error(f"JIRA error fetching issues: {e}")
        return []


def format_issue_info(issue):
    """Format issue info for table. Returns a dictionary of issue information or an empty dictionary."""
    try:
        return {
            'key': issue.key,
            'summary': issue.fields.summary,
            'type': issue.fields.issuetype.name,
            'link': f"{JIRA_SERVER}/browse/{issue.key}",
            'created': datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M'),
            'updated': datetime.strptime(issue.fields.updated, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M'),
            'status': issue.fields.status.name,
        }
    except AttributeError as e:
        logger.warning(f"Missing field in issue {issue.key}: {e}")
        st.warning(f"Missing field in issue {issue.key}: {e}")
        return {}


def main():
    """Main function."""

    date_info = get_date_input(LOCAL_TZ)

    if date_info['submitted']:
        st.empty()

        start_date = date_info['date']

        if start_date is None:
            three_months_ago = datetime.now(LOCAL_TZ) - timedelta(days=90)
            start_date = three_months_ago.date()

        issues = fetch_all_issues_since(start_date)
        if not issues:
            st.info("No issues found.")
            return

        issue_data = []
        for issue in issues:
            issue_info = format_issue_info(issue)
            if issue_info:
                issue_data.append([
                    issue_info['key'],
                    issue_info['summary'],
                    issue_info['type'],
                    issue_info['status'],
                    issue_info['link'],
                    issue_info['created'],
                    issue_info['updated'],
                ])

        issue_data.sort(key=lambda row: (row[3], row[5]))
        headers = ["Key", "Summary", "Type", "Status", "Link", "Created", "Updated"]
        df = pd.DataFrame(issue_data, columns=headers)

        # CSS for centering the DataFrame
        css = """
        <style>
            /* Center the entire dataframe container */
            .stDataFrame { 
                display: flex; 
                justify-content: center; 
            }

            /* Center the internal table */
            div[data-testid="stTable"] {
                display: flex;
                justify-content: center;
                width: 100%;
            }

            /* Ensure the table is centered and properly formatted */
            table {
                width: auto; /* Adjust width dynamically */
                margin: 0 auto; /* Center horizontally */
                table-layout: fixed;
            }

            th, td {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                text-align: center;
            }
        </style>
        """

        # Apply CSS
        st.markdown(css, unsafe_allow_html=True)

        # Display the DataFrame
        st.dataframe(df)

        # Custom CSS to center the button
        st.markdown(
            """
            <style>
                .center-button {
                    display: flex;
                    justify-content: center;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Create a container to center the button
        col1, col2, col3 = st.columns([2, 1, 2])  # Adjust column width ratios
        with col2:  # Center column
            if st.button("Clear Output", key="restart_button"):
                st.rerun()

    else:
        return


if __name__ == "__main__":
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    main()