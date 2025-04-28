import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# OpenAD tools
from openad_tools.grammar_def import molecules, molecule_identifier, clause_save_as

# Plugin
from openad_plugin_ds.plugin_grammar_def import search_for, w_ith, substructure
from openad_plugin_ds.commands.find_mols_substruct.description import description
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.find_mols_substruct.find_mols_substruct import find_substructure_molecules

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """Find molecules with substructure..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Molecules"
        self.index = 1
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + search_for
                + molecules
                + w_ith
                + substructure
                + molecule_identifier("smiles")
                + clause_save_as
            )(self.parser_id)
        )

        # BACKWARD COMPATIBILITY WITH TOOLKIT COMMAND
        # -------------------------------------------
        # Original command:
        #   - search for substructure instances of <smiles>
        # New command:
        #   - ds search for molecules with substructure <smiles>
        # To be forwarded:
        #   - [ ds ] search for substructure instances of <smiles>
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + search_for
                + substructure
                + py.CaselessKeyword("instances")
                + py.CaselessKeyword("of")
                + molecule_identifier("smiles")
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=f"{PLUGIN_NAMESPACE} search for molecules with substructure <smiles> [ save as '<filename.csv>' ]",
                description=description,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        # Login
        login(cmd_pointer)

        # Execute
        cmd = parser.as_dict()
        return find_substructure_molecules(cmd_pointer, cmd)
