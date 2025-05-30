import pandas as pd

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.smols.smol_functions import valid_smiles

# OpenAD tools
from openad_tools.output import output_success, output_error, output_table
from openad_tools.jupyter import save_df_as_csv, jup_display_input_molecule

# Plugin
from openad_plugin_ds.plugin_params import PLUGIN_KEY
from openad_plugin_ds.plugin_msg import msg as plugin_msg

# Deep Search
from deepsearch.chemistry.queries.molecules import MoleculeQuery
from deepsearch.chemistry.queries.molecules import MolQueryType

from deepsearch.chemistry.queries import (
    query_chemistry,
    CompoundsBySubstructure,
    CompoundsBySimilarity,
    CompoundsBySmarts,
    CompoundsIn,
    DocumentsByIds,
    DocumentsHaving,
)


def find_substructure_molecules(cmd_pointer, cmd: dict):
    """
    Search for molecules by substructure, as defined by a smiles string.

    Parameters
    ----------
    cmd_pointer:
        The command pointer object
    cmd: dict
        Parser inputs from pyparsing as a dictionary
    """

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Parse identifier
    smiles = cmd["smiles"][0]
    if not valid_smiles(smiles):
        return output_error(plugin_msg("err_invalid_identifier"))

    # Fetch results from API
    try:
        resp = query_chemistry(api, CompoundsBySubstructure(structure=smiles))
    except Exception as err:  # pylint: disable=broad-exception-caught
        return output_error(plugin_msg("err_deepsearch", err))

    # Parse results
    results_table = []

    for row_obj in resp:
        row = row_obj.model_dump()
        row.pop("persistent_id")
        results_table.append(row)

    # No results found
    if not results_table:
        return output_error(plugin_msg("err_no_substr_mols"))

    # Success
    output_success(
        [
            f"We found <yellow>{len(results_table)}</yellow> molecules that contain the provided substructure",
            f"Input: {smiles}",
        ],
        return_val=False,
        pad_top=1,
    )

    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string

    # Display image of the input molecule in Jupyter Notebook
    if GLOBAL_SETTINGS["display"] == "notebook":
        jup_display_input_molecule(smiles, "smiles")

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
