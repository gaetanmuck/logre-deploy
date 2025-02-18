from typing import Literal
from schema import Prefix, EndpointTechnology
import lib.state as state

prefixes = [
    Prefix(short='xsd', url='http://www.w3.org/2001/XMLSchema#'),
    Prefix(short='rdf', url='http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
    Prefix(short='rdfs', url='http://www.w3.org/2000/01/rdf-schema#'),
    Prefix(short='owl', url='http://www.w3.org/2002/07/owl#'),
    Prefix(short='sh', url='http://www.w3.org/ns/shacl#'),
    Prefix(short='crm', url='http://www.cidoc-crm.org/cidoc-crm/'),
    Prefix(short='sdh', url='https://sdhss.org/ontology/core/'),
    Prefix(short='sdh-shortcut', url='https://sdhss.org/ontology/shortcuts/'),
    Prefix(short='sdh-shacl', url='https://sdhss.org/shacl/profiles/'),
    Prefix(short='ontome', url='https://ontome.net/ontology/'),
]


def get_prefixes_str(format: Literal['sparql', 'turtle'] = 'sparql') -> str:
    """
    Transform the list of prefixes into a valid SPARQL.
    Done to avoid to put manually all prefixes everywhere.
    """
    # Add the dynamic one (base)
    all_prefixes = prefixes + [Prefix(short='base', url=state.get_endpoint().base_uri)]

    # Transform to list of string
    prefixes_str = list(map(lambda p: p.to_sparql() if format == 'sparql' else p.to_turtle(), all_prefixes))

    import streamlit as st

    # In case we are in Allegrograph, we would like to shortcut the default graph behavior of Allegrograph
    endpoint_technology = state.get_endpoint().technology
    if endpoint_technology == EndpointTechnology.ALLEGROGRAPH or endpoint_technology.value == EndpointTechnology.ALLEGROGRAPH.value:
        franz_rdf = Prefix(short='franzOption_defaultDatasetBehavior', url='franz:rdf')
        if format == 'sparql': prefixes_str = [franz_rdf.to_sparql()] + prefixes_str

    # Transform into a single string
    return '\n'.join(prefixes_str)


def shorten_uri(uri: str) -> str:
    """
    Replace all long URIs by its short prefix.
    Usefull to display in the GUI.
    """

    # Add the dynamic one (base)
    all_prefixes = prefixes + [Prefix(short='base', url=state.get_endpoint().base_uri)]
    
    for prefix in all_prefixes:
        uri = prefix.shorten(uri)
    return uri

def explicits_uri(uri: str) -> str:
    """
    Replace the short URIs by its explicit version.
    Usefull to display in the GUI.
    """

    # Add the dynamic one (base)
    all_prefixes = prefixes + [Prefix(short='base', url=state.get_endpoint().base_uri)]
    
    for prefix in all_prefixes:
        uri = prefix.explicit(uri)
    return uri

def is_prefix(supposed_prefix: str) -> bool:
    """Check if the given supposed prefix is listed as a prefix."""

    found = [prefix for prefix in prefixes if prefix.short == supposed_prefix]
    return len(found) == 0