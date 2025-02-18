from pathlib import Path
import pandas as pd
from io import StringIO
import streamlit as st
from schema import EndpointTechnology, Triple
from components.init import init
from components.menu import menu
from components.dialog_confirmation import dialog_confirmation
import requests
import lib.state as state
from lib.sparql_base import insert
from lib.prefixes import is_prefix

all_file_formats = ['Turtle (.ttl)', 'Spreadsheet (.csv)']
all_file_types = ['ttl', 'csv']


def format_filename(filename: str) -> str:
    """Transform a filename in a usable title in the page"""
    name = filename[0:filename.rindex(".")] # Remove extension
    name = name.replace("-", " ").replace("_", " ")  # Replace separators
    return name.title()


def __get_import_url(graph_uri: str = ""):

    technology = endpoint.technology
    endpoint_url = endpoint.url

    # Allegrograph endpoint
    if technology == EndpointTechnology.ALLEGROGRAPH:
        
        # If in the Allegrograph endpoint, there is the trailing '/sparql', remove it: 
        # import does not work on this URL
        allegrograph_base_url = endpoint_url.replace('/sparql', '')

        # In a dedicated graph, create the correct URL
        if graph_uri: 
            graph_uri = graph_uri.replace('base:', endpoint.base_uri)
            # Make the graph URI URL compatible
            graph_uri = '%3C' + graph_uri.replace(':', '%3A').replace('/', '%2F') + '%3E'

            # Create and return  the import URL
            url = f"{allegrograph_base_url}/statements?context={graph_uri}"
        else: 
            # If it is in the default graph, nothing is needed to do
            url = f"{allegrograph_base_url}/statements"

        return url
    
    elif technology == EndpointTechnology.FUSEKI:
        # If it is a Fuseki endpoint
        if graph_uri:
            graph_uri = graph_uri.replace('base:', 'http://geovistory.org/information/')
            return f"{endpoint_url}?graph={graph_uri}"
        else: 
            return endpoint_url


def __upload_turtle_file(ttl_data: str, graph_uri: str):

    # Upload
    url = __get_import_url(graph_uri)
    headers = {"Content-Type": "text/turtle"}
    authentication = (endpoint.username, endpoint.password)
    response = requests.post(url, data=ttl_data, headers=headers, auth=authentication)

    # Check response
    if response.status_code >= 400:
        st.error(f"Failed to upload file. Status code: {response.status_code}. Reason: {response.reason}. Message: {response.text}.")
        return 'error'
    else:
        # We clear the cache, because it needs to refetch the needed information: 
        # If for example, imported data is the model, we need to fetch it on next occasion
        # Which won't happen if the cache is not cleared.
        st.cache_data.clear()

    state.set_toast('Data inserted', ':material/file_upload:')



def __upload_spreadsheet_file(csv_data: str, graph_uri: str):

    df = pd.read_csv(StringIO(csv_data))

    # Prepare all the triples to be imported
    triples = []
    for _, row in df.iterrows():
        # Get the URI of the entity
        uri = row['uri']
        # For each properties available
        for col in df.columns:
            # Do not do anything with the uri
            if col == 'uri': continue
            # If the cell is empty, skip
            if pd.isna(row[col]) or row[col] is None or row[col] == '': continue
            # Extract the property URI from the column name, and save it as a triple
            property_uri = col[:col.index('_') if '_' in col else len(col)]

            # Is the range a URI or a literal?
            if (':' in row[col] and is_prefix(row[col][:row[col].index(':')])) or row[col].startswith('http://'):
                triples.append(Triple(uri, property_uri, row[col]))
            else:
                triples.append(Triple(uri, property_uri, f"'{row[col]}'"))

    insert(triples, graph_uri)

    state.set_toast('Data inserted', ':material/file_upload:')



##### The page #####

init()
menu()

# From state
endpoint = state.get_endpoint()
all_graphs = state.get_graphs()

# Title
st.title("Import")
st.text('')

# Can't import anything if there is no endpoint
if not endpoint:

    st.warning('You need to select an endpoint first (menu on the left).')

