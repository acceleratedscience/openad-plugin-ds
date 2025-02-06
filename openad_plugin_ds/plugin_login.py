"""Login procedure for the Deep Search plugin"""

import os
import jwt
import time
import requests
import deepsearch as ds
from datetime import datetime, timezone

# OpenAD
from openad.helpers.credentials import load_credentials, get_credentials, write_credentials

# OpenAD tools
from openad_tools.helpers import confirm_prompt
from openad_tools.output import output_text, output_error, output_warning, output_success

# Plugin
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY

DEFAULT_URL = "https://sds.app.accelerate.science/"
API_CONFIG_BLANK = {
    "host": "None",
    "auth": {"username": "None", "api_key": "None"},
    "verify_ssl": "False",
}


def login(cmd_pointer, print_success=False):
    """
    OpenAD login to Deep Search

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    """

    # Check for existing credentials
    cred_file = os.path.expanduser(f"{cmd_pointer.home_dir}/deepsearch_api.cred")
    if not os.path.isfile(cred_file):
        login_reset = True
    else:
        login_reset = False

    # For debugging
    # print("$$", PLUGIN_KEY, cmd_pointer.login_settings)

    # First-time login
    first_login = False
    if PLUGIN_KEY not in cmd_pointer.login_settings["toolkits"]:
        cmd_pointer.login_settings["toolkits"].append(PLUGIN_KEY)
        cmd_pointer.login_settings["toolkits_details"].append({"type": "config_file", "session": "handle"})
        cmd_pointer.login_settings["toolkits_api"].append(None)
        cmd_pointer.login_settings["client"].append(None)
        cmd_pointer.login_settings["expiry"].append(None)
        # Note: session_vars are used by RXN but have to be added here too to prevent error in RXN.
        # Storing of login credentials should be reworked so both plugins don't depend on one another.
        cmd_pointer.login_settings["session_vars"].append({})
        i = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        first_login = True

    # Previously logged in - check if the token is still valid
    elif login_reset is False:
        now = datetime.now(timezone.utc)
        i = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        now = datetime.timestamp(now)
        expiry_time = cmd_pointer.login_settings["expiry"][i]

        # Success, already lopgged in
        if expiry_time is not None and expiry_time > now:
            if print_success:
                print_login_status(None, expiry_time)
            return

    # Get login credentials
    try:
        cred_config = _get_creds(cred_file, cmd_pointer)
    except Exception:  # pylint: disable=broad-except
        return False, None

    # Validate credentials input
    if cred_config["host"].strip() == "" or cred_config["host"].strip() == "None":
        cred_config["host"] = DEFAULT_URL
    if _uri_valid(cred_config["host"]) is False:
        output_error("Invalid host, try again", return_val=False)
        return False, None
    if cred_config["auth"]["username"].strip() == "":
        output_error("Invalid username, try again", return_val=False)
        return False, None
    if cred_config["auth"]["api_key"].strip() == "":
        output_error("Invalid API key, try again", return_val=False)
        return False, None

    # Login
    try:
        # Define login API
        config = ds.DeepSearchConfig(host=cred_config["host"], verify_ssl=False, auth=cred_config["auth"])
        client = ds.CpsApiClient(config)
        api = ds.CpsApi(client)

        # Store login API
        i = cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)
        cmd_pointer.login_settings["toolkits_api"][i] = api
        cmd_pointer.login_settings["client"][i] = client

        # Decode jwt token
        cb = client.bearer_token_auth
        bearer = cb.bearer_token
        decoded_token = jwt.decode(bearer, options={"verify_at_hash": False, "verify_signature": False}, verify=False)

        # Extract & store expiry time from token payload
        expiry_time = decoded_token["exp"]
        cmd_pointer.login_settings["expiry"][i] = expiry_time

        # Print login success message
        if login_reset is True or first_login is True:
            username = cred_config["auth"]["username"]
            print_login_status(username, expiry_time)

        return

    # Login fail
    except Exception as err:  # pylint: disable=broad-exception-caught
        username = cred_config["auth"]["username"]
        output_error([f"Failed to log in to {PLUGIN_NAME} as <reset>{username}</reset>", err], return_val=False)
        if confirm_prompt("Reset credentials?"):
            reset_login(cmd_pointer, False)
        return


