import datetime

from graphql_utils import send_query, fix_author_id, get_reference_from_pmid_by_metapub, create_reference_mutation, \
    create_journal_mutation, create_AddLiteratureReferenceJournal_mutation, get_authors_names, create_author_mutation, \
    create_AddLiteratureReferenceAuthors_mutation, get_omnigene_id_from_entrez_id, createEditableStatement_with_date, \
    get_gene_id_from_entrez_id, create_myGeneInfo_gene, create_uniprot_entry, get_unique_graph_id
from informatics_utils import fetch_gene_id_by_gene_name, fetch_gene_info_by_gene_id, populate_omni_gene


def get_omnigene_ID_by_name(name:str,server:str)->str:
    id:str = None
    query = f''' {{ OmniGene(name: \"{name}\") {{ id, name }} }}'''
    response = send_query(query, server)
    if len(response['data']['OmniGene']) > 0:
        for item in response['data']['OmniGene']:
            id: str = item['id']
            break
    return id




def get_authors(server:str)->dict:
    author_dict: dict = {}
    query = f'{{ Author  {{ id,surname,firstInitial }} }}'
    response = send_query(query, server)
    if len(response['data']['Author'])>0:
        for item in response['data']['Author']:
            id = item['id']
            surname = item['surname']
            first_initial = item['firstInitial']
            key = fix_author_id(surname + '_' + first_initial)
            author_dict[key] = id
    return author_dict


def get_literature_references(server:str)->dict:
    reference_dict: dict = {}
    query = f'{{ LiteratureReference  {{ id,PMID }} }}'
    response = send_query(query, server)
    if len(response['data']['LiteratureReference'])>0:
        for item in response['data']['LiteratureReference']:
            id = item['id']
            pmid = item['PMID']
            reference_dict[pmid] = id
    return reference_dict


def get_journals(server:str)->dict:
    journal_dict: dict = {}
    query = f'{{ Journal  {{ id,name }} }}'
    response = send_query(query, server)
    if len(response['data']['Journal'])>0:
        for item in response['data']['Journal']:
            id = item['id']
            name = item['name']
            journal_dict[name] = id
    return journal_dict


def handle_references(author_dict, journal_dict, reference_dict, pmid_array):
    s = ''
    reference_string = '['
    for pubmed in pmid_array:
        if pubmed not in reference_dict:
            r = get_reference_from_pmid_by_metapub(pubmed)
            ref_id = 'ref_' + pubmed
            s += create_reference_mutation(ref_id, r)
            reference_dict[pubmed] = ref_id
            journal = r['journal']
            if journal not in journal_dict:
                journal_id = 'journal_' + fix_author_id(journal)
                s += create_journal_mutation(journal, journal_id)
                journal_dict[journal] = journal_id
            else:
                journal_id = journal_dict[journal]
            s += create_AddLiteratureReferenceJournal_mutation(ref_id, journal_id)
            authors = []
            for author in r['authors']:
                first, surname = get_authors_names(author)
                key = fix_author_id(surname + '_' + first)
                if key not in author_dict:
                    author_id = 'author_' + surname + '_' + first
                    author_id = fix_author_id(author_id)
                    s += create_author_mutation(author_id, surname, first)
                    author_dict[key] = author_id
                else:
                    author_id = author_dict[key]
                authors.append(author_id)
            s += create_AddLiteratureReferenceAuthors_mutation(ref_id, authors)
        else:
            ref_id = reference_dict[pubmed]
        reference_string += '\\"' + ref_id + '\\",'
    reference_string += ']'
    return reference_string, s

# createEditableSynonymList(
# editDate: String!
# field: String!
# id: ID!
# list: [String]!): String
def createEditableSynonymList(gene_name:str, field:str, editor_id:str) -> (str,str):
    now = datetime.datetime.now()
    edit_date:str = now.strftime("%Y-%m-%d-%H-%M-%S")
    id:str = get_unique_graph_id('esl_')
    ede_id:str = get_unique_graph_id('esle_')

    s = f'''{id} : createEditableStringList(editDate: \\"{edit_date}\\", field: \\"{field}\\", id: \\"{id}\\", stringList:[\\"{gene_name}\\"] ),'''
    s += f'{ede_id}: addEditableStringListEditor(editor:[\\"{editor_id}\\"], id:\\"{id}\\" ),'
    return s, id

