# Text semantics
The package with scripts for semantic analyser project

## Usage

```
from textsemantics.server_api import ServerAPI

# init API
# URL is not required for a default server file.biolab.si/text-semantics
api = ServerAPI()

# get all available datasets - list with dataset names
datasets = api.list_datasets()

# get dataset info - dictionary with dataset size and metadata type
api.get_dataset_info(datasets[0][0])

# get metadata for particular dataset - pandas dataframe
metadata = api.get_metadata(datasets[0][0])

# get all texts in the column - metadata["Law text"] - list of strings
texts = api.get_texts(metadata["Law text"])
```

For detailed description looks at docstrings in the 
[module](https://github.com/biolab/text-semantics/blob/main/textsemantics/server_api.py).



