import pyparsing as py

# Note: Decided to revert to "search for" instead of "find" but both are supported
search_for = py.MatchFirst([py.CaselessKeyword("find"), py.CaselessKeyword("search for"), py.CaselessKeyword("search")])
similar = py.CaselessKeyword("similar")
to = py.CaselessKeyword("to")

w_ith = py.CaselessKeyword("with")
substructure = py.CaselessKeyword("substructure")

i_n = py.CaselessKeyword("in")
patents = py.CaselessKeyword("patents")
f_rom = py.CaselessKeyword("from")
file = py.CaselessKeyword("file")
l_ist = py.CaselessKeyword("list")
dataframe = py.CaselessKeyword("dataframe")

l_ist = py.CaselessKeyword("list")
a_ll = py.CaselessKeyword("all")
collections = py.CaselessKeyword("collections")
domains = py.CaselessKeyword("domains")

containing = py.CaselessKeyword("containing")
f_or = py.CaselessKeyword("for")
domain = py.CaselessKeyword("domain")

details = py.CaselessKeyword("details")

search = py.CaselessKeyword("search")
collection = py.CaselessKeyword("collection")

save = py.CaselessKeyword("save")
a_s = py.CaselessKeyword("as")

reset = py.CaselessKeyword("reset")
login = py.CaselessKeyword("login")


# Search collection
clause_show = py.Optional(
    py.CaselessKeyword("show").suppress()
    + py.Suppress("(")
    + py.OneOrMore(py.CaselessKeyword("data") | py.CaselessKeyword("docs"))("show")
    + py.Suppress(")")
)
clause_estimate_only = py.Optional(py.CaselessKeyword("estimate").suppress() + py.CaselessKeyword("only").suppress())(
    "estimate_only"
)
