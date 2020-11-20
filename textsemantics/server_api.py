import io
import os
import random
from multiprocessing import Pool
from typing import List, Tuple, Dict, Iterable, Optional
from urllib.parse import urljoin, unquote

import requests
import yaml
from bs4 import BeautifulSoup
import pandas as pd
from requests_futures.sessions import FuturesSession


class ServerAPI:
    def __init__(
        self, server_url: str = "http://file.biolab.si/text-semantics/"
    ):
        self.server_url = server_url

    @staticmethod
    def _list_files(url: str) -> List[Tuple[str, str]]:
        """
        Return a list of (filename, file-URL) pairs in the server directory
        """
        if not url.endswith("/"):
            url += "/"

        soup = BeautifulSoup(requests.get(url).text, "html.parser")
        return [
            (unquote(os.path.basename(node.get("href").rstrip("/"))),
             urljoin(url, node.get("href")))
            for node in soup.find_all("a")
            if node.text != "../"
        ]

    def list_datasets(self) -> List[Tuple[str, str]]:
        """
        List all datasets from the provided address.

        We assume each directory contains one dataset.

        Returns
        -------
        The list of tuples with dataset name and path to the datasets
        """
        return self._list_files(self.server_url)

    def get_dataset_info(self, dataset_name: str) -> Dict[str, str]:
        """
        Get the number of instances in a server dataset and a metadata type.

        Parameters
        ----------
        dataset_name
            The directory containing text files and metadata file/s.

        Returns
        -------
        A dictionary with two keys:
        - Instances number: number of instances in the dataset
        - Metadata type: the format of metadata (CSV: one table, YAML: separate
          file for each document).
        """
        files = self._list_files(urljoin(self.server_url, dataset_name))
        files_names = [f[0] for f in files]
        yamls = [f.endswith(".yml") or f.endswith(".yaml") for f in files_names]

        if "metadata.csv" in files_names:
            content = requests.get(
                urljoin(self.server_url, f"{dataset_name}/metadata.csv")
            ).content
            num_files = len(pd.read_csv(io.StringIO(content.decode("utf-8"))))
            metadata_type = "CSV"
        elif any(yamls):
            num_files = sum(yamls)
            metadata_type = "YAML"
        else:
            num_files = len(files_names)
            metadata_type = None
        return {"Instances number": num_files, "Metadata type": metadata_type}

    @staticmethod
    def _join_yaml_metadata(files: List[Tuple[str, str]], sample_size: int = None) -> pd.DataFrame:
        """
        Download YAMLs with metadata and concatenate them in a data frame.
        """
        yamls = [f for f in files if f[0].endswith((".yml", ".yaml"))]
        if sample_size is not None:
            try:
                yamls = random.sample(yamls, sample_size)
            except ValueError:  # Sample larger than population
                yamls = yamls

        # FuturesSession - faster download with parallel thread
        session = FuturesSession(max_workers=20)
        futures = [session.get(y[1]) for y in yamls]
        mds = [
            yaml.safe_load(io.StringIO(f.result().content.decode("utf-8")))
            for f in futures
        ]
        return pd.DataFrame(mds)

    @staticmethod
    def _file_names_to_paths(meta_data: pd.DataFrame, files: List[Tuple[str, str]]) -> pd.DataFrame:
        """
        Transforms file names (if they are not paths already) to full url/path.
        """
        files_names, files_paths = list(zip(*files))
        for col in meta_data:
            try:
                is_file = (
                    meta_data[col].str.contains(r".+\.\w+", na=True).all()
                    and not meta_data[col].isnull().all()
                )
            except AttributeError:
                # when column has a dtype not compatible with .str (e.g. float)
                is_file = False

            if is_file:
                paths = []
                for item in meta_data[col]:
                    try:
                        if item:
                            idx = files_names.index(item)
                            paths.append(files_paths[idx])
                        else:
                            paths.append(None)
                    except ValueError:
                        break
                else:
                    # assign only in case files exists for each value - no break
                    # using assign method to insert in a copy of dataframe
                    meta_data = meta_data.assign(**{col: paths})
        return meta_data

    def get_metadata(self, dataset_name: str, sample_size: int = None) -> pd.DataFrame:
        """
        Get metadata for a specified dataset from the server.

        Parameters
        ----------
        dataset_name
            The name of the dataset
        sample_size
            The random sample size (optional). When None sampling is disabled.

        Returns
        -------
        The data frame where each row represents a data instance, columns are
        metadata. Some of them are paths to document file.
        """
        files = self._list_files(urljoin(self.server_url, dataset_name))
        ds_info = self.get_dataset_info(dataset_name)

        if ds_info["Metadata type"] == "CSV":
            s = requests.get(
                urljoin(self.server_url, f"{dataset_name}/metadata.csv"),
            ).content
            meta_data = pd.read_csv(io.StringIO(s.decode("utf-8")))
            if sample_size is not None:
                meta_data = meta_data.sample(sample_size)
            meta_data = self._file_names_to_paths(meta_data, files)
        elif ds_info["Metadata type"] == "YAML":
            meta_data = self._join_yaml_metadata(files, sample_size=sample_size)
            meta_data = self._file_names_to_paths(meta_data, files)
        else:
            meta_data = pd.DataFrame(files, columns=["File name", "File path"])
        return meta_data

    @staticmethod
    def get_text(url: str) -> Optional[str]:
        """
        Retrieve text from the document at the provided URL.

        Parameters
        ----------
        url
            Url of the document

        Returns
        -------
        Document's text.
        """
        # TODO: add support for pdf, odt, and doc
        if not url:
            return None
        handler = {
            "text/plain": lambda x: x.content.decode("utf-8"),
        }
        r = requests.get(url)
        type_ = r.headers['Content-Type'].split()[0].strip(";")

        return handler.get(type_)(r)

    def get_texts(self, urls: Iterable[Optional[str]]) -> List[Optional[str]]:
        """
        Retrieve texts from the documents at the provided URLs.

        Parameters
        ----------
        urls
            Documents' URLs

        Returns
        -------
        Documents' texts.
        """
        with Pool(20) as p:
            return p.map(self.get_text, urls)


if __name__ == "__main__":
    # init API
    # URL is not required for a default server file.biolab.si/text-semantics
    api = ServerAPI()

    # get all available datasets
    datasets = api.list_datasets()
    print(datasets)

    # print dataset info
    print(api.get_dataset_info(datasets[0][0]))

    # get info about a particular dataset
    metadata = api.get_metadata(datasets[0][0])
    print(metadata.columns)
    print(metadata["Law text"])

    # get all texts in the column - metadata["Law text"]
    texts = api.get_texts(metadata["Law text"])
    print(texts)


