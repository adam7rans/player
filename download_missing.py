#!/usr/bin/env python3
from downloader import download_missing_playlists

PLAYLISTS = [
    "https://music.youtube.com/playlist?list=OLAK5uy_n09BOqlYRm1RdhvTovqQie87TGwa3PbRA",
    "https://music.youtube.com/playlist?list=OLAK5uy_kYR35B4ncA8wieeJxNroXlI8cSOVh3okU",
    "https://music.youtube.com/playlist?list=OLAK5uy_npVGHGqWs_-hTzVUivb8lCndQPVB7aIm0",
    "https://music.youtube.com/playlist?list=OLAK5uy_kYJNMDJkoNOf2yLk9ufq-m1Cipu1dvG24",
    "https://music.youtube.com/playlist?list=OLAK5uy_lSgzI-u4sTZ9YWMlMcTpeRBhfnp5HKmEY",
    "https://music.youtube.com/playlist?list=OLAK5uy_mTZiCulgHFbzkIChf8KQbUL3DWh2PCmSI",
    "https://music.youtube.com/playlist?list=OLAK5uy_kXVkPcdf0y9h8Im_G6XQ3YM_h18WBGrV0",
    "https://music.youtube.com/playlist?list=OLAK5uy_lJn0jn-w7AaHAJQcnbUKHdQ_i4T4RpCvI",
    "https://music.youtube.com/playlist?list=OLAK5uy_mLan-c6bbAQvHu2gk8NglLlstkk7FGl7c",
    "https://music.youtube.com/playlist?list=OLAK5uy_m3SXiiM0zykHKsmU_4UaOE8jBUoVYU4xg"
]

if __name__ == "__main__":
    print("Starting missing playlist download check...")
    download_missing_playlists(PLAYLISTS)
    print("\nDownload check complete!")