def reset_login(cmd_pointer, print_feedback=True):
    """Remove the deepsearch credentials file"""

    cred_path = os.path.expanduser(f"{cmd_pointer.home_dir}/deepsearch_api.cred")
    success = False
    if os.path.isfile(cred_path):
        os.remove(cred_path)
        if print_feedback:
            output_success(f"You are logged out from {PLUGIN_NAME}", return_val=False)
        success = True
    else:
        if print_feedback:
            output_warning("No login credentials found", return_val=False)

    # Log back in
    prompt_msg = "Would you like to log in again?" if success else "Would you like to log in?"
    if confirm_prompt(prompt_msg):
        login(cmd_pointer)


def _uri_valid(url: str) -> bool:
    """Check if a URI is valid"""
    try:
        request = requests.get(url, stream=True, timeout=10)
    except:  # pylint: disable=bare-except
        return False
    if request.status_code == 200:
        return True
    else:
        return False


def _get_creds(cred_file, cmd_pointer):
    """
    Return existing login credentials or prompt for new ones.
    """

    api_config = load_credentials(cred_file)
    if api_config is None:
        output_text(
            "\n".join(
                [
                    f"<h1>{PLUGIN_NAME} Authentication</h1>",
                    "To obtain your API key, visit:",
                    "<link>ds4sd.github.io</link>",
                    "",
                    "For instructions, visit:",
                    "<link>github.com/acceleratedscience/openad-plugin-ds#login</link>",
                ]
            ),
            return_val=False,
            pad=2,
        )

        output_warning(
            [f"Please provide your {PLUGIN_NAME} credentials", f"Leave this blank to use the default: {DEFAULT_URL}"],
            return_val=False,
        )
        api_config = API_CONFIG_BLANK.copy()
        api_config = get_credentials(
            cmd_pointer=cmd_pointer, credentials=api_config, creds_to_set=["host", "auth:username", "auth:api_key"]
        )
        write_credentials(api_config, cred_file)
    return api_config


def print_login_status(username, expiry_time):
    msg = (
        f"You are now logged in to {PLUGIN_NAME} as <reset>{username}</reset>"
        if username
        else f"You are already logged in to {PLUGIN_NAME}"
    )
    output_success(
        [
            msg,
            f"Token expires {_expiration_str(expiry_time)}",
        ],
        return_val=False,
    )


def _date_str(timestamp):
    """Convert timestamp to human-readable time"""
    return time.strftime("%a %b %d, %Y at %H:%M", time.localtime(timestamp))


def _expiration_str(expiry_time):
    """
    Get the duration until the token expires.

    Returns:
    on Jan 1, 2025 at 00:00
        if expiry_time > 10 days in the future
    in 5 days, 3 hours and 2 minutes
        if expiry_time < 10 days in the future
    """
    now = datetime.now(timezone.utc)
    now = datetime.timestamp(now)
    time_difference = expiry_time - now + 30  # Add 30 seconds to round up
    output = []

    # More than 10 days in the future: return date
    if time_difference > 86400:
        date_str = _date_str(expiry_time)
        return f"on {date_str}"

    # Less than 10 days in the future: return remaining time
    else:
        # Calculate the number of days
        days, remainder = divmod(time_difference, 86400)  # 86400 seconds in a day
        if days > 0:
            output.append(f"{int(days)} days")

        # Calculate the number of hours
        hours, remainder = divmod(remainder, 3600)  # 3600 seconds in an hour
        if hours > 0:
            output.append(f"{int(hours)} hours")

        # Calculate the number of minutes
        minutes, seconds = divmod(remainder, 60)  # 60 seconds in a minute
        minutes = round(minutes)

        and_x_mins = f" and {minutes} minutes" if minutes > 0 else ""
        return f"in {', '.join(output)}{and_x_mins}" if output else f"{int(seconds)} seconds"
