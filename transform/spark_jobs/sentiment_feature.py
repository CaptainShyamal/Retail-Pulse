import json
import os
import pandas as pd
from typing import Dict

def compute_sentiment_scores(reviews_path: str = None, cache_path: str = None) -> Dict[str, float]:
    """
    Computes average sentiment score per SKU from reviews.
    Score ranges from -1.0 (most negative) to 1.0 (most positive), 0.0 is neutral.
    Caches results to avoid re-computing.
    """
    if reviews_path is None:
        reviews_path = os.path.join("data", "raw_sample", "reviews_raw.csv")
    if cache_path is None:
        cache_path = os.path.join("data", "cache", "sentiment_scores.json")

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    # Check if cache exists
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                scores = json.load(f)
                print(f"Loaded cached sentiment scores for {len(scores)} SKUs.")
                return scores
        except Exception as e:
            print(f"Cache read error: {e}. Recomputing...")

    if not os.path.exists(reviews_path):
        print(f"Reviews file not found at {reviews_path}. Defaulting all SKUs to neutral sentiment (0.0).")
        return {}

    df = pd.read_csv(reviews_path)
    if "sku" not in df.columns or "review_text" not in df.columns:
        print(f"Missing required columns in {reviews_path}. Returning default scores.")
        return {}

    print(f"Analyzing sentiment for {len(df)} customer reviews across SKUs...")

    # Attempt HuggingFace sentiment pipeline, fallback to keyword/lexicon based scoring
    use_hf = False
    sentiment_pipeline = None
    try:
        from transformers import pipeline
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=-1  # CPU
        )
        use_hf = True
    except Exception as e:
        print(f"Transformers pipeline not loaded ({e}), using optimized sentiment heuristic.")

    sku_scores = {}
    for sku, group in df.groupby("sku"):
        scores_list = []
        for text in group["review_text"].dropna():
            text_str = str(text).strip()
            if not text_str:
                continue
            if use_hf and sentiment_pipeline:
                try:
                    res = sentiment_pipeline(text_str[:512])[0]
                    score = res["score"] if res["label"] == "POSITIVE" else -res["score"]
                    scores_list.append(score)
                    continue
                except Exception:
                    pass

            # Fast Lexicon heuristic fallback
            pos_words = {"great", "good", "love", "excellent", "fast", "perfect", "best", "recommend", "amazing", "fresh", "happy", "quality"}
            neg_words = {"bad", "poor", "broken", "terrible", "slow", "damaged", "awful", "horrible", "defect", "worst", "hate", "issue", "expired", "delay"}
            tokens = set(text_str.lower().split())
            pos_count = len(tokens & pos_words)
            neg_count = len(tokens & neg_words)
            if pos_count + neg_count > 0:
                raw_score = (pos_count - neg_count) / (pos_count + neg_count)
            else:
                raw_score = 0.0
            scores_list.append(raw_score)

        avg_score = float(pd.Series(scores_list).mean()) if scores_list else 0.0
        sku_scores[sku] = round(avg_score, 4)

    # Save to cache
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(sku_scores, f, indent=4)
    print(f"Computed & cached sentiment scores: {sku_scores}")
    return sku_scores

if __name__ == "__main__":
    compute_sentiment_scores()
