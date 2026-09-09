# TikREC

A minimal command-line tool for recording a single TikTok LIVE stream to disk.

Point it at a URL, it records until the stream ends or you stop it, and
you get one MP4 out.

## Status

Rewrite in progress. Building module by module:

- [ ] `flv.py` — FLV tag parsing
- [ ] `writer.py` — part files on disk
- [ ] `source.py` — fetching the stream
- [ ] `finalize.py` — stitching to MP4

## Usage

    tikrec record <url> [--out DIR]

## Requirements

- Python 3.11+
- ffmpeg and ffprobe on PATH

## Design

See [SPEC.md](SPEC.md) for the full design and [AGENTS.md](AGENTS.md)
for the working rules.