from collections import defaultdict
from string import punctuation

from nltk.tokenize import RegexpTokenizer
from datasets import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    AutoConfig,
    DataCollatorForTokenClassification,
    Trainer,
)
import torch
from torch.nn import functional as F
import spacy


class TransformerKeywordExtractor:

    def __init__(self, model_path):
        config = AutoConfig.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)
        model = AutoModelForTokenClassification.from_pretrained(
            model_path, from_tf=False, config=config,
        )
        data_collator = DataCollatorForTokenClassification(
            tokenizer, pad_to_multiple_of=None,
        )
        self.trainer = Trainer(
            model=model,
            args=None,
            train_dataset=None,
            eval_dataset=None,
            tokenizer=tokenizer,
            data_collator=data_collator,
            compute_metrics=None,
        )
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.spacy_object = spacy.load('xx_sent_ud_sm')

    def _fragmentize(self, text):
        sentences = self.sent_tokenize(text)
        tokenized = [self.trainer.tokenizer.tokenize(sent) for sent in sentences]
        result = list()
        current = list()
        current_len = 0
        for sentence, tokenized_sentence in zip(sentences, tokenized):
            if current_len + len(tokenized_sentence) <= self.trainer.tokenizer.model_max_length - 2:
                current.append(sentence)
                current_len += len(tokenized_sentence)
            else:
                result.append(' '.join(current))
                current = list()
                current_len = 0
        result.append(' '.join(current))
        return result

    def sent_tokenize(self, text):
        return [sent.text for sent in self.spacy_object(text).sents]

    def extract_keywords(self, texts):
        fragments = list()
        num_fragments = list()
        for text in texts:
            result = self._fragmentize(text)
            fragments.extend(result)
            num_fragments.append(len(result))
        result = self._extract_keywords(fragments)
        all_keywords = list()
        current = 0
        for num in num_fragments:
            kws = list()
            for kw in result[current:current+num]:
                kws.extend(kw)
            all_keywords.append(kws)
            current += num
        return all_keywords

    def _extract_keywords(self, texts):
        def tokenize(data):
            tokenized_dataset = self.trainer.tokenizer(
                data['tokens'],
                padding=False,
                truncation=True,
                is_split_into_words=True,
            )
            labels = list()
            for i in range(len(data['tokens'])):
                previous_word_idx = -1
                current_labels = list()
                for word_idx in tokenized_dataset.word_ids(batch_index=i):
                    if word_idx is None or word_idx == previous_word_idx:
                        current_labels.append(-100)
                    else:
                        current_labels.append(1)
                    previous_word_idx = word_idx
                labels.append(current_labels)

            tokenized_dataset['labels'] = labels
            return tokenized_dataset

        dataset_d = defaultdict(list)
        tokenizer = RegexpTokenizer(r'\w+|\$[\d\.]+|\S+')
        for text in texts:
            dataset_d['tokens'].append(tokenizer.tokenize(text))
        dataset = Dataset.from_dict(dataset_d).map(
            tokenize, batched=True, num_proc=None)

        predictions, labels, _ = self.trainer.predict(dataset)
        predictions = F.softmax(torch.tensor(predictions), dim=2)
        probabilities, predictions = torch.max(
            torch.tensor(predictions).to(self.device), dim=2)

        label_list = ['B', 'I', 'O']
        predictions = [
            [label_list[p] for (p, lab) in zip(prediction, label) if lab != -100]
            for prediction, label in zip(predictions, labels)
        ]

        all_keywords = list()
        for text_idx, (example, pred, prob) in enumerate(zip(dataset_d['tokens'], predictions, probabilities)):
            keywords = list()
            keyword_probabilities = list()
            i = 0
            while i < len(pred):
                if pred[i] == 'B':
                    current_keyword = example[i]
                    current_prob = prob[i]
                    i = i + 1
                    while i < len(pred) and pred[i] == 'I':
                        current_keyword += (example[i] if current_keyword + example[i] in
                                            texts[text_idx] else ' ' + example[i])
                        current_prob *= prob[i]
                        i += 1
                    else:
                        i = i - 1
                    keywords.append(current_keyword.lower())
                    keyword_probabilities.append(float(current_prob))
                i += 1
            idx = torch.argsort(torch.tensor(keyword_probabilities), descending=True)
            keywords = [keywords[i] for i in idx]
            probabilities = [keyword_probabilities[i] for i in idx]
            
            def strip_punctuation(kw):
                return kw.strip(punctuation)

            def deduplicate(kws, probs):
                new_kws = list()
                new_probs = list()
                for kw, p in zip(kws, probs):
                    kw = strip_punctuation(kw)
                    if kw not in new_kws:
                        new_kws.append(kw)
                        new_probs.append(p)
                return list(zip(new_kws, new_probs))

            all_keywords.append(deduplicate(keywords, probabilities))
        return all_keywords
