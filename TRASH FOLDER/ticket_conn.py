import streamlit as st
import requests
from msal import PublicClientApplication

CLIENT_ID = "4eab6de9-7b10-453d-b10c-393bf9f90376"
TENANT_ID = "3ec84e8f-8c1d-4ecc-a417-006e622c2a1d"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read", "Mail.Read"]

app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
else:
    result = app.acquire_token_interactive(SCOPES)

if "access_token" in result:
    headers = {"Authorization": f"Bearer {result['access_token']}"}
    response = requests.get("https://graph.microsoft.com/v1.0/me/messages?$top=5", headers=headers)

    if response.status_code == 200:
        emails = response.json().get("value", [])
        st.title("📬 Your Emails")
        for email in emails:
            st.subheader(email["subject"])
            st.write(email["bodyPreview"])
    else:
        st.error("Failed to fetch emails.")
else:
    st.error("Authentication failed.")
