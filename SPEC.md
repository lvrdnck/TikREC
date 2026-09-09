# tikrec2 — minimal FLV recorder

## Goal
A command-line tool that records one TikTok LIVE stream to disk, from a URL
I supply manually, and stops when I stop it or when the stream ends.

Nothing else. No monitoring, no polling, no transcription, no web UI,
no notifications, no database.

## Non-goals (do not build these)
- Watching a handle and auto-starting
- Transcription, chapters, search, analytics
- Web server or library UI
- Cookie/authenticated access to restricted streams
- Anything involving multiple creators

## Usage
    tikrec record <url> [--out DIR]

Prints progress to stdout. Ctrl-C stops cleanly and finalizes what it has.

## Behaviour

1. Resolve the given URL to a direct FLV stream URL.
2. Open an HTTP connection and read the FLV byte stream.
3. Parse it into tags and write them to `part-0001.flv`, `part-0002.flv`, ...
4. Start a new part whenever the video configuration changes.
5. On stop or stream end, stitch the parts into one `final/original.mp4`.
6. Write a short `session.json` with what happened.

## Architecture — four modules, in dependency order

Build and test these in order. Do not start the next until the previous
has passing tests.

### 1. flv.py — pure format handling
No network, no subprocess. Bytes in, structured data out.

- `FlvTag` dataclass: tag_type, timestamp, stream_id, payload
- `read_tag(stream)` -> FlvTag | None
- `FlvTag.encoded(base_timestamp)` -> bytes
- Detect configuration tags vs media tags (byte 1 == 0 vs 1)
- `sps_dimensions(sps)` -> (width, height)
- `avc_configuration_dimensions(config)` -> (width, height)

### 2. writer.py — parts on disk
Takes an iterable of tags, writes part files.

- Rolls to a new part when the AVC configuration changes
- Rebases timestamps so each part starts near zero
- Waits for a video keyframe before writing media into a new part
- Writes to a hidden `.partial` name, renames on clean close
- Deletes parts that ended up with zero media tags

Key seam: this takes an *iterator of tags*, not a socket. That means a
file on disk is a valid input and the whole thing is testable offline.

### 3. source.py — getting the bytes
- Resolve a TikTok LIVE URL to a direct FLV URL
- Open it and yield chunks
- Reconnect on drop, with backoff, up to N attempts
- Same seam: expose `iter_tags(source)` so tests can pass a local file

### 4. finalize.py — stitching
- Given N part files, produce one MP4
- If all parts share the same configuration: remux losslessly, no re-encode
- If they differ: use an ffmpeg filter graph that keeps A/V in sync
- Shell out to ffmpeg; do not attempt this in Python

## Testing rules

- Every module gets tests before the next module is written.
- Tests must run without network access and without a live stream.
- Test inputs are small FLV files committed under `tests/fixtures/`.
  Generate them with ffmpeg where possible; capture real short samples
  where the quirk can't be synthesized.
- Minimum fixture set:
  - clean single-configuration stream
  - stream with a mid-stream resolution change
  - file truncated mid-tag (crash simulation)

## Constraints

- Python 3.11+, standard library only for FLV handling.
- ffmpeg/ffprobe as external binaries. No PyAV, no pypdf-style wrappers.
- Every non-obvious line gets a comment explaining *why*, citing the
  format behaviour it handles. If you can't explain why a line exists,
  don't write it.
- No file over 300 lines. If a module grows past that, split it.
- Ask me before adding any dependency.

## How to work with me

I am learning this codebase as we build it. After each module:
- Explain what you wrote, in plain language, before moving on.
- Point out anything you were unsure about.
- Do not scaffold ahead. One module at a time.