"""Reproduce #52's bounded Windows-only comparison without production changes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess as sp
import sys
import time

from tikrec.finalize import finalize_parts
from tikrec.part_validation import validate_part
from tikrec.validation import validate_target
from tests.diagnostics.priority_windows import DiskMetrics, Metrics


def percentile(values, fraction):
    """Return an interpolated sample quantile, or None for unavailable samples."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (position - low)


def digest(path):
    """Hash only the named disposable fixture/output in bounded read chunks."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, value):
    """Persist experimental metadata outside the production recording roots."""
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def bounded_runner(command, **options):
    """Bound existing TikREC FFprobe checks without changing media options."""
    options["timeout"] = min(options.get("timeout", 30), 30)
    return sp.run(command, **options)


def check_media(path):
    """Preserve existing decoder/packet-DTS and deep output validation findings."""
    report = validate_target(path, deep=True, runner=bounded_runner).as_dict()
    if path.is_file():
        problems, warnings = validate_part(path, "ffprobe", bounded_runner)
        report["packet_problems"], report["packet_warnings"] = problems, warnings
    probe = bounded_runner([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
        "-show_entries", "stream=codec_name,codec_type,width,height,nb_read_frames,avg_frame_rate,time_base,start_time,duration:format=duration",
        "-of", "json", str(path)], capture_output=True, text=True, check=False) if path.is_file() else None
    if probe is not None:
        report["stream_probe"] = json.loads(probe.stdout)
        report["stream_probe_stderr"] = probe.stderr
    return report


def prepare(root, duration):
    """Generate only synthetic FLVs, retaining exact commands and input checks."""
    root.mkdir()
    commands = []
    for case in ("copy", "encode"):
        (root / case).mkdir()
    for index, size in enumerate(("1280x720", "1920x1080"), start=1):
        path = root / "encode" / f"part-{index:04}.flv"
        command = ["ffmpeg", "-nostdin", "-n", "-f", "lavfi", "-i",
                   f"testsrc2=size={size}:rate=30", "-f", "lavfi", "-i",
                   "sine=frequency=440:sample_rate=44100", "-t", str(duration),
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)]
        result = sp.run(command, capture_output=True, text=True, timeout=60)
        (root / f"fixture-{index}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        result.check_returncode()
        commands.append(command)
    for index in (1, 2):
        shutil.copyfile(root / "encode" / "part-0001.flv", root / "copy" / f"part-{index:04}.flv")
    inputs = {str(p.relative_to(root)): digest(p) for p in root.glob("*/*.flv")}
    validations = {case: check_media(root / case) for case in ("copy", "encode")}
    write_json(root / "fixtures.json", {"duration_per_part": duration, "commands": commands,
                                       "hashes": inputs, "validation": validations})
    if not all(v["passed"] for v in validations.values()):
        raise RuntimeError("Synthetic inputs failed existing TikREC checks; preserve diagnostics")


def stop_owned(process):
    """Terminate only the Popen object created by this experiment if still running."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except sp.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def run_trial(root, case, priority, trial, contenders):
    """Run an identical current-finalizer command with one controlled priority class."""
    directory = root / f"{case}-{trial}-{priority}"
    directory.mkdir()
    stop = directory / "stop"
    probe_path = directory / "probe.json"
    loads = []
    flags = sp.NORMAL_PRIORITY_CLASS if priority == "normal" else sp.BELOW_NORMAL_PRIORITY_CLASS
    fixture_hashes = json.loads((root / "fixtures.json").read_text(encoding="utf-8"))["hashes"]
    assert all(digest(root / path) == value for path, value in fixture_hashes.items())
    record = {"case": case, "priority": priority, "trial": trial,
              "logical_cpus": os.cpu_count(), "contenders": contenders, "proxy_hz": 60}
    try:
        for mode in ["cpu"] * contenders + ["probe"]:
            command = [sys.executable, "-m", "tests.diagnostics.priority_load", mode,
                       "--stop", str(stop), "--seconds", "90"]
            if mode == "probe":
                command += ["--result", str(probe_path)]
            process = sp.Popen(command, stdin=sp.DEVNULL, stdout=sp.DEVNULL,
                               stderr=sp.DEVNULL, creationflags=sp.NORMAL_PRIORITY_CLASS)
            loads.append(process)
        record["load_pids"] = [p.pid for p in loads]
        time.sleep(1)
        measured = {}

        def runner(command, **_):
            # Injection is provided by finalize_parts; no runtime module is modified.
            disk = DiskMetrics()
            samples = []
            process = None
            try:
                with (directory / "ffmpeg.stderr.txt").open("w", encoding="utf-8") as stderr:
                    started = time.perf_counter()
                    process = sp.Popen(command, stdin=sp.DEVNULL, stdout=sp.DEVNULL,
                                       stderr=stderr, creationflags=flags)
                    if "-f" in command and command[command.index("-f")+1] == "concat":
                        # Preserve the disposable manifest before the real finalizer removes it.
                        measured["concat_manifest_contents"] = Path(command[command.index("-i")+1]).read_text(encoding="utf-8")
                    metrics = Metrics(process)
                    while process.poll() is None:
                        value = metrics.sample()
                        value.update(t=time.perf_counter(), **disk.sample())
                        samples.append(value)
                        if value["physical_available"] < 4 * 1024**3 or (value["private_bytes"] or 0) > 2 * 1024**3:
                            raise RuntimeError("Test resource guard reached; stop only test-owned workloads")
                        if value["t"] - started > 60:
                            raise TimeoutError("FFmpeg trial reached its 60-second limit")
                        time.sleep(0.05)
                    ended = time.perf_counter()
                    last = metrics.sample()
                    observed = {v["priority_class"] for v in samples}
                    if observed != {flags}:
                        raise RuntimeError(f"Observed child priority mismatch: {observed}")
                stderr_text = (directory / "ffmpeg.stderr.txt").read_text(encoding="utf-8")
                measured.update(pid=process.pid, parent_pid=os.getpid(), command=command,
                                creationflags=flags, observed_priority_classes=sorted(observed),
                                started=started, ended=ended, elapsed=ended-started,
                                final_metrics=last, samples=samples, pdh_error=disk.error,
                                returncode=process.returncode)
                return sp.CompletedProcess(command, process.returncode, stderr=stderr_text)
            finally:
                if process is not None:
                    stop_owned(process)
                disk.close()

        decode = []
        started_total = time.perf_counter()
        output = finalize_parts(sorted((root / case).glob("*.flv")), directory / "final.mp4",
                                runner=runner, on_input_decode=decode.append)
        record.update(total_finalizer_seconds=time.perf_counter()-started_total,
                      input_decode=decode, ffmpeg=measured, output_sha256=digest(output))
    finally:
        stop.touch()
        for load in loads:
            try:
                load.wait(timeout=3)
            except sp.TimeoutExpired:
                stop_owned(load)
        if "ffmpeg" not in record:
            write_json(directory / "incomplete.json", record)
    proxy = json.loads(probe_path.read_text(encoding="utf-8"))
    active = [p for p in proxy if measured["started"] <= p["scheduled"] and p["end"] <= measured["ended"]]
    delay = [(p["wake"]-p["scheduled"])*1000 for p in active]
    response = [(p["end"]-p["scheduled"])*1000 for p in active]
    record["proxy_summary"] = {
        "samples": len(active), "wake_p95_ms": percentile(delay, .95),
        "response_p50_ms": percentile(response, .5), "response_p95_ms": percentile(response, .95),
        "response_p99_ms": percentile(response, .99), "response_max_ms": max(response, default=None),
        "missed_16_667ms": sum(r > 1000/60 for r in response),
    }
    record["validation"] = check_media(output)
    record["inputs_unchanged"] = all(digest(root / path) == value for path, value in fixture_hashes.items())
    samples = measured["samples"]
    cpu = measured["final_metrics"]["cpu_seconds"]
    record["resource_summary"] = {
        "ffmpeg_cpu_seconds": cpu,
        "ffmpeg_mean_machine_cpu_pct": cpu/measured["elapsed"]/os.cpu_count()*100,
        "peak_working_set": max(v["peak_working_set"] or 0 for v in samples),
        "peak_sampled_private": max(v["private_bytes"] or 0 for v in samples),
        "process_read_bytes": measured["final_metrics"]["read_bytes"],
        "process_write_bytes": measured["final_metrics"]["write_bytes"],
    }
    for field in ("disk_read_bps", "disk_write_bps", "disk_queue"):
        values = [v[field] for v in samples if field in v]
        record["resource_summary"]["mean_" + field] = statistics.mean(values) if values else None
        record["resource_summary"]["peak_" + field] = max(values, default=None)
    machine = []
    for previous, value in zip(samples, samples[1:]):
        total = value["system_total"] - previous["system_total"]
        if total > 0:
            machine.append(100 * (1 - (value["system_idle"]-previous["system_idle"])/total))
    record["resource_summary"].update(mean_machine_cpu_pct=statistics.mean(machine) if machine else None,
                                      peak_machine_cpu_pct=max(machine, default=None))
    write_json(directory / "result.json", record)
    if not record["inputs_unchanged"]:
        raise RuntimeError("Disposable inputs changed; retain experiment diagnostics")
    if not record["validation"]["passed"] or record["validation"]["packet_problems"]:
        raise RuntimeError("Output validation failed; retain experiment diagnostics")
    print(json.dumps({"run": directory.name, "elapsed": measured["elapsed"],
                      "proxy": record["proxy_summary"], "resources": record["resource_summary"]}), flush=True)


def main():
    """Require an external test root and bounded explicit experiment parameters."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=16)
    parser.add_argument("--case", choices=("copy", "encode"), default="encode")
    parser.add_argument("--priority", choices=("normal", "below"), default="normal")
    parser.add_argument("--trial", type=int, default=1)
    parser.add_argument("--contenders", type=int, default=8)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows-local experiment only")
    allowed = (Path.home() / "TikREC-tests").resolve()
    if not args.root.is_absolute() or not args.root.resolve().is_relative_to(allowed):
        parser.error("root must be under the user's external TikREC-tests directory")
    if not 1 <= args.duration <= 20 or not 0 <= args.contenders <= min(8, os.cpu_count()//4):
        parser.error("fixture duration/contention exceeds the experiment resource bound")
    if args.action == "prepare":
        prepare(args.root, args.duration)
    else:
        run_trial(args.root, args.case, args.priority, args.trial, args.contenders)


if __name__ == "__main__":
    main()