def create_new_omniGene(omni_gene:dict, jax_gene_dict:dict, curation_item:dict, editor_ids:dict,pmid_extractor:callable, reference_dict:dict, journal_dict:dict, author_dict:dict)->(str,str,str,str):
    id = get_omnigene_id_from_entrez_id(omni_gene['entrez_gene_id'])
    gene: str = omni_gene['symbol']
    panel_name = omni_gene['panel_name']
    s = f'{id}: createOmniGene(id: \\"{id}\\", name: \\"{gene}\\", panelName:\\"{panel_name}\\" ),'

    # create geneDescription EditableStatement
    field1: str = 'geneDescription_' + id
    gene_description = '(Insert Gene Description)'
    editor_id = editor_ids['loader']
    # edit_date: str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")

    statement1: str = gene_description
    (m, id1) = createEditableStatement_with_date(statement1,field1,editor_id,datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),pmid_extractor, reference_dict, journal_dict, author_dict)
    s += m
    s += f'addOmniGeneGeneDescription(geneDescription:[\\"{id1}\\"], id:\\"{id}\\" ),'

    statement2 = 'Neither'

        # create OncogenicCategory EditableStatement
    field2: str = 'OncogenicCategory_' + id
    (m, id2) = createEditableStatement_with_date(statement2,field2,editor_id,datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),pmid_extractor, reference_dict, journal_dict, author_dict)
    s += m
    s += f'addOmniGeneOncogenicCategory(id:\\"{id}\\", oncogenicCategory:[\\"{id2}\\"] ),'

    canonicalTranscript = ''
    ct_field = 'canonicalTranscript_' + id
    (m, id3) = createEditableStatement_with_date(canonicalTranscript, ct_field, editor_id, datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"), pmid_extractor, reference_dict, journal_dict, author_dict)
    s += m
    s += f'addOmniGeneTranscript(id:\\"{id}\\", transcript:[\\"{id3}\\"] ),'


    field4: str = 'synonyms_omnigene_' + id
    (m, id4) = createEditableSynonymList(gene, field4, editor_id)
    s += m
    s += f'addOmniGeneSynonyms(id:\\"{id}\\", synonyms:[\\"{id4}\\"] ),'

    if gene in jax_gene_dict:
        jaxGene = jax_gene_dict[gene]
        s += f'addOmniGeneJaxGene(id:\\"{id}\\", jaxGene:[\\"{jaxGene}\\"] ),'
    else:
        print("no jax gene for ",gene)
# addOmniGeneMyGeneInfoGene(id: ID!myGeneInfoGene: [ID!]!): String
# Adds MyGeneInfoGene to OmniGene entity
    myGeneInfoGene = get_gene_id_from_entrez_id(omni_gene['entrez_gene_id'])
    s += f'addOmniGeneMyGeneInfoGene(id:\\"{id}\\", myGeneInfoGene:[\\"{myGeneInfoGene}\\"] ),'

    # addOmniGeneUniprot_entry(id: ID!uniprot_entry: [ID!]!): String
    # Adds Uniprot_entry to OmniGene entity
    if 'sp_info' in omni_gene:
        uniprot_id:str = omni_gene['sp_info']['id']
        s += f'addOmniGeneUniprotEntry(id:\\"{id}\\", uniprotEntry:[\\"{uniprot_id}\\"] ),'

    return s, id, id2, id3

def create_omni_gene(gene_name:str, curation_item:dict, editor_ids:dict,jax_gene_dict,pmid_extractor:callable,sp_pmid_extractor:callable, reference_dict:dict,journal_dict:dict,author_dict:dict,hgnc_gene_name_dict)->str:
    omni_gene: dict = {
        'symbol': gene_name,
        'panel_name': gene_name
    }
    if gene_name in hgnc_gene_name_dict:
        omni_gene['panel_name'] = gene_name
        omni_gene['synonym'] = gene_name
        gene_name = hgnc_gene_name_dict[gene_name]
        omni_gene['symbol'] = gene_name
    entrez_gene_id = fetch_gene_id_by_gene_name(gene_name)
    omni_gene['entrez_gene_id'] = entrez_gene_id
    editor_id = editor_ids['loader']
    if entrez_gene_id is None:
        print("no entrz gene id for", gene_name)
    else:
        gene_info = fetch_gene_info_by_gene_id(entrez_gene_id)
        populate_omni_gene(gene_info, omni_gene)
        print(omni_gene)
        s = create_myGeneInfo_gene(omni_gene,editor_id,pmid_extractor,reference_dict,journal_dict,author_dict)
        s += create_uniprot_entry(omni_gene,editor_id,sp_pmid_extractor,reference_dict,journal_dict,author_dict)
        m, omnigene_id, cat_id, syn_id = create_new_omniGene(omni_gene,jax_gene_dict,curation_item,editor_ids,pmid_extractor,reference_dict,journal_dict,author_dict)
        s += m
        return s


