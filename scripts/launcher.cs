using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;

namespace SignOfTheCrossLauncher
{
    static class Program
    {
        static bool IsPortOpen(string host, int port)
        {
            try
            {
                using (var client = new TcpClient())
                {
                    var result = client.BeginConnect(host, port, null, null);
                    var success = result.AsyncWaitHandle.WaitOne(TimeSpan.FromMilliseconds(400));
                    if (!success) return false;
                    client.EndConnect(result);
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }

        static string FindPython()
        {
            string laragonPy = @"C:\laragon\bin\python\python-3.13\python.exe";
            if (File.Exists(laragonPy)) return laragonPy;
            return "python.exe";
        }

        static void StartBackgroundPython(string pythonExe, string scriptPath, string workDir)
        {
            if (!File.Exists(scriptPath)) return;
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = "\"" + scriptPath + "\"",
                WorkingDirectory = workDir,
                CreateNoWindow = true,
                UseShellExecute = false,
                WindowStyle = ProcessWindowStyle.Hidden
            };
            Process.Start(psi);
        }

        static void OpenAppWindow(string url)
        {
            string[] edgePaths = new string[]
            {
                @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Google\Chrome\Application\chrome.exe"
            };
            foreach (var browser in edgePaths)
            {
                if (File.Exists(browser))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = browser,
                        Arguments = "--app=" + url + " --window-size=1480,920",
                        UseShellExecute = true
                    });
                    return;
                }
            }
            Process.Start(new ProcessStartInfo { FileName = url, UseShellExecute = true });
        }

        [STAThread]
        static void Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string pythonExe = FindPython();
            string appPy = Path.Combine(baseDir, "app.py");
            string sentinelPy = Path.Combine(baseDir, "agent", "sentinel.py");

            if (!IsPortOpen("127.0.0.1", 8765))
            {
                StartBackgroundPython(pythonExe, appPy, baseDir);
                StartBackgroundPython(pythonExe, sentinelPy, baseDir);
                for (int i = 0; i < 20; i++)
                {
                    if (IsPortOpen("127.0.0.1", 8765)) break;
                    Thread.Sleep(250);
                }
            }

            OpenAppWindow("http://127.0.0.1:8765");
        }
    }
}
