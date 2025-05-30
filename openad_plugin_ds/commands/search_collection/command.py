import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_tools.grammar_def import str_strict_or_quoted, clause_using, clause_save_as
from openad_plugin_ds.plugin_grammar_def import (
    search,
    f_or,
    collection,
    clause_show,
    clause_estimate_only,
)
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.search_collection.search_collection import search_collection
from openad_plugin_ds.commands.search_collection.description import description

# Login
from openad_plugin_ds.plugin_login import login

command = f"""{PLUGIN_NAMESPACE} search collection '<collection_name_or_key>' for '<search_query>'
    [ USING (<parameter>=<value> <parameter>=<value>) ] [ show (data | docs | data docs) ]
    [ estimate only ] [ save as '<filename.csv>' ]"""


class PluginCommand:
    """Search collection..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Collections"
        self.index = 4
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # BACKWARD COMPATIBILITY WITH TOOLKIT COMMAND
        # -------------------------------------------
        # Support for deprecated [ return as data ] clause
        clause_return_as_data = py.Optional(
            py.CaselessKeyword("return") + py.CaselessKeyword("as") + py.CaselessKeyword("data")
        )("return_as_data")
        # -------------------------------------------

        # Command definition
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + search
                + collection
                + str_strict_or_quoted("collection_name_or_key")
                + f_or
                + str_strict_or_quoted("search_query")
                + clause_using
                + clause_show
                + clause_estimate_only
                # BACKWARD COMPATIBILITY WITH TOOLKIT COMMAND
                # -------------------------------------------
                # Support for deprecated [ return as data ] clause
                + clause_return_as_data
                # -------------------------------------------
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=command,
                description=description,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        # Login
        login(cmd_pointer)

        # Execute
        cmd = parser.as_dict()
        return search_collection(cmd_pointer, cmd)
