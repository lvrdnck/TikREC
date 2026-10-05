"""Disposable native validator fixture compiled with the existing Windows compiler."""

import shutil
import subprocess
from pathlib import Path

SOURCE = r'''
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
class Validator {
 static int Main(string[] args) {
  string home = Path.GetDirectoryName(typeof(Validator).Assembly.Location);
  string[] config = File.ReadAllLines(Path.Combine(home, "validator-config.txt"));
  string mode = config[0];
  if (args.Length == 1 && args[0] == "--leaf") {
   EventWaitHandle.OpenExisting(config[2]).Set();
   EventWaitHandle.OpenExisting(config[3]).WaitOne();
   return 0;
  }
  bool decode = Array.IndexOf(args, "-show_frames") >= 0;
  if (decode && (mode == "barrier" || mode == "unknown")) {
   EventWaitHandle.OpenExisting(config[2]).Set();
   EventWaitHandle.OpenExisting(config[3]).WaitOne();
  }
  if (decode && mode == "long") Thread.Sleep(31100);
  if (decode && mode == "descendant") {
   ProcessStartInfo leaf = new ProcessStartInfo(typeof(Validator).Assembly.Location, "--leaf");
   leaf.UseShellExecute = false;
   Process.Start(leaf);
   return 0;
  }
  if (decode && mode == "diagnostic") {
   Console.Error.Write(new string('x', 20000) + "\nvalidation decode failed");
   return 0;
  }
  if (decode && mode == "utf8") {
   Stream stderr = Console.OpenStandardError();
   stderr.WriteByte(0xff); return 0;
  }
  if (decode && mode == "nonzero") return 23;
  string command = "";
  foreach (string arg in args) command += "\"" + arg.Replace("\"", "\\\"") + "\" ";
  ProcessStartInfo probe = new ProcessStartInfo(config[1], command);
  probe.UseShellExecute = false;
  Process process = Process.Start(probe);
  process.WaitForExit(); return process.ExitCode;
 }
}
'''


def native_validator(root, mode, names=()):
    """Build an explicit disposable executable; install or change no runtime."""
    root.mkdir()
    source, executable = root / "validator.cs", root / "validator.exe"
    source.write_text(SOURCE)
    compiler = Path("C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe")
    assert compiler.is_file(), "existing Windows fixture compiler unavailable"
    subprocess.run([str(compiler), "/nologo", "/target:exe", "/out:" + str(executable), str(source)],
                   check=True, capture_output=True, timeout=30)
    (root / "validator-config.txt").write_text("\n".join([mode, str(Path(shutil.which("ffprobe")).resolve()), *names]))
    return executable
