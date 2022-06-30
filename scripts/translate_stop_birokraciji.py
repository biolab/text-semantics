import os

import deepl
import pandas as pd
import yaml


# to enable the script create IN_PATH folder in the same directory then script
IN_PATH = "stop-birokraciji"
OUT_PATH = "stop-to-bureaucracy"
auth_key = "..."


podrocje_trans = {
    "Visoko šolstvo": "Higher education",
    "Zdravstvo": "Health",
    "Finance": "Finance",
    "Javna uprava": "Public Administration",
    "Promet": "Traffic",
    "Okolje in prostor": "Environment and spatial planning",
    "Sociala": "Social activity",
    "Delovno pravno": "Working law",
    "Kohezija": "Cohesion",
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

    data["Initiative ID"] = data.pop("ID pobude")
    data["Initiative published"] = data.pop("Pobuda objavljena")
    data["Initiative submitted"] = data.pop("Pobuda oddana")
    data["Initiative forwarded in response"] = data.pop("Pobuda posredovana v odziv")
    data["Initiative accepted and completed"] = data.pop(
        "Pobuda sprejeta in zaključena"
    )
    data["Initiative classified in EZU"] = data.pop("Pobuda uvrščena v EZU")
    data["Competent authority"] = data.pop("Pristojni organ")

    title = data.pop("Naslov")
    data["Title"] = title if pd.isna(title) else translator.translate_text(
        title, target_lang="EN-US", source_lang="SL"
    ).text
    response = data.pop("Odgovor pristojnega organa")
    data["Response from the competent authority"] = (
        response
        if pd.isna(response)
        else translator.translate_text(
            response, target_lang="EN-US", source_lang="SL"
        ).text
    )
    area = data.pop("Področje")
    data["Area"] = area if pd.isna(area) else area

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
