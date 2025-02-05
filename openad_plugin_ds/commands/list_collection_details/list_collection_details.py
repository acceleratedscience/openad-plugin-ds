import pandas as pd
from datetime import datetime

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS

# OpenAD tools
from openad_tools.helpers import pretty_nr, pretty_date
from openad_tools.output import output_text, output_error

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY


def list_collection_details(cmd_pointer, cmd: dict):
    """
    Displays the details for a given collection.

    Parameters
    ----------
    cmd_pointer : object
        The command pointer object.
    cmd : dict
        The command dictionary.
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Fetch all collections
    try:
        collections = api.elastic.list()
        # raise Exception("This is a test error")
    except Exception as err:  # pylint: disable=broad-exception-caught
        return output_error(plugin_msg("err_deepsearch", err))

    # Find specified collection
    collection = None
    for c in collections:
        if cmd["collection"] == c.name:
            collection = c
            break
        if cmd["collection"] == c.source.index_key:
            collection = c
            break

    # Error
    if not collection:
        return output_error(plugin_msg("err_no_collection_found_by_name", cmd["collection"]))

    # Display results in CLI & Notebook
    if GLOBAL_SETTINGS["display"] != "api":
        print_str = "\n".join(
            [
                f"<h1>{collection.name}</h1>",
                f"{collection.metadata.description}",
                "<soft>---</soft>",
                f"<yellow>Name     </yellow> {collection.name}",
                f"<yellow>Key      </yellow> {collection.source.index_key}",
                f"<yellow>Domain   </yellow> {' / '.join(collection.metadata.domain)}",
                f"<yellow>Type     </yellow> {collection.metadata.type}",
                f"<yellow>Entries  </yellow> {pretty_nr(collection.documents)}",
                f"<yellow>Created  </yellow> {pretty_date(datetime.fromisoformat(collection.metadata.created).timestamp(), 'pretty', include_time=False)}",
            ]
        )
        output_text(print_str, return_val=False, width=80, pad=1)

    # Return data for API
    else:
        print(collection)
        results_table = [
            {
                "Collection Name": collection.name,
                "Collection Key": collection.source.index_key,
                "Description": collection.metadata.description,
                "Domain": " / ".join(collection.metadata.domain),
                "Type": collection.metadata.type,
                "Entries": collection.documents,
                "Created": datetime.fromisoformat(collection.metadata.created).strftime("%Y-%m-%d"),
                "Created timestamp": datetime.timestamp(collection.metadata.created),
            }
        ]
        df = pd.DataFrame(results_table)
        df = df.fillna("")  # Replace NaN with empty string
        return df
