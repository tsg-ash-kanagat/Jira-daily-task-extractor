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

# Load environment variables
load_dotenv()
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_USERNAME = os.getenv('JIRA_USERNAME')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY') or "INFRAARCH"
START_DATE_FIELD_ID = "created"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezones
LOCAL_TZ = get_localzone()
TOKYO_TZ = pytz.timezone('Asia/Tokyo')

# Connect to JIRA
try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    logger.debug(f"Connected to JIRA at {JIRA_SERVER}")
except JIRAError as e:
    logger.error(f"JIRA connection error: {e}")
    st.error(f"JIRA connection error: {e}")
    st.stop()

# Streamlit configuration
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>JIRA Task Viewer</h1>", unsafe_allow_html=True)

# Center input field
st.markdown(
    """
    <style>
        .stTextInput>label { display: flex; justify-content: center; font-size: 16px; font-weight: bold; }
        .stTextInput>div>div>input { text-align: center; }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    date_str = st.text_input("Enter start date (MM/DD/YYYY, empty for 3 months ago):", key="date_input")

col4, col5, col6 = st.columns([1, 0.1, 1])
with col5:
    submitted = st.button("✔", key="submit_button")
with col6:
    cancelled = st.button("X", key="cancel_button")


def get_date_input(local_tz):
    if cancelled:
        st.markdown(
            """
            <style>
                .center-text { text-align: center; font-size: 20px; font-weight: bold; }
            </style>
            <div class="center-text">Application cancelled. Please close this tab.</div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<script>window.close();</script>", unsafe_allow_html=True)
        st.stop()

    if submitted:
        if not date_str:
            return {'date': (datetime.now(local_tz) - timedelta(days=90)).date(), 'submitted': True}
        try:
            return {'date': datetime.strptime(date_str, '%m/%d/%Y').date(), 'submitted': True}
        except ValueError:
            st.error("Invalid date format. Use MM/DD/YYYY.")
    return {'date': None, 'submitted': False}


def fetch_all_issues_since(start_date):
    if start_date is None:
        return []
    jql_query = f'assignee = currentUser() AND {START_DATE_FIELD_ID} >= "{start_date.strftime("%Y-%m-%d")}" AND status != "Done" ORDER BY {START_DATE_FIELD_ID} ASC'
    try:
        return jira.search_issues(jql_query, maxResults=False)
    except JIRAError as e:
        logger.error(f"JIRA error fetching issues: {e}")
        st.error(f"JIRA error fetching issues: {e}")
        return []


def format_issue_info(issue):
    try:
        return {
            'summary': issue.fields.summary,
            'type': issue.fields.issuetype.name,
            'link': f"<a href='{JIRA_SERVER}/browse/{issue.key}' target='_blank'>{issue.key}</a>",
            'created': datetime.strptime(issue.fields.created, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M'),
            'updated': datetime.strptime(issue.fields.updated, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M'),
            'status': issue.fields.status.name,
        }
    except AttributeError as e:
        logger.warning(f"Missing field in issue {issue.key}: {e}")
        st.warning(f"Missing field in issue {issue.key}: {e}")
        return {}


def main():
    date_info = get_date_input(LOCAL_TZ)
    if date_info['submitted']:
        st.empty()
        start_date = date_info['date'] or (datetime.now(LOCAL_TZ) - timedelta(days=90)).date()
        issues = fetch_all_issues_since(start_date)
        if not issues:
            st.info("No issues found.")
            return

        issue_data = [format_issue_info(issue) for issue in issues if format_issue_info(issue)]
        issue_data.sort(key=lambda row: (row['status'], row['created']))
        df = pd.DataFrame(issue_data, columns=["link", "summary", "type", "status", "created", "updated"])

        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.markdown(
            """
            <style>
                .center-button { display: flex; justify-content: center; }
            </style>
            """,
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("Clear Output", key="restart_button"):
                st.rerun()


if __name__ == "__main__":
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    main()