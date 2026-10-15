# Third-party notices

These notices apply to the named third-party materials, not to a new license grant for the application as a whole.

## PUBHEALTH

Dataset: Neema Kotonya and Francesca Toni, Explainable Automated Fact-Checking for Public Health Claims (EMNLP 2020).
Source: https://github.com/neemakot/Health-Fact-Checking
Upstream license: https://github.com/neemakot/Health-Fact-Checking/blob/master/LICENSE
The supplied CSV is the project's cleaned two-class subset. Original fact-check and source publisher attributions remain in its provenance columns.

MIT License

Copyright (c) 2020 Neema Kotonya

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## XLM-RoBERTa base

Base model: https://huggingface.co/FacebookAI/xlm-roberta-base
Original implementation: https://github.com/facebookresearch/fairseq/tree/main/examples/xlmr
Upstream license: https://github.com/facebookresearch/fairseq/blob/main/LICENSE
The supplied sequence classifier is fine-tuned from this pretrained base model.

MIT License

Copyright (c) Facebook, Inc. and its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Other downloaded components

Runtime dependencies retain their own licenses. Setup downloads these models separately:

- Embeddings: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- Evidence NLI: https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
- OCR: https://github.com/RapidAI/RapidOCR

Evidence passages retain their recorded source URLs and license notes in SQLite.
