# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: CC-BY-NC-4.0

from tqdm import tqdm
import penman
import copy
import sys

# This code is used to disrupt AMR. By that we mean, chopping named entities from the anywhere in an utterance.
# Note that if more than one chop is possible, all are completed - but only one per example.
# To illustrate, the sentence "I ate a pear and an orange" would result in two chopped outputs:
# 1) "I ate a UNK and an orange"
# 2) "I ate a pear and an UNK"

# Given an original AMR record, decode it into a penman graph and return it with some additional metadata (for use in the final corpus).
def parseOriginal(stringAMR):
    graph = penman.decode(stringAMR)
    graph.metadata["chop-section"] = "original"
    # Return the cleaned utterance and pased AMR graph.
    return graph.metadata["snt"].replace(".","").replace("?","").strip(), graph

# This function searches the AMR graph for all named entity and date nodes.
def getNameInfo(triples):
    # These are the date node types that we are interested in from the AMR spec.
    timePreds = [":day", ":month", ":year", ":year2"]
    nodes = []
    labels = {}
    # Check every triple in the graph for names and dates.
    for triple in triples:
        if triple[2] == "name":
            nodes.append(triple[0])
        if triple[2] == "date-entity":
            nodes.append(triple[0])

    # Check the graph for every triple that starts with a node we just stored above. If found, extract their string labels.
    for triple in triples:
        if triple[0] in nodes and triple[1].startswith(":op"):
            if triple[0] in labels:
                labels[triple[0]] = labels[triple[0]] + " " + triple[2].replace('"','')
            else:
                labels[triple[0]] = triple[2].replace('"','')
        elif triple[0] in nodes and triple[1] in timePreds:
            if triple[0] in labels:
                labels[triple[0]] = labels[triple[0]] + " " + triple[2].replace('"','')
            else:
                labels[triple[0]] = triple[2].replace('"','')
    
    # Return the list of suitable chop point nodes, and their respective labels.
    return nodes, labels

# This function checks whether the AMR graph can be chopped, and returns the chop node and label if so.
def willItChop(utt, nodes, labels):
    prepUtt = " " + utt + " "
    try:
        # Check whether the utterance contains each node's label.
        for node in nodes:
            # If it does, then return that this graph is truly choppable, and return the node and label at which chopping is possible.
            # Note: find returns -1 if not found.
            if prepUtt.find(" " + labels[node] + " ") != -1:
                return True, node, labels[node]
         # If all nodes are checked and haven't returned True, return False as chopping is not possible.
        return False, None, None
    except KeyError:
        # In case the list of nodes passed is empty, return False.
        return False, None, None

# Given the original graph triples and the node at which to chop them, split the triples into the two new halves.
def chopTriples(triples, node):
    half1 = []
    half2 = []
    for triple in triples:
        # If the triple ends with the node we wish to chop, replace the node with the underspecification (UNK) and store it in the first half of the chopped triples (incomplete utterance).
        if triple[2] == node:
            chopped = (triple[0], triple[1], 'UNK')
            half1.append(chopped)
        # If the triple starts with the node we wish to chop, store the triple in the second half of the chopped triples (the sentence completion).
        elif triple[0] == node:
            half2.append(triple)
        else:
            # Otherwise store every other triple in the first half as it is not what we want to disrupt.
            half1.append(triple)
    # Return both halves.
    return half1, half2

# Given the original graph, split triples, chopped utterance, and new top node if h2 is True.
# Set h2 True if it's the second half (aka the completion or chopped named entity) of the chopped utterance, and False if the first half.
# The graph top must be changed to the given node if h2 is True, otherwise we would be left with a disconnected AMR graph.
def chopGraph(graph, newTriples, utt, h1, node):
    # Copy the original graph to preserve structure that will be unchanged.
    gh = copy.deepcopy(graph)
    # Replace the triples with the new chopped triples.
    gh.triples = newTriples
    # Keep the metadata we need and add extra metadata about chopping.
    gh.metadata = {}
    gh.metadata["id"] = graph.metadata["id"]
    gh.metadata["chop-date"] = "2022-06-29" # TODO update if planning to release new version.
    gh.metadata["chop-section"] = "incomplete"
    gh.metadata["snt"] = utt
    gh.metadata["tok"] = utt
    # Clear graph epidata as no longer valid for the chopped graph.
    gh.epidata = {}

    # If the chopped graph is the completion section, set the 'top' to the new graph root and set the correct chop-section in the metadata.
    if h1:
        gh.top = node
        gh.metadata["chop-section"] = "completion"
    # Return the graph half.
    return gh

