import os
from dotenv import load_dotenv

load_dotenv(".env")

CLIENT_ID = os.environ.get("CLIENT_ID") # Application (client) ID of app registration

CLIENT_SECRET = os.environ.get("CLIENT_SECRET") # Placeholder - for use ONLY during testing.
# In a production app, we recommend you use a more secure method of storing your secret,
# like Azure Key Vault. Or, use an environment variable as described in Flask's documentation:
# https://flask.palletsprojects.com/en/1.1.x/config/#configuring-from-environment-variables
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# if not CLIENT_SECRET:
#     raise ValueError("Need to define CLIENT_SECRET environment variable")

#Username used to get Azure token for Graph API
USERNAME = os.environ.get("USERNAME")

#Password for given username
PASSWORD = os.environ.get("PASSWORD")

# AUTHORITY = "https://login.microsoftonline.com/common"  # For multi-tenant app
AUTHORITY = os.environ.get("AUTHORITY")

REDIRECT_PATH = os.environ.get("REDIRECT_PATH")  # Used for forming an absolute URL to your redirect URI.
# The absolute URL must match the redirect URI you set
# in the app's registration in the Azure portal.

#Testing token!!!
AZURE_TOKEN_URL = os.environ.get("AZURE_TOKEN_URL")

AZURE_AUTH_URL = os.environ.get("AZURE_AUTH_URL")

# You can find more Microsoft Graph API endpoints from Graph Explorer
# https://developer.microsoft.com/en-us/graph/graph-explorer
ENDPOINT1 = os.environ.get("ENDPOINT1")  # This resource requires no admin consent

# Fetch all groups in organization
ENDPOINT_GROUPS = os.environ.get("ENDPOINT_GROUPS")

ENDPOINT = os.environ.get("ENDPOINT")  # This resource requires no admin consent
# ENDPOINT = os.environ.get("ENDPOINT_CAL")  # This resource requires no admin consent
# ENDPOINT2 = os.environ.get("ENDPOINT2_CAL")  # This resource requires no admin consent
ENDPOINT2 = os.environ.get("ENDPOINT2")
# ENDPOINT = os.environ.get("ENDPOINT_CAL_ST_ET")  # This resource requires no admin consent

ENDPOINT3 = "https://graph.microsoft.com/beta/me/presence"

# You can find the proper permission names from this document
# https://docs.microsoft.com/en-us/graph/permissions-reference
SCOPE = ["User.ReadBasic.All", "User.Read", "https://graph.microsoft.com/User.Read",
         "https://graph.microsoft.com/User.ReadBasic.All", "https://graph.microsoft.com/Calendars.Read"]

SESSION_TYPE = "filesystem"  # Specifies the token cache should be stored in server-side session