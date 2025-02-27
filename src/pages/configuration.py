import os
from enum import Enum
import streamlit as st
from schema import Triple, Endpoint, Graph, Prefix
from lib.sparql_base import delete
from lib.sparql_queries import count_graph_triples
from lib.utils import readable_number, ensure_uri
from lib.configuration import save_config, unload_config, CONFIG_PATH
import lib.state as state
from components.init import init
from components.menu import menu
from components.dialog_confirmation import dialog_confirmation
from components.dialog_download import dialog_download_graph, dialog_dump_endpoint
from components.dialog_config_endpoint import dialog_config_endpoint
from components.dialog_config_graph import dialog_config_graph
from components.dialog_config_prefix import dialog_config_prefix


def __delete_endpoint(endpoint: Endpoint) -> None:
    """Delete the specified endpoint"""

    # Delete endpoint from state
    state.delete_endpoint(endpoint)

    # Save config if local
    if os.getenv('ENV') != 'streamlit':
        save_config()

    # Close confirmation window and reload the page with new state
    state.set_toast('Endpoint removed', icon=':material/delete:')
    st.rerun()


def __prune_graph(graph: Graph) -> None:
    """Delete all statements of a given graph"""

    graph_uri = ensure_uri(graph.uri)

    # The delete "where clause" triple: delete all triples from the graph
    triple = Triple('?s', '?p', '?o')
    delete(triple, graph=graph_uri)

    # If the graph is not the default one
    if graph.uri:
        # Also, from the default graph, delete all predicates related to the graph (label, comment, ...)
        triple = Triple(graph_uri, '?p', '?o')
        delete(triple)

    state.clear_graphs()
    state.set_toast('Graph deleted', icon=':material/delete:')
    st.rerun()


def __delete_prefix(prefix: Prefix) -> None:
    """Delete the specified endpoint"""

    # Delete endpoint from state
    state.delete_prefix(prefix)

    # Save config if local
    if os.getenv('ENV') != 'streamlit':
        save_config()

    # Close confirmation window and reload the page with new state
    state.set_toast('Prefix removed', icon=':material/delete:')
    st.rerun()


def __show_endpoint_list() -> None:
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    st.session_state['display_endpoint_list'] = True


def __hide_endpoint_list() -> None:
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    st.session_state['display_endpoint_list'] = False


def __endpoint_list() -> None:

    # If endpoint list is deactivated, display nothing
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    if 'display_endpoint_list'not in st.session_state or not st.session_state['display_endpoint_list']:
        return

    # Fetch from state
    all_endpoints = state.get_endpoints()

    # Display all saved endpoints
    for i, endpoint in enumerate(all_endpoints):

        # For some reason, sometimes, especially on hot reload, Enums are lost.
        # Maybe its my fault, by I can't find the reason why after some clicking around, the enums are lost
        # This is the way I found to make it work every time
        technology = endpoint.technology.value if isinstance(endpoint.technology, Enum) else endpoint.technology
        ontology_framework = endpoint.ontology_framework.value if isinstance(endpoint.ontology_framework, Enum) else endpoint.ontology_framework

        # Display all information from the endpoint as disabled inputs
        col1, col2 = st.columns([6, 13], vertical_alignment='center')
        col1.text_input('Name', value=endpoint.name, key=f"config-endpoint-name-{i}", disabled=True)
        col2.text_input('URL', value=endpoint.url, key=f"config-endpoint-url-{i}", disabled=True)
        col1, col2, col3 = st.columns([6, 6, 7], vertical_alignment='center')
        col1.text_input('Username', value=endpoint.username, key=f"config-endpoint-username-{i}", disabled=True)
        col2.text_input('Password', value=endpoint.password, key=f"config-endpoint-password-{i}", type='password', disabled=True)
        col3.text_input('Endpoint technology', value=technology, key=f"config-endpoint-technology-{i}", disabled=True)
        col1, col2, col3 = st.columns([8, 5, 5], vertical_alignment='center')
        col1.text_input('Base URI', value=endpoint.base_uri, key=f"config-endpoint-base-uri-{i}", disabled=True)
        col2.text_input('Ontology graph URI', value=endpoint.ontology_uri, key=f"config-endpoint-ontology-graph-uri-{i}", disabled=True)
        col3.text_input('Ontology Framework', value=ontology_framework, key=f"config-endpoint-ontology-framework-{i}", disabled=True)

        st.text('')
        
        col1, col2, col3 = st.columns([3, 3, 2])

        # Button to delete an endpoint
        if col1.button(f'Remove this endpoint', key=f"config-endpoint-delete-{i}", icon=':material/delete:'):
            dialog_confirmation(f"You are about to delete \"{endpoint.name}\" endpoint.", __delete_endpoint, endpoint=endpoint)

        # Button to edit an endpoint
        if col2.button(f'Edit this endpoint', key=f"config-endpoint-edit-{i}", icon=":material/edit:"):
            dialog_config_endpoint(endpoint, i)

        # Divider between endpoints
        col1, col2, col3 = st.columns([3, 7, 3], vertical_alignment='center')
        col2.divider()