# This function receives th original data, and returns the dirsupted utterance and AMR graph.
def chopAMR(utt, graph, node, label):
    # The triples are split on the given node identified in the willItChop function.
    triplesHalf1, triplesHalf2 = chopTriples(graph.triples, node)
    # We add spaces as the label might be at the start or end of the utterance, and replacing without spaces would cause huge errors.
    # For example, replacing "US" with "" would transform "Julius is useless" to "Juli is eless" - hence the spaces are necassary.
    prepUtt = " " + utt + " "
    # The utterance is disrupted by replacing the label with the UNK token (label identified in the willItChop function).
    choppedUtt = prepUtt.replace(" " + label + " ", " UNK ", 1).strip()
    # Using the split triples and chopped utterance, we can generate the chopped graph halves.
    gh1 = chopGraph(graph, triplesHalf1, choppedUtt, False, None)
    gh2 = chopGraph(graph, triplesHalf2, label, True, node)
    return gh1, gh2

# When testing, 'store can be replaced by 'display' in the processRecord function.
def display(original, gh1, gh2):
    try:
        print("_____________________ORIGINAL_____________________")
        print(penman.encode(original))
        print("__________________Chopped Half 1__________________")
        print(penman.encode(gh1))
        print("__________________Chopped Half 2__________________")
        print(penman.encode(gh2))
    except penman.exceptions.LayoutError:
        print("FAILED")
        return

# Store the chopped corpora (note: written in append mode per record).
def store(original, gh1, gh2):
    # Using the provided input AMR path, set the output path to store chopped data.
    try:
        filepath = sys.argv[1]
        outpath = filepath.replace("./input/", "./output/")
    except IndexError:
        print("Please add ./input/filepath.txt after disruptAMR.py")
        sys.exit(1)

    # For later experimentation with different pipelines, we store variations of the chopped data.
    allOutPath = outpath.replace(".txt", "-disrupted-all.txt")
    originalOnlyPath = outpath.replace(".txt", "-disrupted-original.txt")
    choppedOnlyPath = outpath.replace(".txt", "-disrupted-chopped.txt")
    incompleteOnlyPath = outpath.replace(".txt", "-disrupted-incomplete.txt")
    completionOnlyPath = outpath.replace(".txt", "-disrupted-completion.txt")

    # On the odd occasion (rare), our chopped graphs are not valid AMR. We check this with penman.encode before storing.
    try:
        pmoriginal = penman.encode(original)
        pmgh1 = penman.encode(gh1)
        pmgh2 = penman.encode(gh2)
    except penman.exceptions.LayoutError:
        # If the AMR graph is invalid, we simply print "FAILED" and do not store.
        print("FAILED")
        return

    # The 'all' dataset contains the original full AMR graphs, the incomplete underspecified graphs, and the completions.
    with open(allOutPath, "a") as aop:
        aop.write(pmoriginal)
        aop.write("\n\n")
        aop.write(pmgh1)
        aop.write("\n\n")
        aop.write(pmgh2)
        aop.write("\n\n")

    # The 'orignal' dataset contains only the original full AMR graphs. We evaluate the full AMR sota model on this subset to check that it is not a particularly easy/difficult subset.
    with open(originalOnlyPath, "a") as oop:
        oop.write(pmoriginal)
        oop.write("\n\n")

    # The 'chopped' dataset contains only the incomplete underspecified graphs, and the completions.
    with open(choppedOnlyPath, "a") as cop:
        cop.write(pmgh1)
        cop.write("\n\n")
        cop.write(pmgh2)
        cop.write("\n\n")

    # The 'incomplete' dataset contains only the incomplete underspecified graphs.
    with open(incompleteOnlyPath, "a") as iop:
        iop.write(pmgh1)
        iop.write("\n\n")

    # The 'completion' dataset contains only the AMR/completion pairs.
    with open(completionOnlyPath, "a") as cop2:
        cop2.write(pmgh2)
        cop2.write("\n\n")

# Given an AMR record, process it and chop if appropriate.
def processRecord(AMRrecord):
    # Extract the text sentence and the AMR graph from the record.
    utterance, originalGraph = parseOriginal(AMRrecord)
    # Extract all the named entities from the triples in the AMR graph
    nameNodes, nameLabels = getNameInfo(originalGraph.triples)
    # At every potential chop point, check if the graph is choppable, and return the chop node and label if it is.
    for nn in nameNodes:
        choppable, chopNode, chopLabel = willItChop(utterance, [nn], nameLabels)
        # If choppable, proceed to chop and store.
        if choppable:
            # Chop the AMR graph into gh1 and gh2 (gh = graph half), chopping at the identified node.
            gh1, gh2 = chopAMR(utterance, originalGraph, chopNode, chopLabel)
            # Some AMR examples are just named entities, so check that the incomplete sentence (gh1) is not empty.
            if gh1.metadata["snt"].replace(" UNK", "") != '':
                # Save if chopped sucessfully.
                store(originalGraph, gh1, gh2)

# This function checks for the filepath input, parses the AMR and sends each AMR record for processing.
def processFile():
    try:
        filepath = sys.argv[1]
    except IndexError:
        print("Please add ./input/filepath.txt after disruptAMR.py")
        sys.exit(1)
    
    with open(filepath) as f:
        amrs = f.read().split("\n\n")
        for amr in tqdm(amrs):
            processRecord(amr)

# Disrupt the file given as a system argument input.
if __name__ == "__main__":
    processFile()
