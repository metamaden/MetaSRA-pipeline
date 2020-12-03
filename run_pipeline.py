########################################################################
#
# Run the ontology mapping pipeline on a set of key-value pairs 
# that describe a biological sample
#
########################################################################

from optparse import OptionParser
import json
from sets import Set
import sys
import os
reload(sys)
sys.setdefaultencoding("utf-8") # needed for Python 2..
sys.path.append(os.path.join("bktree"))
sys.path.append(os.path.join("map_sra_to_ontology"))
import argparse
from collections import defaultdict, deque
import json
import dill

from os.path import join

import map_sra_to_ontology
from map_sra_to_ontology import ontology_graph
from map_sra_to_ontology import load_ontology
from map_sra_to_ontology import predict_sample_type
from map_sra_to_ontology import config
from map_sra_to_ontology import run_sample_type_predictor
from predict_sample_type.learn_classifier import *
from map_sra_to_ontology import pipeline_components as pc

# additional imports
from timeit import default_timer
import argparse

def main():
    # add main args to parse
    parser = argparse.ArgumentParser(description='Arguments for run_pipeline.py')
    parser.add_argument("--fnvread", type=str, required=True,
        default=None, help='Paths of files to read, separated with ";".')
    parser.add_argument("--fnvwrite", type=str, required=True,
        default=None, help='Paths of files to write, separated with ";".')
    args = parser.parse_args()
    # start timer
    t1 = default_timer()
    parser = OptionParser()
    # parse args
    print str(args)
    input_fl = args.fnvread.split(";")
    print "detected "+str(len(input_fl))+" files to read"
    # summarize detected files
    input_fl = args.fnvread.split(";")
    print "detected "+str(len(input_fl))+" files to read"
    write_fl = args.fnvwrite.split(";")
    print "detected "+str(len(write_fl))+" files to write"
    tagsl = []
    for infile in input_fl:
        with open(infile, "r") as opf:
            tagsl.append(json.load(opf))
    # ** do main ontology loads outside of main loop
    ont_name_to_ont_id = {
        "UBERON":"12",
        "CL":"1",
        "DOID":"2",
        "EFO":"16",
        "CVCL":"4"}
    ont_id_to_og = {x:load_ontology.load(x)[0] for x in ont_name_to_ont_id.values()}
    pipeline = p_48()
    # do main loop on samples (works for up to 500, then string too long)
    for ii, tag_to_vals in enumerate(tagsl):
        write_f = write_fl[ii]
        # Designate file to write output to
        # Map key-value pairs to ontologies
        pipeline = p_48()
        all_mappings = []
        for tag_to_val in tag_to_vals:
            sample_acc_to_matches = {}
            mapped_terms, real_props = pipeline.run(tag_to_val)
            mappings = {
                "mapped_terms":[x.to_dict() for x in mapped_terms],
                "real_value_properties": [x.to_dict() for x in real_props]
            }
            all_mappings.append(mappings)
        outputs = []
        for tag_to_val, mappings in zip(tag_to_vals, all_mappings):
            outputs.append(
                run_pipeline_on_key_vals(tag_to_val, ont_id_to_og, mappings)
            )
        # use json.dump to stream json to outfile, where fn is second arg
        with open(write_f, 'w') as outfile:
            json.dump(obj = outputs, fp = outfile, indent=4,
                separators=(',', ': ')
                )
        # use json.dumps to return json output as a string, to console
        print json.dumps(outputs, indent=4, separators=(',', ': '))
        print "time elapsed = "+str(default_timer() - t1)



    parser = OptionParser()
    #parser.add_option("-f", "--key_value_file", help="JSON file storing key-value pairs describing sample")
    (options, args) = parser.parse_args()
    input_f = args[0]
    # Designate file to write output to
    if len(args) >1 :
        write_f = args[1]
        with open(input_f, "r") as f:
            tag_to_vals = json.load(f)
    else:
        write_f = str(input_f+".msrap")
        with open(input_f, "r") as f:
            tag_to_vals = json.load(f)
    # Map key-value pairs to ontologies
    # Load ontologies
    ont_name_to_ont_id = {
        "UBERON":"12",
        "CL":"1",
        "DOID":"2",
        "EFO":"16",
        "CVCL":"4"}
    ont_id_to_og = {x:load_ontology.load(x)[0] for x in ont_name_to_ont_id.values()}
    pipeline = p_48()

    all_mappings = []
    for tag_to_val in tag_to_vals:
        sample_acc_to_matches = {}
        mapped_terms, real_props = pipeline.run(tag_to_val)
        mappings = {
            "mapped_terms":[x.to_dict() for x in mapped_terms],
            "real_value_properties": [x.to_dict() for x in real_props]
        }
        all_mappings.append(mappings)

    outputs = []
    for tag_to_val, mappings in zip(tag_to_vals, all_mappings):
        outputs.append(
            run_pipeline_on_key_vals(tag_to_val, ont_id_to_og, mappings)
        )
    # use json.dump to stream json to outfile, where fn is second arg
    if write_f:
        with open(write_f, 'w') as outfile:
            json.dump(obj = outputs, fp = outfile, indent=4, 
                separators=(',', ': ')
                )
    # use json.dumps to return json output as a string, to console
    print json.dumps(outputs, indent=4, separators=(',', ': '))

