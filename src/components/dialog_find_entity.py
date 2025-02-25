import streamlit as st
from lib.sparql_queries import find_entities, get_ontology
import lib.state as state


@st.dialog('Find an entity', width='large')
def dialog_find_entity() -> None:
    """Dialog function to allow user to find an entity and select it."""
    
    # From state
    graph = state.get_graph()

    ontology = get_ontology()

    # All entity filters:
    col1, col2, col3 = st.columns([2, 2, 1])
    # Class filter
    classes_labels = list(map(lambda cls: cls.display_label , ontology.classes))
    class_label = col1.selectbox('Entity is instance of class:', options=classes_labels, index=None)
    # Label filter
    entity_label = col2.text_input('Entity label contains:', help='Write the entity label (or a part of it) and hit "Enter"')
    # Retrieved entities
    limit = col3.selectbox('Number to retrieve:', options=[10, 20, 50, 100])

    # Find the selected entity from the selected label
    if class_label:
        class_index = classes_labels.index(class_label)
        selected_class_uri = ontology.classes[class_index].uri
    else:
        selected_class_uri = None

    st.divider()    

    # Fetch the entities
    entities = find_entities(
        graph=graph,
        label_filter=entity_label if entity_label else None,
        class_filter=selected_class_uri,
        limit=limit
    )

    # Set the state selected entity as being the one chosen
    for i, entity in enumerate(entities):
        if st.button(entity.display_label_comment, type='tertiary', key=f'dlg-find-entity-{i}'):
            state.set_entity(entity)
            st.switch_page("pages/entity.py")

