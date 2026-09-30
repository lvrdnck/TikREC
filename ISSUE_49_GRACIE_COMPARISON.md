# Issue #49: old versus current Gracie recordings

Read-only investigation, 2026-09-30, against current `main` at `e18d132`.
Related: [#49](https://github.com/lvrdnck/TikREC/issues/49),
[#28](https://github.com/lvrdnck/TikREC/issues/28), and
[ISSUE_27_FORENSICS.md](ISSUE_27_FORENSICS.md).

## Findings

The exact issue-#28 LIVE was recorded by both programs. **They selected different
video renditions, and the old recording omits the reported corrupt interval.**
The old program rejected an in-band dimensions announcement at source timestamp
653.925 seconds, retried other renditions, and resumed useful retained input about
16.43 source-clock seconds later. Its visually clean MP4 therefore does not contain the same
10:15 moment as current TikREC's MP4.

Replaying the damaged current interval through the old normalization settings
does **not** make the columns visually clean. With or without
`+genpts+discardcorrupt`, the experiment preserves all 1,124 decoded video frames
and produces identical decoded output pixels. Both re-encoded MP4s decode without
errors but still display severe columns. A decoder-clean output is not evidence
of clean input imagery.

The transition hypothesis gains concrete evidence: current retained H.264 SEI
contains `push_video_width`/`push_video_height` changes at the exact source
timestamps reported by the old recorder's rejection path. These describe the
publisher's pushed geometry; they do not prove that the CDN rendition's actual
encoded geometry changed. Current AVC headers remain 640x1280 throughout.

No specific current-TikREC writer defect is proven. The original HTTP bytes for
this occurrence are missing, so source-versus-writer attribution remains #28.
No corrective issue or production change was justified by this comparison.

## Matched evidence and limits

All times below are UTC or explicitly identified media timestamps. Manifest and
packet evidence takes precedence over filename clocks and filesystem creation
times. The intended old implementation is the local `capture_lab` checkout, build
`capture-v0.5.35`, not the simpler legacy GitHub recorder mentioned in #49's body.

| Fact | Old recorder | Current recorder |
| --- | --- | --- |
| Creator | `gracie.kf` | `gracie.kf` |
| Room | `7690364623728102175` | `7690364623728102175` |
| Session start | 2026-09-27 23:43:57.447273 | 2026-09-27 23:43:57.472334 |
| Identity | `2026-09-27_23-43-57_90054f371a13_capture-v0.5.35` | UUID `ea288e43-61af-4189-b068-2f57a18b7539` |
| Initial selected source | `origin`, FLV, `mobile:sdk-main` | `hd1`, FLV, `flv_pull_url` |
| Initial configured dimensions | 960x1920 | 640x1280 |
| Surviving input evidence | 15 stream-copy `final/original-parts/part-*.mp4` files; raw-signature and event records | Two retained `part-*.flv`, manifest and connections |
| Final being examined | `final/original.mp4`, NVENC, 1080x1920 | `gracie.kf-20260928-014356.mp4`, stream copy, 640x1280 |
| Actual final duration | 2158.626375 s (35:58.626) | 6167.444 s (1:42:47.444) |
| Actual final video frames | 42,753 | 130,159 |

Old session root:
`C:\Users\Leandro\Desktop\antigravity\TikREC\runs\gracie.kf\2026-09-27_23-43-57_90054f371a13_capture-v0.5.35`.
Current originals are under `C:\Users\Leandro\Videos`, with the above MP4 stem
and matching `.parts` directory.

The old session's `raw` and `safety-raw` directories are absent. The corresponding
archive under
`G:\My Drive\03 Projects & Tech\TikREC & TikTok\TikREC-Archive\gracie.kf`
also has no raw directory for this session. Surviving remuxed parts are useful
evidence before normalization, but **are not untouched FLV or HTTP source**:
the old remux itself uses `discardcorrupt`. Historical raw-signature hashes prove
what the old finalizer recorded, not what is now available to decode.

The surviving old `original.mp4` has subsequently been reconstructed. Its actual
size is 674,772,624 bytes, whereas historical `finalization.json` describes
674,764,894 bytes. This report uses the actual file's hash, FFprobe metadata,
decoder results, and `reconstruct.log`, not that stale output-size claim.
The reconstruction command uses the surviving `original-parts` and the same
NVENC normalization family. No old finalizer was invoked during this task.

## Timeline alignment and the missing interval

Packet hashes independently confirm that these are the same LIVE. In the
approximately 579--611-second tail of old input part 0, 741 AAC packet payloads
match current retained audio exactly, with identical DTS. The next old input
part has 311 matching AAC payloads with this constant relation:

```text
current part-0001 DTS = old original-parts/part-0001 DTS + 627.447 seconds
current MP4 first-part DTS = current retained DTS - 0.006 seconds
current source clock = current retained DTS + 42.863 seconds
```

Old part 0's last matched audio packet is at current retained 611.030 s. Old
part 1's first matched audio packet is at current retained 627.460 s. Their
16.430-second separation matches the old `reconnect_source_gap` record.
Thus current MP4 10:15 maps to retained 615.006 s, **inside the old capture gap**.
No old raw, remuxed part, or final frame for that moment can be compared.

Both old input part 0 at 610 s and current retained input at 610 s show the same
healthy one-person scene. Old input part 1 around source-equivalent retained
630 s shows a healthy two-person composition. Old final MP4 at its own 615 s
also shows that later composition; concatenation has collapsed the capture gap.
Comparing final MP4s at identical elapsed times would compare different moments.

Old event records contain 1,886 primary in-band configuration rejections, 131
rendition-fallback events, 15 useful primary parts, and eight safety parts.
Redundant coverage assembly failed with `no playable redundant capture
observations were found`; there is no evidence that the safety track restored
the missing interval. The historical health report marks capture completeness
RED and logs 13 source gaps totaling 2901.419 s, largest 1728.704 s. These logged
gaps do not account for all missing tail coverage. The final's roughly 35% of
current retained duration must not be presented as equivalent LIVE completeness.

## Configuration, IDR and packet evidence

Every current retained part starts with exactly one AVC configuration. Both
configuration payloads have SHA-256
`870a4f92a24b18d64bad87ae74a49a489803f331bc0e61cdcee57c2972c6521e`,
describing 640x1280. Full byte scans found no later AVC header, in-band SPS/PPS,
malformed length-prefixed NAL, or backward media DTS in either part. Part 1
contains 1,053 IDR access units, 39,700 non-IDR slice NALs, and 5,348 SEI NALs.
The second part is an identical-configuration reconnect, not a resolution roll.

The relevant SEI announcements in current part 1 are:

| Retained DTS (s) | Source DTS (s) | Retained PTS (s) | Announced push geometry | Boundary |
| --- | --- | --- | --- | --- |
| 0.000 | 42.863 | Initial media | 960x1920 | IDR, configured 640x1280 |
| 611.062 | 653.925 | 611.178 | 720x1280 | IDR, no new AVC configuration |
| 611.598 | 654.461 | 611.750 | 1080x1920 | IDR, no new AVC configuration |
| 613.782 | 656.645 | 613.915 | 720x1280 | IDR, no new AVC configuration |
| 617.446 | 660.309 | 617.580 | 1080x1920 | IDR, no new AVC configuration |

These are actual NAL type 5 boundaries, not just FLV keyframe flags. The first
transition tag payload has SHA-256
`25d630fdd3b90b6f22aaf4c3d8573e6deecf51cd1dbbaa9a6b2a70bda4ffcf77`.
Later push announcements include 960x1920 at retained 1308.330 s and further
720/1080 changes; the retained AVC record still does not change.

Old input 0 was configured 960x1920, with event-recorded configuration fingerprint
`4ef216fc4bd086fe5105c260acf4cd11426d7a8d667c0a46d7f1c8eae13ec7e1`.
It stopped with maximum retained source timestamp 653.897 s. The very next
dimensions announcement is the 653.925-second event above; the old callback
reported `no_exact_candidate_header_decoded_cleanly`. It refused to retain that
access unit, then attempted `uhd`, `sd`, `SD2`, `ld`, and other routes before
retaining `origin` again, now configured 1080x1920, at 23:54:27.508798 UTC.

The retained old configuration sequence from event/part records is:

```text
part 0       960x1920
parts 1--3   1080x1920
part 4       720x1280
parts 5--7   1080x1920
parts 8--10  960x1920
parts 11--14 720x1280
```

There is no shared recorded 640-to-720 AVC configuration sequence. Short rejected
old attempts sometimes opened 640x1280 or 720x1280 configurations, but they are
not the retained video sequence feeding this final. The old program saw publisher
push changes and changed connections/renditions; current retained those
announcements inside a fixed 640x1280 configuration.

In the aligned window, zero video packet hashes match old input 0 or 1 against
current retained video, while the AAC matches above do. Different AVC dimensions
and video hashes establish materially different video bytes. This rules out
treating old/current outputs as a same-video-input finalizer A/B comparison.

## Decoder and bounded replay results

FFmpeg/FFprobe build: `N-124716-g054dffd133-20260531`. Decoder checks use
`ffprobe -v error -show_frames`, not FFmpeg's null muxer. A zero process exit
does not override decoder messages. Late-SEI notices are recorded separately
from genuine H.264 macroblock/reference failures.

| Check | Frames / packets examined | Result |
| --- | --- | --- |
| Old surviving input 0, full video/audio decode | 15,257 video; 14,301 audio | Zero decoder error lines |
| Old surviving input 1, full video decode | 200 video | Zero decoder error lines; sampled composition visually healthy |
| Old actual final, full video/audio decode | 42,753 video; 101,186 audio | Zero decoder error lines |
| Current retained part 1, seek 580--650 s | 1,367 video, starting at preceding IDR 579.522 PTS | 402 decoder error lines; severe columns at 615 s |
| Current final, corresponding window | 1,367 video | Same 402 error lines and visible columns |
| Current actual final, full video/audio decode | 130,159 video; 144,530 audio | 25,294 decoder error lines |
| Current packet window, seek 580--690 s | 1,967 video; 2,587 audio | No demux packet has a corrupt flag |
| Same packet window with `+genpts+discardcorrupt` | Same counts | Entire packet-record list, timestamps and hashes identical |

The disposable replay FLV copies exact current retained tag payloads from IDR
DTS 589.319 through 650.000 s; its source offset starts at byte 78,787,639.
It inserts the cached original AVC/AAC headers and subtracts 589,319 ms from
tag timestamps. No original is rewritten. Full decoding of this 60.681-second
excerpt returns 1,124 video frames with 404 genuine decoder error lines.

Two bounded NVENC runs use the old options: PTS reset, 1080x1920 scale/pad,
`setsar=1`, audio resampling, `h264_nvenc` p6/hq VBR CQ 18, VFR,
1/1000 encoder time base, AAC 128k, negative-timestamp normalization and 90 kHz
MP4 video timescale. The runs differ only in whether the input format flags
`+genpts+discardcorrupt` are enabled.

Both runs produce 1,124 video frames, zero output decoder errors, and identical
decoded video frame hashes. Every output PTS equals the corresponding decoded
input PTS plus 0.039 s. There is no frame-count loss, selective PTS omission, or
extra time collapse in this excerpt. Encoder I/P/B choices change, as expected.
Both outputs visibly retain the columns at source-equivalent 615 s. Scaling,
concealment and re-encoding cannot reconstruct this missing image information.

Across the surviving 15 old remuxed inputs there are 42,724 video packets and
50,512 AAC packets; the actual normalized final has 42,753 video frames and
101,186 AAC packets. The net 29 additional video frames and audio repacketization
are consistent with the old filter's padding and resampling. They do not prove
that no individual frame was dropped elsewhere. Exact raw-to-remux packet loss
cannot be measured without the absent old FLVs. In particular, no evidence
attributes the missing 16.43-second interval to finalizer `discardcorrupt`:
the old capture had already stopped retaining it.

FFmpeg documents `discardcorrupt` as a format flag for corrupted packets and
`genpts` as generating missing presentation timestamps from decode timestamps.
These are not a guarantee that H.264 slice damage is detected by the demuxer or
that re-encoding repairs imagery. See the official
[format options](https://ffmpeg.org/ffmpeg-formats.html#Format-Options).
The concrete packet and replay results above determine their effect here.

## Supplement with available old FLVs

The only recent matching Gracie session with locally available old FLVs at
inspection was old `2026-09-30_06-44-25_29878c354dba_capture-v0.5.35`, room
`7691214478142212895`, started 06:44:26.001781 UTC, matching current UUID
`05f3e981-b713-403c-9bef-198282ec5766`, stem `gracie.kf-20260930-084426`,
started 06:44:27.855050 UTC.

This is a **healthy control, not a replacement corrupt transition case**.
The seven old primary FLVs (2,713,739,846 bytes) all configure 960x1920;
the four current retained FLVs all configure 640x1280. Complete structural scans
of all eleven find no changed AVC header, in-band SPS/PPS, malformed NAL lengths,
or backward media timestamps. Old event records have no dimensions rejection.

Old raw part 0's 1158.160--1198.079 PTS window decodes 999 video frames without
errors. Bounded probes of its already published `original.mp4`, current retained
part 1, and current final around 1160--1230 s also decode without errors.
Stills near 1170 s from all four stages show the same healthy one-person scene.
The old final is 6994.951 s with 174,790 video frames at 960x1920; current is
7013.649 s with 175,025 at 640x1280. Different reconnect coverage still prevents
whole-final frame counts from being a controlled loss comparison.
The old delivery finalizer was still working on its HD derivative; this task
examined the stable published original and completed FLVs and did not wait for,
interrupt, or invoke that finalizer. No battle acceptance claim follows from
this control.

## Answers and next experiment

1. **Same LIVE/source rendition?** Same exact issue-#28 LIVE, proven by room,
   same-second start and 1,052 shared AAC payloads. Different video renditions,
   configuration sequences and packet payloads; different retained coverage.
2. **Corrupt before old finalization?** The raw-FLV question is unresolved
   because those files are absent. The surviving inputs immediately before/after
   the gap decode cleanly and sampled images are healthy. The corrupt 10:15
   moment was not retained. Available control old FLV also decodes cleanly in
   the examined window.
3. **Corrupt before current finalization?** Yes: the retained FLV has the same
   columns and decoder failures as the MP4. Without HTTP raw, this does not
   prove TikTok sent those exact damaged bytes.
4. **What does old finalization change/drop?** It resets part clocks, collapses
   gaps between retained inputs, normalizes dimensions, pads timing, resamples
   audio and re-encodes. The damaged-input replay drops no decoded video frames
   and its format flag drops no examined packets. The important 16.43-second
   omission happened during capture, before finalization.
5. **Transition hypothesis supported?** Yes, as an association with publisher
   push-geometry announcements at IDRs and the old capture refusal, at the
   reported battle entry. No 640/720 AVC switch was stored by current TikREC.
   The scene changes from one person to two; precise TikTok battle state still
   depends on the owner's observation, not an independent battle marker.
6. **Most likely reason the old final looks clean?** A cleaner/different retained
   video rendition combined with refusal and omission of the damaged interval,
   followed by gap-collapsing assembly. Confidence is strong for omission and
   rendition difference here; the missing old raw prevents assigning every
   potential cause. The proposed `discardcorrupt`/re-encode repair mechanism is
   not supported for this damaged current window.
7. **Next narrow experiment/product work?** Preserve untouched HTTP raw for an
   owner-authorized natural Gracie recurrence, with current retained input and
   a simultaneous known rendition when available. Compare bytes and exact
   AVC/SEI/IDR context before trying header changes or dropping anything. #48's
   opt-in watcher raw-copy is the existing bounded product item that supplies
   this evidence; #13 remains the separate rendition-selection policy item.
   Reuse this bounded normalization comparison if a matching damaged raw window
   appears. Do not copy the old retry storm, silent omission, or guessed-header
   policy into current TikREC. Preserve recovery, identity, two-slot ownership,
   retained evidence, validation and auditability.

## Preservation and reproducibility

New scripts, excerpts, stills, frame hashes and logs are exclusively under
`C:\Users\Leandro\TikREC-diagnostics\issue-49-20260930`, outside both recording
roots. Key files: `survey.json`, `new28-push-transitions.json`,
`original-stamps.json`, `preservation-verification.json`, packet/frame JSONs,
`clip-timeline.json`, `nvenc-*.command.json`, `nvenc-*.framehash`,
`old28-actual-reconstruct-command.txt`, and `comparison-contact-sheet.jpg`.
`control-contact-sheet.jpg` records the healthy four-stage control sample.
The local helper scripts record the exact commands; media and verbose diagnostic
files are intentionally not committed. This report persists the findings and
bounded reproduction parameters in GitHub.

Representative packet and decoder commands (repeat packet inspection with
`-fflags +genpts+discardcorrupt` before the input to compare the flag):

```text
ffprobe -v error -read_intervals 580%690 -show_packets -show_data_hash sha256 -show_entries packet=stream_index,pts_time,dts_time,duration_time,size,flags,data_hash -of json CURRENT_PART_1.flv
ffprobe -v error -read_intervals 580%650 -select_streams v:0 -show_frames -show_entries frame=pts_time,pkt_dts_time,best_effort_timestamp_time,duration_time,key_frame,pict_type,width,height -of json CURRENT_PART_1.flv
ffprobe -v error -show_frames -show_entries frame=media_type -of csv=p=0 ORIGINAL.mp4
```

Seek intervals may start at an earlier IDR; the table records the actual frame
coverage, not an assumed exact start. For the replay, generate the exact-tag
excerpt at the byte/time boundary above with the original cached AVC/AAC headers,
then use this command twice, omitting the format flags for the second run:

```text
ffmpeg -nostdin -n -hide_banner -loglevel warning -fflags +genpts+discardcorrupt -i EXCERPT.flv
  -vf "settb=AVTB,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
  -af "asettb=AVTB,asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0"
  -c:v h264_nvenc -preset p6 -tune hq -rc vbr -cq 18 -b:v 0 -pix_fmt yuv420p
  -fps_mode vfr -enc_time_base:v 1:1000 -c:a aac -b:a 128k
  -avoid_negative_ts make_zero -movflags +faststart -video_track_timescale 90000 DISPOSABLE.mp4
```

The displayed replay command is wrapped for readability, not shell continuation
syntax. Use distinct disposable destinations outside recording roots. Compare
decoded pixel hashes with `ffmpeg -i DISPOSABLE.mp4 -map 0:v:0 -c:v rawvideo
-f framehash -`, and inspect stills at input-relative 25.681 s (retained 615 s).

Forty-two selected original files, totaling 10,099,373,768 bytes, passed repeated
SHA-256, size and modification-time checks. No source media, service,
configuration, production code, or #51 retention archive was changed.

| Original | SHA-256 |
| --- | --- |
| Current issue-#28 MP4 | `64096acb4f1027b5c6b10f63959a17fda6c4e323661afbe4fad78d7557bdb249` |
| Current issue-#28 FLV 1 | `2a0745c350568d17529c0df3d7206544b321e60a045f61a6df34864dc64849eb` |
| Current issue-#28 FLV 2 | `5498254988136f840e29b0e0c54ab611bf2d0e31d43d67abafac108d86a1fd1b` |
| Old issue-#28 actual final | `7869c8aa383faa071d355bfe7df4419d2612469d6c617f0bf8da9f59d9de3214` |
| Old surviving input 0 | `a4e163acba1546aceb3215785e495965c0be2aa0041a9169de42b381e9252c71` |
| Old surviving input 1 | `169e95fce4882f9e4eefd153ece2cf678d8a506d24a03f2671b7d79bad50d26a` |
| Old healthy-control FLV 0 | `25fd969b80b68aba789725746cc7e8edf7c695ed4c46954e2eaebbe3e0107f32` |

#49's bounded comparison is complete with the raw-input limitation documented.
#28 remains open and non-blocking; #51 remains paused awaiting a naturally idle,
stable root. The retention real-media gate remains unpassed, its one-deletion
authorization unused, and its age rule unset. v0.10.0 remains the current release;
v0.11.0 remains unreleased. No release blocker or media policy was relaxed.
