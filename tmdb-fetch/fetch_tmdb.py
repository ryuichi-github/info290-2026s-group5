"""Fetch ~5,000 popular movies from the TMDB API and save as parquet/CSV."""

import os
import sys
import time

import pandas as pd
import requests
from tqdm import tqdm

BASE_URL = "https://api.themoviedb.org"
RATE_LIMIT_DELAY = 1 / 25  # 25 requests per second


def get_bearer_token() -> str:
    token = os.environ.get("TMDB_BEARER")
    if not token:
        print("Error: TMDB_BEARER environment variable is not set.")
        sys.exit(1)
    return token


def tmdb_get_with_retry(url: str, params: dict, token: str, max_retries: int = 3):
    """Make a GET request to TMDB with retry on rate limit (429)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    for attempt in range(max_retries):
        time.sleep(RATE_LIMIT_DELAY)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"  Request error: {e}")
            return None

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 2))
            print(f"  Rate limited, sleeping {retry_after}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_after)
            continue

        print(f"  HTTP {resp.status_code} for {url}: {resp.text[:200]}")
        return None

    print(f"  Max retries exceeded for {url}")
    return None


def discover_movie_ids(token: str, max_pages: int = 250) -> list[int]:
    """Phase 1: Page through /discover/movie to collect movie IDs."""
    print("Phase 1: Discovering movie IDs...")
    movie_ids = []
    params = {
        "sort_by": "popularity.desc",
        "vote_count.gte": 100,
        "language": "en-US",
        "include_adult": "false",
    }

    for page in tqdm(range(1, max_pages + 1), desc="Discovering"):
        params["page"] = page
        data = tmdb_get_with_retry(f"{BASE_URL}/3/discover/movie", params, token)
        if data is None:
            print(f"  Failed to fetch page {page}, stopping discovery.")
            break

        results = data.get("results", [])
        if not results:
            print(f"  No results on page {page}, stopping discovery.")
            break

        movie_ids.extend(m["id"] for m in results)

        total_pages = data.get("total_pages", max_pages)
        if page >= total_pages:
            print(f"  Reached last page ({total_pages}).")
            break

    unique_ids = list(dict.fromkeys(movie_ids))  # preserve order, dedupe
    print(f"  Discovered {len(unique_ids)} unique movie IDs.")
    return unique_ids


def fetch_movie_details(movie_ids: list[int], token: str) -> list[dict]:
    """Phase 2: Fetch details for each movie ID."""
    print(f"\nPhase 2: Fetching details for {len(movie_ids)} movies...")
    movies = []
    seen_ids = set()

    for i, movie_id in enumerate(tqdm(movie_ids, desc="Fetching details"), 1):
        if movie_id in seen_ids:
            continue

        data = tmdb_get_with_retry(f"{BASE_URL}/3/movie/{movie_id}", {}, token)
        if data is None:
            continue

        overview = (data.get("overview") or "").strip()
        tagline = (data.get("tagline") or "").strip()

        # Data quality filters
        if not overview or len(overview) < 50:
            continue
        if not tagline and not overview:
            continue

        genres = data.get("genres", [])
        genre_ids = [g["id"] for g in genres]
        genre_names = [g["name"] for g in genres]

        movies.append({
            "id": data["id"],
            "title": data.get("title", ""),
            "tagline": tagline,
            "overview": overview,
            "release_date": data.get("release_date", ""),
            "genre_ids": genre_ids,
            "genre_names": genre_names,
            "vote_average": data.get("vote_average", 0.0),
            "vote_count": data.get("vote_count", 0),
            "popularity": data.get("popularity", 0.0),
        })
        seen_ids.add(movie_id)

        if i % 500 == 0:
            print(f"  Progress: {i}/{len(movie_ids)} fetched, {len(movies)} kept")

        if i % 1000 == 0:
            save_checkpoint(movies, i)

    return movies


def save_checkpoint(movies: list[dict], count: int):
    """Save a partial checkpoint parquet file."""
    df = pd.DataFrame(movies)
    path = f"tmdb_movies_checkpoint_{count}.parquet"
    df.to_parquet(path, index=False)
    print(f"  Checkpoint saved: {path} ({len(df)} movies)")


def save_output(movies: list[dict]):
    """Phase 3: Save final parquet and CSV files."""
    print(f"\nPhase 3: Saving output...")
    df = pd.DataFrame(movies)
    df.drop_duplicates(subset=["id"], inplace=True)

    df.to_parquet("tmdb_movies.parquet", index=False)
    df.to_csv("tmdb_movies.csv", index=False)

    with_tagline = df["tagline"].astype(bool).sum()
    without_tagline = len(df) - with_tagline

    print(f"\nSummary:")
    print(f"  Total movies saved: {len(df)}")
    print(f"  With tagline:       {with_tagline}")
    print(f"  Without tagline:    {without_tagline}")
    print(f"  Output files:       tmdb_movies.parquet, tmdb_movies.csv")


def main():
    token = get_bearer_token()
    movie_ids = discover_movie_ids(token)
    movies = fetch_movie_details(movie_ids, token)
    save_output(movies)


if __name__ == "__main__":
    main()
