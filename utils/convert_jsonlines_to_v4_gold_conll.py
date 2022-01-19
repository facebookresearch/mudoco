"""
(c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

Usage
python utils/convert_jsonlines_to_v4_gold_conll \
    mudoco_{domain}.jsonlines \
    moduco_{domain}.v4_gold_conll
"""

import sys 
import json 

if __name__ == "__main__":
    fin = open(sys.argv[1],"r",encoding="utf-8")
    fout = open(sys.argv[2],"w",encoding="utf-8")

    coref_id = 1

    for line in fin:
        doc = json.loads(line.replace("\n",""))
        doc_id = doc["doc_key"]

        if "/" in doc_id: # if english document, remove the id from the doc_id
            doc_id = "_".join(doc_id.split("_")[:-1])

        fout.write(f"#begin document ({doc_id}); part 000\n") 

        coref_str_list = []    
        for sentence in doc["sentences"]:
            for token in sentence:
                coref_str_list.append([])
        
        for coref_idx,cluster in enumerate(doc["clusters"]):
            for pair in cluster:
                if pair[0] == pair[1]:
                    coref_str_list[pair[0]].append(f"({coref_idx+1})")
                else:
                    coref_str_list[pair[0]].append(f"({coref_idx+1}")
                    coref_str_list[pair[1]].append(f"{coref_idx+1})")

        real_id = 0
        for sent_id,sentence in enumerate(doc["sentences"]):
            for token_id, token in enumerate(sentence):
                fout.write(f"{doc_id}\t{sent_id}\t{token_id}\t{token}\t-\t-\t-\t-\t-\t-\t*\t*\t*\t")

                if len(coref_str_list[real_id]) == 0:
                    fout.write("-")
                else:
                    fout.write("|".join(coref_str_list[real_id]))
                real_id += 1
                
                fout.write("\n")
            fout.write("\n")
        
        fout.write("#end document\n")