else:

    graphs_labels = [graph.label for graph in all_graphs]
    tab_data, tab_ontologies = st.tabs(['Data', 'Ontologies'])

    ### TAB DATA ### 
    
    tab_data.text('')
    col1, col2 = tab_data.columns([1, 1])

    # Graph selection
    graph_label = col1.selectbox('Select the graph', options=graphs_labels, index=None, key='import-data-graph-selection')  

    # Fetch the graph
    if graph_label:
        graph_index = graphs_labels.index(graph_label)
        selected_graph = all_graphs[graph_index]

    # File format selection
    format = col2.selectbox('Select the file format', options=all_file_formats, disabled=(graph_label is None))
    if format:
        format_index = all_file_formats.index(format)
        file_type = all_file_types[format_index]

    # File uploader
    file = tab_data.file_uploader(f"Load your {format} file:", type=[file_type], disabled=(format is None or graph_label is None))
    tab_data.text('')

    # Explaination for the user, in order to build a specific table
    if file_type == 'csv':
        st.markdown('## Tip:')
        st.markdown("""
                    To make the CSV import work, you will need to provide a specific format. 
                    In short, you should provide one table per class, and all triples in it should be outgoing.
                    If you would like to import incoming statements, you should then have a table for the domain class.
        """)
        st.markdown('Separator is comma.')
        st.markdown("""
                    Also, the content of the file itself should have a specific format.
                    First of all, there should be a column named `uri` (generally the first column).
                    Then each other column name should be like `rdfs:label_has-name`: 
                    first the property as a uri, followed by an underscore, and then you're free to put the name you want.
                    If, for some lines you do not have all the properties, no problem, just let an empty string of None instead.
        """)
        st.markdown('**Example of CSV to import person instances:**')
        st.markdown('`my-persons.csv`')
        st.dataframe(pd.DataFrame(data=[
            {'uri':'base:1234', 'rdfs:type':'crm:E21', 'rdfs:label_name':'John Doe', 'rdfs:comment_description':'Unknown person', 'sdh:P23_gender':'base:SAHIIne'},
            {'uri':'base:1235', 'rdfs:type':'crm:E21', 'rdfs:label_name':'Jeane Doe', 'rdfs:comment_description':'Unknown person', 'sdh:P23_gender':None},
            {'uri':'base:1236', 'rdfs:type':'crm:E21', 'rdfs:label_name':'Albert', 'rdfs:comment_description':'King of some country', 'sdh:P23_gender':'base:SAHIIne'},
        ]), use_container_width=True, hide_index=True)

    # If everything is ready for the TTL import
    if graph_label and format and file and file_type == 'ttl' and tab_data.button('Upload Turtle file', icon=':material/upload:'):
        dialog_confirmation(
            f'You are about to upload **{file.name.upper()}** into **{graph_label.upper()}**.', 
            callback=__upload_turtle_file, 
            ttl_data=file.read().decode("utf-8"),
            graph_uri=selected_graph.uri
        )

    # If everything is ready for the CSV import
    if graph_label and format and file and file_type == 'csv' and tab_data.button('Upload Spreadsheet', icon=':material/upload:'):
        dialog_confirmation(
            f'You are about to upload **{file.name.upper()}** into **{graph_label.upper()}**.', 
            callback=__upload_spreadsheet_file, 
            csv_data=file.read().decode("utf-8"),
            graph_uri=selected_graph.uri
        )


    ### TAB ONTOLOGIES ###
    
    tab_data.text('')

    # Loop through all ontologies files
    folder = Path('./ontologies')
    files = [{ 'name': format_filename(f.name), 'path': f.name } for f in folder.iterdir()]
    onto_names = [file['name'] for file in files]
    onto_paths = [file['path'] for file in files]
    
    # Graph selection
    has_onto_graph = endpoint.ontology_uri != ''
    if has_onto_graph:
        selected_graph_uri = endpoint.ontology_uri
    else:
        graph_label = tab_ontologies.selectbox('Select the graph', options=graphs_labels, index=None, key='import-ontology-graph-selection')  

        # Fetch the graph
        if graph_label:
            graph_index = graphs_labels.index(graph_label)
            selected_graph_uri = all_graphs[graph_index].uri

    # Ontology selection
    ontology_name = tab_ontologies.selectbox('Choose an ontology', options=onto_names, index=None)
    if ontology_name:
        onto_index = onto_names.index(ontology_name)
        onto_path = './ontologies/' + onto_paths[onto_index]
        f = open(onto_path, 'r')
        file_content = f.read()
        f.close()
        tab_ontologies.text('')

        if file_content and tab_ontologies.button('Upload ontology', icon=':material/upload:'):
            dialog_confirmation(
                f'You are about to upload the ontology named **{ontology_name.upper()}** into **{selected_graph_uri}**.', 
                callback=__upload_turtle_file, 
                ttl_data=file_content,
                graph_uri=selected_graph_uri
            )