def __show_graph_list() -> None:
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    st.session_state['display_graph_list'] = True


def __hide_graph_list() -> None:
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    st.session_state['display_graph_list'] = False


def __graph_list() -> None:

    # If graph list is deactivated, display nothing
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    if 'display_graph_list'not in st.session_state or not st.session_state['display_graph_list']:
        return

    # Fetch from state
    all_graphs = state.get_graphs()

    # Display all graphs in sessions
    for i, graph in enumerate(all_graphs):
        st.text('')
        col1, col2, col3, col4, col5 = st.columns([3, 2, 4, 1, 1], vertical_alignment='center')
        col1.markdown(graph.label)
        col2.markdown(f"{readable_number(count_graph_triples(graph))} triples")
        col3.markdown(graph.comment)

        # Button to cleanse a graph
        if col4.button('', key=f"config-graph-delete-{i}", icon=":material/delete:", help='From the endpoint, this will remove all triples of this graph, but also information about the graph in others. Resulting in making the graph fully disapear.', type='tertiary'):
            dialog_confirmation(f'You are about to delete the graph "{graph.label}" and all its triples.', __prune_graph, graph=graph)

        # Button to download a graph
        if col5.button('', key=f"config-graph-download-csv-{i}", icon=":material/download:", type='tertiary'):
            dialog_download_graph(graph)


def __show_prefix_list() -> None:
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    st.session_state['display_prefix_list'] = True


def __hide_prefix_list() -> None:
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    st.session_state['display_prefix_list'] = False


def __prefix_list() -> None:

    # If graph list is deactivated, display nothing
    # Here, because it is only for here and for display information
    # We took the liberty of handling the session_state directly
    if 'display_prefix_list'not in st.session_state or not st.session_state['display_prefix_list']:
        return
    
    # Fetch from state
    all_prefixes = state.get_prefixes()

    # Display all graphs in sessions
    for i, prefix in enumerate(all_prefixes):
        st.text('')
        col1, col2, col3, col4 = st.columns([2, 7, 1, 1], vertical_alignment='center')
        col1.markdown(prefix.short)
        col2.markdown(prefix.url)

        # Button to cleanse a graph
        if col3.button('', key=f"config-prefix-delete-{i}", icon=":material/delete:", help='This will delete this prefix from your configuration.', type='tertiary'):
            dialog_confirmation(f'You are about to delete this prefix from your configuration.', __delete_prefix, prefix=prefix)




##### The page #####

init()
menu()

# From state
endpoint = state.get_endpoint()


### CONFIGURATION ###

col1, col2 = st.columns([6, 2], vertical_alignment='bottom')
col1.title("Endpoint configuration")
col2.download_button(
    label='Download', 
    data=unload_config(), 
    disabled=os.getenv('ENV') != 'streamlit',
    file_name=CONFIG_PATH,
    help='Download this configuration as a toml file. If Logre is running locally, it will be updated automatically.',
    icon=':material/download:'
)

st.divider()


### ENDPOINTS ###

col1, col2, col3, col4 = st.columns([4, 1, 1, 2], vertical_alignment='bottom')
col1.markdown('### Endpoints')

col2.button('Show', on_click=__show_endpoint_list, icon=':material/visibility:', key='config-btn-show-endpoints', type='tertiary')
col3.button('Hide', on_click=__hide_endpoint_list, icon=':material/visibility_off:', key='config-btn-hide-endpoints', type='tertiary')
col4.button('Add new', on_click=dialog_config_endpoint, icon=':material/add:', key='config-btn-add-endpoint')

__endpoint_list()

st.divider()


### GRAPHS ###

# Only display graph section if an endpoint is selected:
# can't fetch information from nowhere
if endpoint:

    # Title and boxes for graph actions (show/hide graph list)
    col1, col_dump, col2, col3, col4 = st.columns([2, 2, 1, 1, 2], vertical_alignment='bottom')
    col1.markdown('### Graphs')

    col_dump.button('Dump', icon=":material/download_2:", on_click=dialog_dump_endpoint, type='tertiary')
    col2.button('Show', on_click=__show_graph_list, icon=':material/visibility:', key='config-btn-show-graphs', type='tertiary')
    col3.button('Hide', on_click=__hide_graph_list, icon=':material/visibility_off:', key='config-btn-hide-graphs', type='tertiary')
    col4.button('Add new', on_click=dialog_config_graph, icon=':material/add:', key='config-btn-add-graph')

    __graph_list()

    st.divider()


### PREFIXES ###


# Title and boxes for graph actions (show/hide graph list)
col1, col_dump, col2, col3, col4 = st.columns([2, 2, 1, 1, 2], vertical_alignment='bottom')
col1.markdown('### Prefixes')

col2.button('Show', on_click=__show_prefix_list, icon=':material/visibility:', key='config-btn-show-prefixes', type='tertiary')
col3.button('Hide', on_click=__hide_prefix_list, icon=':material/visibility_off:', key='config-btn-hide-prefixes', type='tertiary')
col4.button('Add new', on_click=dialog_config_prefix, icon=':material/add:', key='config-btn-add-prefix')

__prefix_list()

st.divider()