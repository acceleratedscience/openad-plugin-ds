import re
import os
import json
import base64
import pandas as pd
import urllib.parse
from copy import deepcopy

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.credentials import load_credentials

# OpenAD tools
from openad_tools.style_parser import style, strip_tags
from openad_tools.helpers import confirm_prompt
from openad_tools.jupyter import save_df_as_csv
from openad_tools.pyparsing import parse_using_clause
from openad_tools.output import output_text, output_table, output_error, output_warning

# Plugin
from openad_plugin_ds.plugin_msg import msg as plugin_msg
from openad_plugin_ds.plugin_params import PLUGIN_KEY

# Deep Search
from deepsearch.cps.client.components.elastic import ElasticDataCollectionSource, ElasticProjectDataCollectionSource
from deepsearch.cps.queries import DataQuery

# Aggregations
aggs = {
    "by_year": {
        "date_histogram": {
            "field": "description.publication_date",
            "calendar_interval": "year",
            "format": "yyyy",
            "min_doc_count": 0,
        }
    }
}


def search_collection(cmd_pointer, cmd: dict):
    """
    Search a given collection in the Deep Search repository.

    Parameters
    ----------
    cmd_pointer : object
        The command pointer object.
    cmd : dict
        The command dictionary.
    """

    # TQDM progress bar
    # Note: needs to be imported inside function to recognize notebook display context
    if GLOBAL_SETTINGS["display"] == "notebook":
        from tqdm.notebook import tqdm
    else:
        from tqdm import tqdm

    # Define the DeepSearch API
    api = cmd_pointer.login_settings["toolkits_api"][cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

    # Define the host
    host = _get_host(cmd_pointer)

    # Parse search query
    search_query = cmd["search_query"]
    # print("search_query: ", search_query)

    # Query paremeter defaults
    defaults = {
        "collection_name_or_key": "pubchem",
        "elastic_page_size": 50,  # aka `page_size` (per ds4sd examle and deprecated toolkit command)
        "elastic_id": "default",  # aka `system_id` (per ds4sd examle and deprecated toolkit command)
        "slop": 3,  # aka `edit_distance` (per ds4sd examle and deprecated toolkit command)
        "limit_results": 0,
    }

    # Parse collection key
    collection_name_or_key = (
        cmd["collection_name_or_key"] if "collection_name_or_key" in cmd else defaults["collection_name_or_key"]
    )

    # Parse USING parameters
    params = parse_using_clause(
        cmd.get("using"),
        allowed=[
            "elastic_page_size",
            "page_size",  # Backward compatibilty, maps to "elastic_page_size"
            "elastic_id",
            "system_id",  # Backward compatibilty, maps to "elastic_id"
            "slop",
            "edit_distance",  # Backward compatibilty, maps to "slop"
            "limit_results",
        ],
    )
    elastic_page_size = int(
        params.get("elastic_page_size", defaults["elastic_page_size"])
        or params.get("page_size", defaults["elastic_page_size"])
    )  # Backward compatibilty
    elastic_id = params.get("elastic_id", defaults["elastic_id"]) or params.get(
        "system_id", defaults["elastic_id"]
    )  # Backward compatibilty
    slop = int(
        params.get("slop", defaults["slop"]) or params.get("edit_distance", defaults["slop"])
    )  # Backward compatibilty
    limit_results = int(params.get("limit_results", defaults["limit_results"]))

    # Parse collections
    collections = api.elastic.list()
    collections.sort(key=lambda c: c.name.lower())
    elastic_list = [c.source.elastic_id for c in collections]
    collection_key_list = [c.source.index_key for c in collections]
    collection_name_list = [c.name for c in collections]
    result = [
        {
            "Domain": " / ".join(c.metadata.domain),
            "Collection Name": c.name,
            "Collection Key": c.source.index_key,
            "elastic_id": c.source.elastic_id,
        }
        for c in collections
    ]

    # Translate collection name to collection key
    if collection_name_or_key not in collection_key_list and collection_name_or_key in collection_name_list:
        collection_name_or_key = collection_key_list[collection_name_list.index(collection_name_or_key)]

    # Validate collection key
    if collection_name_or_key not in collection_key_list:
        output_error(plugin_msg("err_invalid_collection_id"), return_val=False)
        collectives = pd.DataFrame(result)
        output_table(collectives, is_data=False, return_val=False)
        return

    # Validate elastic id (currently only default is allowed)
    if elastic_id not in elastic_list:
        output_error(plugin_msg("err_invalid_elastic_id"), return_val=False)
        collectives = pd.DataFrame(result)
        output_table(collectives, is_data=False, return_val=False)
        return

    # Define the data collection to be queried
    data_collection = ElasticDataCollectionSource(elastic_id=elastic_id, index_key=collection_name_or_key)

    # Backward compatibilty - support for "return as data" clause
    return_data = GLOBAL_SETTINGS["display"] == "api" or "return_as_data" in cmd

    # Prepare the data query
    # ----------------------

    # Define fuzziness
    # if slop > 0 or 1: # trash
    search_query = search_query + " ~" + str(slop)

    # Parse show clause
    source_list = []
    is_docs = False
    show = cmd.get("show")
    if show and ("data" in show or "docs" in show):
        if "data" in show:
            source_list.extend(["subject", "attributes", "identifiers"])
        if "docs" in show:
            source_list.extend(["description.title", "description.authors", "file-info.filename", "identifiers"])
            is_docs = True
    else:
        source_list = ["subject", "attributes", "identifiers", "file-info.filename"]

    # Highlight matches
    if is_docs:
        highlight = {"fields": {"*": {}}}
        highlight["fragment_size"] = 0
        if "save_as" in cmd:
            highlight["pre_tags"] = [""]
            highlight["post_tags"] = [""]
        elif return_data:
            highlight["pre_tags"] = [""]
            highlight["post_tags"] = [""]
        elif GLOBAL_SETTINGS["display"] == "notebook":
            highlight["pre_tags"] = ["<span style='font-weight: bold; background-color: #FFFF00'>"]
            highlight["post_tags"] = ["</span>"]
        else:
            highlight["pre_tags"] = ["<green>"]
            highlight["post_tags"] = ["</green>"]
    else:
        highlight = None

    # Define the query
    query = DataQuery(
        search_query,  # The search query
        source=source_list,  # What fields to search
        limit=elastic_page_size,  # The size of each elastic search request page
        highlight=highlight,  # Highlight matches
        coordinates=data_collection,  # The data collection to be queried
        aggregations=aggs,
    )

    # Count the total number of results & estimate pages
    count_query = deepcopy(query)
    count_query.paginated_task.parameters["limit"] = 0
    count_results = api.queries.run(count_query)
    expected_total = count_results.outputs["data_count"]
    expected_pages = (expected_total + elastic_page_size - 1) // elastic_page_size
    output_text("Estimated results: " + str(expected_total), return_val=False)

    # Maybe stop with estimation only
    if "estimate_only" in cmd:
        return None
    else:
        if expected_total > 100 and GLOBAL_SETTINGS["display"] != "api":
            if not confirm_prompt("Your query may take some time, do you wish to proceed?"):
                return None

    # Iterate through all records and save matches.
    # The paginated query cursor is passed to tqdm to display a progress bar.
    all_results = []
    all_aggs = {}
    try:
        cursor = api.queries.run_paginated_query(query)
        # raise Exception("This is a test error")
    except Exception as err:  # pylint: disable=broad-exception-caught
        return output_error(plugin_msg("err_deepsearch", err))
    for result_page in tqdm(
        cursor,
        total=expected_pages,
        bar_format="{l_bar}{bar}",
        leave=False,
        disable=GLOBAL_SETTINGS["display"] == "api",
    ):
        all_results.extend(result_page.outputs["data_outputs"])

        # Count number of results per year
        for year in result_page.outputs["data_aggs"]["by_year"]["buckets"]:
            if year["key_as_string"] not in all_aggs:
                all_aggs[year["key_as_string"]] = 0
            all_aggs[year["key_as_string"]] = all_aggs[year["key_as_string"]] + int(year["doc_count"])

    # Display distribution of results by year
    if is_docs and all_aggs:
        distribution_df = pd.json_normalize(all_aggs)
        distribution_df = distribution_df.style.hide(axis="index")
        if len(distribution_df.columns) > 1:
            output_text("<bold>Result distribution by year</bold>", pad=1, return_val=False)
            output_table(distribution_df, pad_btm=1, is_data=False, return_val=False)

    # Compile results table
    results_table = []
    result = None
    for row in all_results:
        result = {}

        if "description" in row["_source"]:
            if "title" in row["_source"]["description"]:
                result["Title"] = row["_source"]["description"]["title"]
            if "authors" in row["_source"]["description"]:
                result["Authors"] = ",".join([author["name"] for author in row["_source"]["description"]["authors"]])
            if "url_refs" in row["_source"]["description"]:
                result["URLs"] = " , ".join(row["_source"]["description"]["url_refs"])

        # if slop > 0 or 1: # trash:
        for field in row.get("highlight", {}).keys():
            for snippet in row["highlight"][field]:
                result["Snippet"] = re.sub(" +", " ", snippet)

        if "attributes" in row["_source"]:
            for ref in row["_source"]["identifiers"]:
                if ref["type"] == "cid":
                    result["cid"] = ref["value"]
        for ref in row["_source"].get("identifiers", []):
            result[ref["type"]] = ref["value"]

        if "subject" in row["_source"]:
            for ref in row["_source"]["subject"]["identifiers"]:
                if ref["type"] == "smiles":
                    result["SMILES"] = ref["value"]
                if ref["type"] == "echa_ec_number":
                    result["ec_number"] = ref["value"]
                if ref["type"] == "cas_number":
                    result["cas_number"] = ref["value"]
                if ref["type"] == "patentid":
                    result["Patent ID"] = ref["value"]

            for ref in row["_source"]["subject"]["names"]:
                if ref["type"] == "chemical_name":
                    result["chemical_name"] = ref["value"]

        if "identifiers" in row["_source"]:
            for ref in row["_source"]["identifiers"]:
                if ref["type"] == "arxivid":
                    result["arXiv"] = _make_clickable(f'https://arxiv.org/abs/{ref["value"]}', "arXiv")
                    if "arxivid" in result:
                        result.pop("arxivid")
                if ref["type"] == "doi":
                    result["DOI"] = _make_clickable(f'https://doi.org/{ref["value"]}', "DOI")
                    if "doi" in result:
                        result.pop("doi")

        if "_id" in row and GLOBAL_SETTINGS["display"] == "notebook" and not return_data:
            result["DS_URL"] = _make_clickable(_generate_url(host, data_collection, row["_id"]), "DS")

        # if slop > 0 or 1: # trash
        for field in row.get("highlight", {}).keys():
            for snippet in row["highlight"][field]:
                result["Report"] = str(row["_source"]["file-info"]["filename"])
                result["Field"] = field.split(".")[0]

        if "attributes" in row["_source"]:
            for attribute in row["_source"]["attributes"]:
                for predicate in attribute["predicates"]:
                    value = predicate["value"]["name"]
                    if "nominal_value" in predicate:
                        value = predicate["nominal_value"]["value"]
                    elif "numerical_value" in predicate:
                        value = predicate["numerical_value"]["val"]
                    result[predicate["key"]["name"]] = value

        results_table.append(result)

    # No results
    if result is None:
        output_warning("Search returned no result", return_val=False)
        return None

    # Results to dataframe
    pd.set_option("display.max_colwidth", None)
    df = pd.DataFrame(results_table)
    df = df.fillna("")  # Replace NaN with empty string
    if limit_results > 0:
        df = df.truncate(after=limit_results - 1)

    # Save results to file (prints success message)
    if "save_as" in cmd:
        results_file = str(cmd["results_file"])
        save_df_as_csv(cmd_pointer, df, results_file)

    # Display results in CLI & Notebook
    if not return_data:
        # Stylize the table for Jupyter
        if GLOBAL_SETTINGS["display"] == "notebook":
            df = df.style.set_properties(**{"text-align": "left"}).set_table_styles(
                [{"selector": "th", "props": [("text-align", "left")]}]
            )

        # Stylize the table for terminal
        if GLOBAL_SETTINGS["display"] == "terminal":
            if "save_as" not in cmd:
                df.style.format(hyperlinks="html")
                if "Title" in df:
                    df["Title"] = df["Title"].str.wrap(50, break_long_words=True)
                if "Authors" in df:
                    df["Authors"] = df["Authors"].str.wrap(25, break_long_words=True)
                if "Snippet" in df:
                    df["Snippet"] = df["Snippet"].apply(lambda x: style(x))  # pylint: disable=unnecessary-lambda
                    df["Snippet"] = df["Snippet"].str.wrap(70, break_long_words=True)

        return output_table(df, show_index=True)

    # Return data for API
    else:
        # Remove styling tags in the snippets column
        if "Snippet" in df:
            df["Snippet"] = df["Snippet"].apply(lambda x: strip_tags(x))  # pylint: disable=unnecessary-lambda
        return df


def _make_clickable(url, name):
    if GLOBAL_SETTINGS["display"] == "notebook":
        return f'<a href="{url}"  target="_blank"> {name} </a>'
    else:
        return url


def _generate_url(host, data_source, document_hash, item_index=None):
    select_coords = {}
    url = ""
    if isinstance(data_source, ElasticProjectDataCollectionSource):
        proj_key = data_source.proj_key
        index_key = data_source.index_key
        select_coords = {
            "privateCollection": index_key,
        }
        url = f"{host}/projects/{proj_key}/library/private/{index_key}"
    elif isinstance(data_source, ElasticDataCollectionSource):
        # TODO: remove hardcoding of community project
        proj_key = "1234567890abcdefghijklmnopqrstvwyz123456"
        index_key = data_source.index_key
        select_coords = {
            "collections": [index_key],
        }
        url = f"{host}/projects/{proj_key}/library/public"

    hash_expr = f'file-info.document-hash: "{document_hash}"'
    search_query = {
        **select_coords,
        "type": "Document",
        "expression": hash_expr,
        "filters": [],
        "select": [
            "_name",
            "description.collection",
            "prov",
            "description.title",
            "description.publication_date",
            "description.url_refs",
        ],
        "itemIndex": 0,
        "pageSize": 10,
        "searchAfterHistory": [],
        "viewType": "snippets",
        "recordSelection": {
            "record": {
                "id": document_hash,
            },
        },
    }
    if item_index is not None:
        search_query["recordSelection"]["itemIndex"] = item_index

    encoded_query = urllib.parse.quote(
        base64.b64encode(urllib.parse.quote(json.dumps(search_query, separators=(",", ":"))).encode("utf8")).decode(
            "utf8"
        )
    )

    url = f"{url}?search={encoded_query}"

    return url


def _get_host(cmd_pointer):
    cred_file = load_credentials(os.path.expanduser(f"{cmd_pointer.home_dir}/deepsearch_api.cred"))

    if cred_file["host"].strip() == "":
        host = "https://sds.app.accelerate.science"
    else:
        host = cred_file["host"]

    return host.rstrip("/")
