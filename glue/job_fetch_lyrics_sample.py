import csv
import io
import json
import time
import requests
import boto3
from urllib.parse import quote_plus

S3_BUCKET = "spotify-genre-similarity-sri"

# NEW safe, headerless UNLOAD file (CSV with proper quoting)
INPUT_S3_URI = "s3://spotify-genre-similarity-sri/curated/lyrics_input_stratified_safe/20260104_030126_00079_9qvn9_00dcdc03-eb1c-430c-82e7-fbbd1b4dc2ab"

# Output (JSONL)
OUT_PREFIX = "curated/lyrics_by_track_sample/"
OUT_FILENAME = "lyrics_sample.jsonl"

# Controls (keep small first)
MAX_TRACKS_TOTAL = 200
SLEEP_SEC = 0.6
TIMEOUT_SEC = 12
RETRIES = 2

s3 = boto3.client("s3")


def parse_s3_uri(uri: str):
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {uri}")
    parts = uri[5:].split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    return bucket, key


def read_text_from_s3(bucket: str, key: str) -> str:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8", errors="replace")


def write_jsonl_to_s3(lines, out_key):
    body = ("\n".join(lines) + "\n").encode("utf-8")
    s3.put_object(Bucket=S3_BUCKET, Key=out_key, Body=body)


def clean_val(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join([str(x).strip() for x in v if x is not None]).strip()
    return str(v).strip()


def get_lyrics_lrclib(track_name: str, artist_name: str):
    q = quote_plus(f"{track_name} {artist_name}")
    url = f"https://lrclib.net/api/search?q={q}"

    for _ in range(RETRIES + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT_SEC, headers={"User-Agent": "spotify-genre-similarity/1.0"})
            if r.status_code != 200:
                time.sleep(SLEEP_SEC)
                continue

            data = r.json()
            if not data:
                return None

            item = data[0]
            lyr = item.get("plainLyrics") or item.get("syncedLyrics")
            return lyr if lyr else None

        except Exception:
            time.sleep(SLEEP_SEC)

    return None


def main():
    in_bucket, in_key = parse_s3_uri(INPUT_S3_URI)
    text = read_text_from_s3(in_bucket, in_key)

    # Headerless CSV: each row is [track_id, track_name, artist_name_primary, genre]
    reader = csv.reader(io.StringIO(text), delimiter=",", quotechar='"', escapechar="\\")
    print("Reading headerless CSV by column position: track_id, track_name, artist_name_primary, genre")

    lines_out = []
    n = 0
    found = 0

    for row in reader:
        if n >= MAX_TRACKS_TOTAL:
            break

        if not row or len(row) < 4:
            continue

        track_id = clean_val(row[0])
        track_name = clean_val(row[1])
        artist_name = clean_val(row[2])
        genre = clean_val(row[3]).lower()

        if not track_id or not track_name or not artist_name or not genre:
            continue

        lyr = get_lyrics_lrclib(track_name, artist_name)
        time.sleep(SLEEP_SEC)

        rec = {
            "track_id": track_id,
            "track_name": track_name,
            "artist_name_primary": artist_name,
            "genre": genre,
            "lyrics": lyr,
            "lyrics_found": bool(lyr)
        }

        if lyr:
            found += 1

        lines_out.append(json.dumps(rec, ensure_ascii=False))
        n += 1

        if n % 50 == 0:
            print(f"Processed {n} tracks. Lyrics found for {found}.")

    out_key = OUT_PREFIX + OUT_FILENAME
    write_jsonl_to_s3(lines_out, out_key)
    print(f"Done. Processed={n}, lyrics_found={found}. Wrote s3://{S3_BUCKET}/{out_key}")


if __name__ == "__main__":
    main()
