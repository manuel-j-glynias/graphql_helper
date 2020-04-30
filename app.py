from flask import Flask
from flask_cors import CORS
import graphql_utils
from informatics_utils import create_hgnc_gene_name_dict

app = Flask(__name__)
CORS(app)

# server: str = 'localhost'
server: str = '165.227.89.140'
editor_ids: dict = graphql_utils.get_editor_ids(server)
authors_dict: dict = graphql_utils.get_authors(server)
reference_dict: dict = graphql_utils.get_literature_references(server)
journals_dict: dict = graphql_utils.get_journals(server)
jax_gene_dict:dict = graphql_utils.get_jax_gene_ids(server)
auto_user_id: str = graphql_utils.get_editor_id('loader', server)
hgnc_gene_name_dict = create_hgnc_gene_name_dict()

@app.route('/new_gene/<string:gene_name>', methods=['GET'])
def new_gene(gene_name):
    id = graphql_utils.get_omnigene_ID_by_name(gene_name,server)
    if id==None:
        curation_item = {'gene': gene_name, 'description': None, 'oncogenic_category': None, 'synonmyms': None}
        s = graphql_utils.create_omni_gene(gene_name, curation_item, editor_ids, jax_gene_dict,
                                           graphql_utils.PMID_extractor,
                                           graphql_utils.PubMed_extractor, reference_dict, journals_dict,
                                           authors_dict,
                                           hgnc_gene_name_dict)
        print(s)
        if s != '':
            m = graphql_utils.send_mutation(s,server)
            if gene_name in hgnc_gene_name_dict:
                gene_name = hgnc_gene_name_dict[gene_name]
            id = graphql_utils.get_omnigene_ID_by_name(gene_name,server)

    data:dict = {'result_id':id, 'result_name':  gene_name}
    return data


@app.route('/reference_preflight/<string:ref_string>', methods=['GET'])
def reference_preflight(ref_string:str):

    reference_string, s = graphql_utils.handle_references(authors_dict, journals_dict, reference_dict, ref_string.split(','))
    # print(s)
    if s != '':
        m = graphql_utils.send_mutation(s,server)
        # print(m)
    reference_string = reference_string.replace('[','')
    reference_string = reference_string.replace(']','')
    reference_string = reference_string.replace('"','')
    reference_string = reference_string.replace('\\','')
    print(reference_string)
    pmid_array:list = []
    for ref in reference_string.split(','):
        if ref != '':
         pmid_array.append(ref)

    data:dict = {'result':'success','refs':pmid_array}
    return data



if __name__ == '__main__':
    app.run()
