# INFO 290 Group 5 — AI Movie Marketing: RAG Pipeline

This notebook implements a RAG-based movie marketing asset generation pipeline. Given a 1-sentence movie concept, it generates the following marketing assets:
- **Tagline** (≤ 12 words)
- **Overview** (≤ 80 words, promo-style synopsis)
- **Poster Art Direction** (≤ 60 words)

## Prerequisites: API Tokens

You will need three API tokens. Set them in Colab via **Secrets** (the 🔑 icon in the left sidebar):

| Secret Name | Description | How to get it |
|---|---|---|
| `TMDB_BEARER` | TMDB API Read Access Token | [developer.themoviedb.org/docs/getting-started](https://developer.themoviedb.org/docs/getting-started) — Log in → Settings → API → "API Read Access Token" |
| `HF_TOKEN` | Hugging Face User Access Token | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) — New token → Role: Read |
| `GITHUB_TOKEN` | GitHub Personal Access Token | [github.com/settings/tokens](https://github.com/settings/tokens) — Generate new token (classic) → Scope: `repo` |

## Pipeline Overview

```
Step 0: Data Collection (done — tmdb_movies.csv on GitHub)
         └─ 4,816 movies fetched from TMDB API

Step 1: Build RAG Corpus
         └─ Filter to movies with taglines (4,312 movies)
         └─ Embed [title + tagline + overview] with Sentence-BERT (all-MiniLM-L6-v2)
         └─ Index with FAISS (IndexFlatIP / cosine similarity)

Step 2: Generation
         └─ V1: Zero-shot baseline (no RAG)
         └─ V2: RAG-enhanced (retrieve top-k → pass as style reference → generate)

Input:  1-sentence movie concept
Output: overview + tagline + poster_art_direction
```

## Model

- **LLM**: Mistral-7B-Instruct-v0.2 (4-bit quantized via BitsAndBytes)
- **Embedding**: sentence-transformers/all-MiniLM-L6-v2 (384-dim)
- **Hardware**: Colab GPU (G4 recommended)

