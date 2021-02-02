import json
import os

from serverfiles import ServerFiles, LocalFiles
from ufal import udpipe


def language_to_name(language):
    return language.lower().replace(' ', '') + 'ud'


def file_to_name(file):
    return file.replace('-', '').replace('_', '')


def file_to_language(file):
    return file[:file.find('ud')-1]\
        .replace('-', ' ').replace('_', ' ').capitalize()


class UDPipeModels:
    server_url = "https://file.biolab.si/files/udpipe/"

    def __init__(self):
        dir_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "udpipe_models"
        )
        self.serverfiles = ServerFiles(self.server_url)
        self.localfiles = LocalFiles(dir_path, serverfiles=self.serverfiles)

    def __getitem__(self, language):
        file_name = self._find_file(language_to_name(language))
        return self.localfiles.localpath_download(file_name)

    @property
    def model_files(self):
        try:
            return self.serverfiles.listfiles()
        except ConnectionError:
            return self.localfiles.listfiles()

    def _find_file(self, language):
        return next(filter(lambda f: file_to_name(f).startswith(language),
                           map(lambda f: f[0], self.model_files)))

    @property
    def supported_languages(self):
        return list(map(lambda f: file_to_language(f[0]), self.model_files))


def get_udipipe_lematizer(language):
    model = udpipe.Model.load(UDPipeModels()[language])
    output_format = udpipe.OutputFormat.newOutputFormat('epe')

    def udpipe_lemmatizer(token):
        sentence = udpipe.Sentence()
        sentence.addWord(token)
        model.tag(sentence, model.DEFAULT)
        output = output_format.writeSentence(sentence)
        return json.loads(output)['nodes'][0]['properties']['lemma']

    return udpipe_lemmatizer