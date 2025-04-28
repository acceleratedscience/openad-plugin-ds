from openad_plugin_ds.plugin_params import CLAUSES

description = f"""Searches for patents that contain mentions of a given molecule. The queried molecule can be described by its SMILES.

{CLAUSES['save_as']}

Examples:
- <cmd>ds search for patents containing molecule CC(C)(c1ccccn1)C(CC(=O)O)Nc1nc(-c2c[nH]c3ncc(Cl)cc23)c(C#N)cc1F</cmd>
- <cmd>ds search for patents containing molecule 'CC(C)(c1ccccn1)C(CC(=O)O)Nc1nc(-c2c[nH]c3ncc(Cl)cc23)c(C#N)cc1F' save as 'patents'</cmd>
"""