def run_pipeline_on_key_vals(tag_to_val, ont_id_to_og, mapping_data): 
    
    mapped_terms = []
    real_val_props = []
    for mapped_term_data in mapping_data["mapped_terms"]:
        term_id = mapped_term_data["term_id"]
        for ont in ont_id_to_og.values():
            if term_id in ont.get_mappable_term_ids():
                mapped_terms.append(term_id)
                break
    for real_val_data in mapping_data["real_value_properties"]:
        real_val_prop = {
            "unit_id":real_val_data["unit_id"], 
            "value":real_val_data["value"], 
            "property_id":real_val_data["property_id"]
        }
        real_val_props.append(real_val_prop)

    # Add super-terms of mapped terms to the list of ontology term features   
    sup_terms = Set()
    for og in ont_id_to_og.values():
        for term_id in mapped_terms:
            sup_terms.update(og.recursive_relationship(term_id, ['is_a', 'part_of']))
    mapped_terms = list(sup_terms)

    predicted, confidence = run_sample_type_predictor.run_sample_type_prediction(
        tag_to_val, 
        mapped_terms, 
        real_val_props
    )

    mapping_data = {
        "mapped ontology terms": mapped_terms, 
        "real-value properties": real_val_props, 
        "sample type": predicted, 
        "sample-type confidence": confidence}

    return mapping_data
    #print json.dumps(mapping_data, indent=4, separators=(',', ': '))


#def run_pipeline(tag_to_val, pipeline):
#    pipeline = p_48()
#    sample_acc_to_matches = {}
#    mapped_terms, real_props = pipeline.run(tag_to_val)
#    mappings = {
#        "mapped_terms":[x.to_dict() for x in mapped_terms], 
#        "real_value_properties": [x.to_dict() for x in real_props]
#    }
#    return mappings
    
def p_48():
    spec_lex = pc.SpecialistLexicon(config.specialist_lex_location())
    inflec_var = pc.SPECIALISTLexInflectionalVariants(spec_lex)
    spell_var = pc.SPECIALISTSpellingVariants(spec_lex)
    key_val_filt = pc.KeyValueFilter_Stage()
    init_tokens_stage = pc.InitKeyValueTokens_Stage()
    ngram = pc.NGram_Stage()
    lower_stage = pc.Lowercase_Stage()
    man_at_syn = pc.ManuallyAnnotatedSynonyms_Stage()
    infer_cell_line = pc.InferCellLineTerms_Stage()
    prop_spec_syn = pc.PropertySpecificSynonym_Stage()
    infer_dev_stage = pc.ImpliedDevelopmentalStageFromAge_Stage()
    linked_super = pc.LinkedTermsOfSuperterms_Stage()
    cell_culture = pc.ConsequentCulturedCell_Stage()
    filt_match_priority = pc.FilterOntologyMatchesByPriority_Stage()
    real_val = pc.ExtractRealValue_Stage()
    match_cust_targs = pc.ExactMatchCustomTargets_Stage()
    cust_conseq = pc.CustomConsequentTerms_Stage()
    delimit_plus = pc.Delimit_Stage('+')
    delimit_underscore = pc.Delimit_Stage('_')
    delimit_dash = pc.Delimit_Stage('-')
    delimit_slash = pc.Delimit_Stage('/')
    block_cell_line_key = pc.BlockCellLineNonCellLineKey_Stage()
    subphrase_linked = pc.RemoveSubIntervalOfMatchedBlockAncestralLink_Stage()
    cellline_to_implied_disease = pc.CellLineToImpliedDisease_Stage()
    acr_to_expan = pc.AcronymToExpansion_Stage()
    exact_match = pc.ExactStringMatching_Stage(["1", "2", "4", "5", "7", "8", "9"], query_len_thresh=3)
    fuzzy_match = pc.FuzzyStringMatching_Stage(0.1, query_len_thresh=3)
    two_char_match = pc.TwoCharMappings_Stage()
    time_unit = pc.ParseTimeWithUnit_Stage()

    stages = [
        key_val_filt,
        init_tokens_stage,
        ngram,
        lower_stage,
        delimit_plus,
        delimit_underscore,
        delimit_dash,
        delimit_slash,
        inflec_var,
        spell_var,
        man_at_syn,
        acr_to_expan,
        time_unit,
        exact_match,
        two_char_match,
        prop_spec_syn,
        fuzzy_match,
        match_cust_targs,
        block_cell_line_key,
        linked_super,
        cellline_to_implied_disease,
        subphrase_linked,
        cust_conseq,
        real_val,
        filt_match_priority,
        infer_cell_line,
        infer_dev_stage,
        cell_culture]
    return pc.Pipeline(stages, defaultdict(lambda: 1.0))


if __name__ == "__main__":
    main()



