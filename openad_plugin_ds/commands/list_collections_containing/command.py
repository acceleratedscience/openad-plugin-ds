import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_grammar_def import str_quoted, clause_save_as
from openad_plugin_ds.plugin_grammar_def import l_ist, collections, containing
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.list_collections_containing.list_collections_containing import (
    list_collections_containing,
)
from openad_plugin_ds.commands.list_collections_containing.description import description

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """List collections containing..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Collections"
        self.index = 2
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: l_ist, grammar_help: l_ist):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.Word(PLUGIN_NAMESPACE)
                + l_ist
                + collections
                + containing
                + str_quoted("search_query")
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"""{PLUGIN_NAMESPACE} list collections containing '<search_query>' [ save as '<filename.csv>' ]""",
                description=description,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        # Login
        login(cmd_pointer)

        # Execute
        cmd = parser.as_dict()
        return list_collections_containing(cmd_pointer, cmd)
