import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_cache import create_analysis_record, save_result
from openad.smols.smol_functions import canonicalize, valid_smiles

# OpenAD tools
from openad_tools.jupyter import save_df_as_csv, jup_display_input_molecule
from openad_tools.output import output_success, output_error, output_table

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.chemistry.queries import (
    query_chemistry,
    CompoundsBySubstructure,
    CompoundsBySimilarity,
    CompoundsBySmarts,
    CompoundsIn,
    DocumentsByIds,
    DocumentsHaving,
)


def find_patents_containing_molecule(cmd_pointer, cmd: dict):
    """
    Searches for patents that contain mentions of a given molecule.

    Parameters
    ----------
    cmd_pointer
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse identifier
    identifier = cmd["identifier"][0]

    result_type = ""
    resp = None

    # Fetch results from API
    try:
        if not valid_smiles(identifier):
            return output_error(plugin_msg("err_invalid_identifier"))
        else:
            canonical_smiles = canonicalize(identifier)
        resp = query_chemistry(
            api, DocumentsHaving(compounds=CompoundsBySubstructure(structure=canonical_smiles)), limit=20
        )
        # raise Exception("This is a test error")
    except Exception as err:  # pylint: disable=broad-exception-caught
        output_error(plugin_msg("err_deepsearch", err), return_val=False)
        return

    # Compile results
    results_table = []
    for row_obj in resp:
        row = row_obj.model_dump()
        row.pop("persistent_id")
        results_table.append(row)

    # No results found
    # results_table = [] # Keep here for testing
    if not results_table:
        return output_error(plugin_msg("err_no_patents_found", result_type, identifier))

    # Success
    output_success(
        plugin_msg("success_patents_found", len(results_table), result_type, identifier), return_val=False, pad_top=1
    )

    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Save results as analysis records that can be merged
    # with the molecule working set in a follow up comand:
    # `enrich mols with analysis`
    save_result(
        create_analysis_record(
            smiles=identifier,
            toolkit=PLUGIN_KEY,
            function="patents_containing_molecule",
            parameters="",
            results=results_table,
        ),
        cmd_pointer=cmd_pointer,
    )

    # Display image of the input molecule in Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        jup_display_input_molecule(identifier)

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
