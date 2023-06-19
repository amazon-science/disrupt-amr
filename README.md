# AMR - Understanding Disrupted Sentences

ASR systems are not always confident of a certain word as the audio was unclear. For example, if a door slams or siren passes in the middle of a customer's utterance. In this project, we want to explore whether we can represent disrupted customer utterances, and recover this into a full representation with one additional turn.

## Citation
If you use this code, please cite the following paper:

```
@inproceedings{angus2023,
  title={Understanding Disrupted Sentences Using Underspecified Abstract Meaning Representation},
  author={Addlesee, Angus and Damonte, Marco},
  booktitle={Interspeech},
  year={2023}
}
```

## Aligning AMR

In order to chop AMR effectively, alignment models can be used to specify which precise AMR subgraph represents a particular token. We implemented IBMs AMR alignment model [found here](https://github.com/IBM/transition-amr-parser). We use the output of this alignment model as the input to all the interruption/disruption scripts below.

## Disrupting AMR

In order to investigate this probelm, we need a dataset of disrupted sentences and their underspecified MRLs. We decided to use AMR 3.0 and disrupted it in three ways.

1. When the end of the sentence is missing, e.g: "She likes France and"
2. When we have the full sentence, but the last word is unclear (this is to determine whether this is an easier task). e.g: "She likes France and UNK"
3. When a word is disrupted anywhere, including the middle of a sentence (same as 2, but not just at the end). e.g: "She likes UNK and Italy"

Download the AMR you would like to disrupt, and put the `.txt` file in the `./input` directory. To chop the AMR with method (1), run the following (replacing amrFile with the name of your file):

    python chopAMR.py ./input/amrFile.txt

You wll find your chopped datasets in the `output` directory. You can uncomment the line marked "TODO Uncomment if you want the UNK tag" and rerun the above to chop with method (2). To chop with method (3), run the following:

    python disruptAMR.py ./input/amrFile.txt

You should now have your corpora in the output file. NOTE: chopped AMR chunks are stored incrementally using the 'append' write method. This will continue appending if you rerun the scripts with the same inputs. We recommend moving to a directory called `stored` to preserve chopped AMR.

## Training disrupted AMR models

We are using the [SPRING](https://github.com/SapienzaNLP/spring) model for our full baseline and retrained models. Follow their setup instructions and edit `configs/config.yaml` to point at your dev, test, and train sets. You will also find the instructions to evaluate your trained SPRING models in their documentation.

# Example Dialogues

In the paper, we noted we would include some example dialogues for illustration purposes. These are real examples from our corpus, but the clarification request is invented (generating CRs is included in the future work section of the paper). Ideally these CRs would be uttered by some Everyday Voice Assistant (EVA).

## Example 1 (UNK denotes where the ASR made a low-confidence prediction, maybe due to a siren passing)
- User: "Where's UNK when you need him?"
- EVA: "Sorry, I didn't cath all of that, where's who?"
- User: "Homer Simpson"

## Example 2 (No UNK as this is where a person paused mid-utterance, maybe due to memory problems))
- User: "Route 288, the circumferential highway running around the south-western quadrant of the Richmond New Urban Region, opened in late"
- EVA: "Apologies, I think I missed something there. In late when?"
- User: "2004"

## Example 3 (the model must identify where the UNK belongs amongst a variety of info)
- User: "The quake occurred at 04:20 pm New Zealand local time (03:20 GMT) and the epic center was 90km northeast of UNK and at a depth of 2585km"
- EVA: "Sorry, northeast of where?"
- User: "Port-Vila"

