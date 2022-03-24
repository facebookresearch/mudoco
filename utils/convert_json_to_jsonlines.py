"""
Copyright (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

Usage
python utils/convert_json_to_jsonlines.py \
    "mudoco_*.json" \
    ./jsonlines_output

The output will be available at ./jsonlines_output
"""

import sys
import glob
import json
from collections import defaultdict
import re
import os

def sanity_check(dialog):
    for idx, turn in enumerate(dialog["turns"]):
        if turn["number"] - 1 != idx:
            return False
    return True

def get_token_offset(mention, sentences):
    context_sentence = sentences[mention["turn_id"]-1]
    mention_char_start, mention_char_end = mention["span"]["start"], mention["span"]["end"]

    token_offset = sum([len(sent) for sent in sentences[:mention["turn_id"]-1]])
    char_offset = 0
    mention_token_start, mention_token_end = -1, -1

    for token_idx, token in enumerate(context_sentence):
        char_offset += len(token) + 1
        if char_offset > mention_char_start and mention_token_start == -1:
            mention_token_start = token_idx
        if char_offset > mention_char_end and mention_token_end == -1:
            mention_token_end = token_idx
            break

    return token_offset+mention_token_start, token_offset+mention_token_end


if __name__ == "__main__":
    pattern = sys.argv[1]
    output_dir = sys.argv[2]

    in_paths = glob.glob(pattern)
    print(in_paths)

    for path in in_paths:

        fails = []

        with open(path, "r") as fin:
            data = json.load(fin)
            data_out = defaultdict(lambda: [])
            for dialog_id in data["dialogs"]:
                dialog = data["dialogs"][dialog_id]
                if not sanity_check(dialog):
                    print("Sanity check failed for", dialog_id)
                    fails.append(dialog_id)
                    continue

                split, turns = dialog["split"], dialog["turns"]

                sentences, speakers, clusters = [], [], []

                sample = {
                    "doc_key": str(dialog_id),
                    "sentences": [],
                    "speakers": [],
                    "clusters": []
                }

                for turn in turns:
                    sentence = re.sub(" +", " ", turn["utterance"]).strip().split(" ")
                    speaker = ["user" if turn["number"] % 2 == 1 else "system" for _ in sentence]
                    sentences.append(sentence)
                    speakers.append(speaker)

                print(sentences)

                coref_group_idx = 0
                mention_to_coref_idx = {}
                coref_idx_to_mentions = {}

                for idx, turn in enumerate(turns):
                    sentence = sentences[idx]
                    for link in turn["links"]:
                        if len(link) == 1: # single mention
                            mention = link[0]
                            mention_offset_start, mention_offset_end = get_token_offset(mention, sentences)
                            mention_offset = (mention_offset_start, mention_offset_end)
                            if not mention_offset in mention_to_coref_idx:
                                mention_to_coref_idx[mention_offset] = coref_group_idx
                                coref_idx_to_mentions[coref_group_idx] = []
                                coref_group_idx += 1
                            if not mention_offset in coref_idx_to_mentions[mention_to_coref_idx[mention_offset]]:
                                coref_idx_to_mentions[mention_to_coref_idx[mention_offset]].append(mention_offset)
                        elif len(link) == 2: # pair of mention
                            first_mention, second_mention = link[0], link[1]

                            first_token_offset_start, first_token_offset_end = get_token_offset(first_mention, sentences)
                            second_token_offset_start, second_token_offset_end = get_token_offset(second_mention, sentences)

                            first_mention_offset = (first_token_offset_start, first_token_offset_end)
                            second_mention_offset= (second_token_offset_start, second_token_offset_end)

                            if first_mention_offset in mention_to_coref_idx:
                                mention_to_coref_idx[second_mention_offset] = mention_to_coref_idx[first_mention_offset]
                            elif second_mention_offset in mention_to_coref_idx:
                                mention_to_coref_idx[first_mention_offset] = mention_to_coref_idx[second_mention_offset]
                            else:
                                mention_to_coref_idx[first_mention_offset] = coref_group_idx
                                mention_to_coref_idx[second_mention_offset] = coref_group_idx
                                coref_idx_to_mentions[coref_group_idx] = []
                                coref_group_idx += 1

                            if not first_mention_offset in coref_idx_to_mentions[mention_to_coref_idx[first_mention_offset]]:
                                coref_idx_to_mentions[mention_to_coref_idx[first_mention_offset]].append(first_mention_offset)
                            if not second_mention_offset in coref_idx_to_mentions[mention_to_coref_idx[second_mention_offset]]:
                                coref_idx_to_mentions[mention_to_coref_idx[second_mention_offset]].append(second_mention_offset)

                            print(first_mention, second_mention)
                            print(first_mention_offset, second_mention_offset)
                            print(mention_to_coref_idx)
                            print(coref_idx_to_mentions)
                            print("======")

                        else:
                            print("len links not = 1 or 2 at ", dialog_id, idx)
                            continue

                sample["sentences"] = sentences
                sample["speakers"] = speakers
                sample["clusters"] = list(coref_idx_to_mentions.values())

                flatten_tokens = []
                for sent in sample["sentences"]:
                    for token in sent:
                        flatten_tokens.append(f"{token} ({len(flatten_tokens)})")
                print("SENTENCES", flatten_tokens)
                print("CLUSTERS", sample["clusters"])
                print()
                print("\n\n------------------------\n\n")

                data_out[split].append(sample)


            os.makedirs(output_dir, exist_ok=True)
            for split in ["train", "eval", "test"]:
                with open(os.path.join(output_dir, f"{path}.{split}.jsonlines"), "w") as fout:
                    for sample in data_out[split]:
                        json.dump(sample, fout)
                        fout.write("\n")

            print(f"Failed {len(fails)}/{len(data['dialogs'])} at {path}")
            print(fails)
