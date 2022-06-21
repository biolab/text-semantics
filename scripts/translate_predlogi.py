import os

import deepl
import yaml


# to enable the script create IN_PATH folder in the same directory then script
IN_PATH = "predlogi-1k"
OUT_PATH = "predlogi-1k-english"
auth_key = "..."


prop_type_trans = {
    "Nezadostna podpora": "Insufficient support",
    "Odziv pristojnega organa": "Competent authority response",
    "Neustrezen": "Inappropriate",
    "Čaka odziv": "Waiting for a response",
    "Predlog v glasovanju": "Proposal in vote",
    "Predlog v razpravi": "Proposal under discussion"
}


def translate_txt(file_name):
    path = os.path.join(IN_PATH, file_name)
    with open(path, "r") as f:
        text = f.read()

    result = translator.translate_text(text, target_lang="EN-US", source_lang="SL")

    out_path = os.path.join(OUT_PATH, file_name)
    with open(out_path, "w") as f:
        f.write(result.text)


def translate_yaml(file_name):
    path = os.path.join(IN_PATH, file_name)
    with open(path, "r") as stream:
        data = yaml.safe_load(stream)
    data["proposal type"] = prop_type_trans[data["proposal type"]]
    if data["response"]:
        data["response"] = translator.translate_text(data["response"], target_lang="EN-US", source_lang="SL").text
    data["title"] = translator.translate_text(data["title"], target_lang="EN-US", source_lang="SL").text

    out_path = os.path.join(OUT_PATH, file_name)
    with open(out_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


if not os.path.exists(OUT_PATH):
    os.mkdir(OUT_PATH)
translator = deepl.Translator(auth_key)

already_translated = set(os.listdir(OUT_PATH))

for file in sorted(os.listdir(IN_PATH)):
    if file not in already_translated:
        print("Translating:", file)
        if file.endswith(".txt"):
            translate_txt(file)
        if file.endswith(".yaml"):
            translate_yaml(file)
    else:
        print("Skipping:", file)
