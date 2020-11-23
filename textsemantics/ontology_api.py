import io
import os
from typing import List

import requests
import yaml
from requests_futures.sessions import FuturesSession

from textsemantics.utils import list_files


class OntologyAPI:
    def __init__(
        self,
        server_url: str = "http://file.biolab.si/text-semantics/ontologies",
    ):
        self.server_url = server_url + ("" if server_url.endswith("/") else "/")

    def list_ontologies(self) -> List[str, str]:
        """
        List all ontologies in the directory on the provided URL.

        We assume each ontology have yaml

        Returns
        -------
        The list of tuples with ontology name and path to the ontology
        """
        yamls = [
            url
            for f, url in list_files(self.server_url)
            if f.endswith((".yaml", ".yml"))
        ]
        # FuturesSession - faster download with parallel thread
        session = FuturesSession(max_workers=20)
        futures = [session.get(y) for y in yamls]
        mds = [
            yaml.safe_load(io.StringIO(f.result().content.decode("utf-8")))
            for f in futures
        ]
        return [os.path.splitext(m["ontology file"])[0] for m in mds]

    def download_ontology(self, ontology_name: str, path: str) -> None:
        meta_file = requests.get(f"{self.server_url}{ontology_name}.yaml")
        meta_file.raise_for_status()  # raise when 404
        meta = yaml.safe_load(io.StringIO(meta_file.content.decode("utf-8")))
        to_download = [meta["ontology file"]] + meta["imports"]
        for file in to_download:
            url = f"{self.server_url}{file}"
            response = requests.get(url)
            with open(os.path.join(path, file), "wb") as f:
                f.write(response.content)


if __name__ == "__main__":
    api = OntologyAPI()
    ontologies = api.list_ontologies()
    print(ontologies)

    api.download_ontology(ontologies[1], "target_dir")
