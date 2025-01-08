import os
import yaml


# Load metadata from file
plugin_metadata = {}
try:
    metadata_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_metadata.yaml")
    with open(metadata_file, "r", encoding="utf-8") as f:
        plugin_metadata = yaml.safe_load(f)
except Exception:  # pylint: disable=broad-except
    pass


PLUGIN_NAME = plugin_metadata.get("name")
PLUGIN_KEY = PLUGIN_NAME.lower().replace(" ", "_")
PLUGIN_NAMESPACE = plugin_metadata.get("namespace")
CLAUSES = {
    # "using": "Note: The <cmd>USING</cmd> clause requires all enclosed parameters to be defined in the same order as listed below.",
    # "using": "Note: All enclosed parameters should be defined in the same order as listed below.",
    "save_as": "Use the <cmd>save as</cmd> clause to save the results as a csv file in your current workspace.",
    "list_collections": "Run <cmd>list all collections</cmd> to list available collections.",
    "list_domains": "Use the command <cmd>list all collections</cmd> to find available domains.",
}
