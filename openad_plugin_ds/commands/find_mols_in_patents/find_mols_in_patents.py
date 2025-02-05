import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS

# OpenAD tools
from openad_tools.jupyter import save_df_as_csv, col_from_df, csv_to_df
from openad_tools.output import output_error, output_table, output_success, output_warning


from deepsearch.chemistry.queries import (
    query_chemistry,
    CompoundsBySubstructure,
    CompoundsBySimilarity,
    CompoundsBySmarts,
    CompoundsIn,
    DocumentsByIds,
    DocumentsHaving,
)

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.chemistry.queries.molecules import MoleculesInPatentsQuery


def find_molecules_in_patents(cmd_pointer, cmd: dict):
    """
    Search for mentions of a given molecules in a list of patents.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse a list of patent ids from the input
    patent_id_list = None
    if "list" in cmd:
        patent_id_list = cmd["list"]
    elif "filename" in cmd or "df_name" in cmd:
        try:
            if "filename" in cmd:
                df = csv_to_df(cmd_pointer, cmd["filename"])
            else:
                df = cmd_pointer.api_variables[cmd["df_name"]]

            df.columns = df.columns.str.lower()
            patent_id_list = col_from_df(df, "patent id")
            if not patent_id_list:
                patent_id_list = col_from_df(df, "patent_id")
            if not patent_id_list:
                patent_id_list = col_from_df(df, "patentid")
            if not patent_id_list:
                raise ValueError("No patent ID column found (patent id, patent_id, patentid)")
            # raise FileNotFoundError("This is a test error")
            # raise Exception("This is a test error")
        except FileNotFoundError:
            return output_error(plugin_msg("err_file_not_found", cmd["filename"]))
        except Exception as err:  # pylint: disable=broad-exception-caught
            src_type = "file" if "filename" in cmd else "dataframe"
            return output_error([plugin_msg("err_no_patent_ids_found", src_type), err])

    # Empty list
    if not patent_id_list:
        return

    # Fetch results from API
    try:

        resp = query_chemistry(api, CompoundsIn(documents=DocumentsByIds(publication_ids=patent_id_list)), limit=20)

        # raise Exception('This is a test error')
    except Exception as err:  # pylint: disable=broad-except
        return output_error(plugin_msg("err_deepsearch", err))

    # Compile results
    results_table = []
    for row_obj in resp:
        row = row_obj.model_dump()
        row.pop("persistent_id")
        results_table.append(row)

    # List of patent IDs to print
    patent_list_output = "\n<reset>- " + "\n- ".join(patent_id_list) + "</reset>"

    # No results found
    if not results_table:
        output_warning(
            "No molecules found in the provided patents." + patent_list_output,
            return_val=False,
            pad_top=1,
        )
        return

    # Success
    output_success(
        f"We found {len(results_table)} molecules mentioned in the following patents:" + patent_list_output,
        return_val=False,
        pad_top=1,
    )

    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Display results in CLI & Notebook
    if GLOBAL_SETTINGS["display"] != "api":
        output_table(df, return_val=False)

    # Save results to file (prints success message)
    if "save_as" in cmd:
        results_file = str(cmd["results_file"])
        save_df_as_csv(cmd_pointer, df, results_file)

    # Return data for API
    if GLOBAL_SETTINGS["display"] == "api":
        return df
