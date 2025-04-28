import os
import pyparsing as py

# OpenAD
from openad.core.help import help_dict_create_v2

# Plugin
from openad_tools.grammar_def import str_quoted, list_quoted, clause_save_as
from openad_plugin_ds.plugin_grammar_def import l_ist, collections, f_or, domain, domains
from openad_plugin_ds.plugin_params import PLUGIN_NAME, PLUGIN_KEY, PLUGIN_NAMESPACE
from openad_plugin_ds.commands.list_collections_for_domain.list_collections_for_domain import (
    list_collections_for_domain,
)
from openad_plugin_ds.commands.list_collections_for_domain.description import description

# Login
from openad_plugin_ds.plugin_login import login


class PluginCommand:
    """Display collections for domain..."""

    category: str  # Category of command
    index: int  # Order in help
    name: str  # Name of command = command dir name
    parser_id: str  # Internal unique identifier

    def __init__(self):
        self.category = "Collections"
        self.index = 2
        self.name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.parser_id = f"plugin_{PLUGIN_KEY}_{self.name}"

    def add_grammar(self, statements: list, grammar_help: list):
        """Create the command definition & documentation"""

        # Command definition
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + l_ist
                + collections
                + f_or
                + (domain | domains)
                + (str_quoted("domain") | list_quoted("domain_list"))
                + clause_save_as
            )(self.parser_id)
        )

        # BACKWARD COMPATIBILITY WITH TOOLKIT COMMAND
        # -------------------------------------------
        # Original command:
        #   - display collections for domain '<domain_name>'
        #   - display collections in domains from list ['<domain_name>',...]
        # New command:
        #   - ds list collections for domain '<domain_name>'
        # To be forwarded:
        #   - [ ds ] display collections for domain '<domain_name>'
        statements.append(
            py.Forward(
                py.CaselessKeyword(PLUGIN_NAMESPACE)
                + py.CaselessKeyword("display")
                + collections
                + py.MatchFirst(
                    [(f_or + domain), (py.CaselessKeyword("in") + domains + py.CaselessKeyword("from") + l_ist)]
                )
                + (str_quoted("domain") | list_quoted("domain_list"))
                + clause_save_as
            )(self.parser_id)
        )

        # Command help
        grammar_help.append(
            help_dict_create_v2(
                plugin_name=PLUGIN_NAME,
                plugin_namespace=PLUGIN_NAMESPACE,
                category=self.category,
                command=[
                    f"""{PLUGIN_NAMESPACE} list collections for domain '<domain_name>' [ save as '<filename.csv>' ]""",
                    f"""{PLUGIN_NAMESPACE} list collections for domains ['<domain_name>','<domain_name>',...] [ save as '<filename.csv>' ]""",
                ],
                description=description,
            )
        )

    def exec_command(self, cmd_pointer, parser):
        """Execute the command"""

        # Login
        login(cmd_pointer)

        # Execute
        cmd = parser.as_dict()
        return list_collections_for_domain(cmd_pointer, cmd)
