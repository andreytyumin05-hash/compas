using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace CompasAiCad
{
    [ComVisible(true)]
    [Guid("8D8B1A6E-4B0B-4D3C-8D72-7E8B9A0F1C31")]
    [ProgId("CompasAiCad.Panel")]
    [ClassInterface(ClassInterfaceType.AutoDual)]
    public sealed class Library
    {
        private static readonly object Sync = new object();
        private static PanelForm _form;
        private static PropertyManagerBackend _native;

        [return: MarshalAs(UnmanagedType.BStr)] public string GetLibraryName() => "CompasAiCad";
        [return: MarshalAs(UnmanagedType.BStr)] public string DisplayLibraryName() => "AI CAD";
        public bool IsOnApplication7() => true;

        [return: MarshalAs(UnmanagedType.BStr)]
        public string ExternalMenuItem(short number, ref short itemType, ref short command)
        {
            if (number == 1) { itemType = 1; command = 1; return "Панель AI CAD"; }
            itemType = 3; command = -1; return string.Empty;
        }

        public void ExternalRunCommand([In] short command, [In] short mode,
            [In, MarshalAs(UnmanagedType.IDispatch)] object kompas_)
        {
            if (command != 1) return;
            try { ShowInsideKompas(kompas_); }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "AI CAD: не удалось встроить панель в КОМПАС.\n\n" + ex.Message +
                    "\n\nОтдельное окно Windows намеренно не используется.",
                    "Compas AI CAD", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void ShowInsideKompas(object kompas)
        {
            lock (Sync)
            {
                if (_form != null && !_form.IsDisposed && _native != null && _native.IsReady)
                {
                    try { _form.FocusTaskBox(); } catch { }
                    try { _native.ShowAgain(); } catch { }
                    return;
                }

                if (_form != null)
                {
                    try { if (!_form.IsDisposed) _form.Dispose(); } catch { }
                    _form = null;
                }
                if (_native != null)
                {
                    try { _native.ReleaseAll(); } catch { }
                    _native = null;
                }

                var form = new PanelForm();
                form.PrepareAsChildHost();
                IntPtr hwnd = form.Handle;
                if (hwnd == IntPtr.Zero)
                    throw new InvalidOperationException("Не удалось создать HWND панели.");

                var backend = new PropertyManagerBackend();
                if (!backend.TryOpen(kompas, hwnd, form.PreferredWidth, form.PreferredHeight))
                {
                    string detail = backend.LastError ?? "неизвестная ошибка PropertyManager";
                    try { form.Dispose(); } catch { }
                    throw new InvalidOperationException(detail);
                }

                form.Visible = true;
                form.SetHostMode(true);
                _form = form;
                _native = backend;
            }
        }

        public void ClosePanel()
        {
            lock (Sync)
            {
                try { _native?.ReleaseAll(); } catch { }
                _native = null;
                try { if (_form != null && !_form.IsDisposed) _form.Dispose(); } catch { }
                _form = null;
            }
        }

        private sealed class PanelForm : Form
        {
            public int PreferredWidth { get { return 280; } }
            public int PreferredHeight { get { return 480; } }

            private readonly TextBox _task;
            private readonly Label _status;
            private readonly Label _modeHint;
            private readonly Button _create, _edit, _save, _clear;
            private readonly ProgressBar _progress;
            private bool _running;

            public PanelForm()
            {
                Text = "AI CAD";
                ClientSize = new Size(PreferredWidth, PreferredHeight);
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                ControlBox = false;
                TopMost = false;
                BackColor = Color.FromArgb(245, 246, 248);
                Font = new Font("Segoe UI", 9F);

                var header = new Panel { Dock = DockStyle.Top, Height = 40, BackColor = Color.FromArgb(32, 90, 167), Padding = new Padding(10, 8, 10, 6) };
                header.Controls.Add(new Label { Text = "AI CAD", Dock = DockStyle.Fill, ForeColor = Color.White, Font = new Font("Segoe UI", 11F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft });

                _modeHint = new Label { Text = "Вкладка Панели свойств КОМПАС (не отдельное окно).", Dock = DockStyle.Top, Height = 36, Padding = new Padding(10, 6, 10, 2), ForeColor = Color.FromArgb(60, 60, 60) };
                var taskLabel = new Label { Text = "Задача", Dock = DockStyle.Top, Height = 20, Padding = new Padding(10, 2, 10, 0), Font = new Font("Segoe UI", 8.5F, FontStyle.Bold) };

                var taskHost = new Panel { Dock = DockStyle.Top, Height = 150, Padding = new Padding(10, 0, 10, 6) };
                _task = new TextBox { Multiline = true, AcceptsReturn = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill, Font = new Font("Segoe UI", 9.5F), BorderStyle = BorderStyle.FixedSingle };
                taskHost.Controls.Add(_task);

                var buttons = new TableLayoutPanel { Dock = DockStyle.Top, Height = 72, ColumnCount = 2, RowCount = 2, Padding = new Padding(8, 2, 8, 2) };
                buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50F));
                buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50F));
                buttons.RowStyles.Add(new RowStyle(SizeType.Percent, 50F));
                buttons.RowStyles.Add(new RowStyle(SizeType.Percent, 50F));
                _create = MakeButton("Создать");
                _edit = MakeButton("Изменить");
                _save = MakeButton("Сохранить");
                _clear = MakeButton("Очистить");
                _create.Click += async (s, e) => await RunAsync("create");
                _edit.Click += async (s, e) => await RunAsync("edit");
                _save.Click += async (s, e) => await RunAsync("save");
                _clear.Click += (s, e) => { _task.Clear(); SetStatus("Готово", false); };
                buttons.Controls.Add(_create, 0, 0);
                buttons.Controls.Add(_edit, 1, 0);
                buttons.Controls.Add(_save, 0, 1);
                buttons.Controls.Add(_clear, 1, 1);

                _progress = new ProgressBar { Dock = DockStyle.Top, Height = 5, Style = ProgressBarStyle.Marquee, MarqueeAnimationSpeed = 0 };
                var statusHeader = new Label { Text = "Статус", Dock = DockStyle.Top, Height = 20, Padding = new Padding(10, 4, 10, 0), Font = new Font("Segoe UI", 8.5F, FontStyle.Bold) };
                _status = new Label { Text = "Готово.", Dock = DockStyle.Fill, Padding = new Padding(10, 2, 10, 10), ForeColor = Color.FromArgb(40, 40, 40) };

                Controls.Add(_status);
                Controls.Add(statusHeader);
                Controls.Add(_progress);
                Controls.Add(buttons);
                Controls.Add(taskHost);
                Controls.Add(taskLabel);
                Controls.Add(_modeHint);
                Controls.Add(header);
            }

            private static Button MakeButton(string text) =>
                new Button { Text = text, Dock = DockStyle.Fill, Margin = new Padding(3), FlatStyle = FlatStyle.System };

            public void PrepareAsChildHost()
            {
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                ControlBox = false;
                Size = new Size(PreferredWidth, PreferredHeight);
            }

            public void SetHostMode(bool insideKompas)
            {
                _modeHint.Text = insideKompas
                    ? "Вкладка Панели свойств КОМПАС. 3D-вид не перекрывается."
                    : "Режим встраивания.";
            }

            public void FocusTaskBox() { try { _task.Focus(); } catch { } }

            private void SetStatus(string text, bool error)
            {
                _status.Text = text ?? "";
                _status.ForeColor = error ? Color.FromArgb(160, 30, 30) : Color.FromArgb(40, 40, 40);
            }

            private void SetBusy(bool busy)
            {
                _running = busy;
                _create.Enabled = _edit.Enabled = _save.Enabled = _clear.Enabled = !busy;
                _progress.MarqueeAnimationSpeed = busy ? 35 : 0;
            }

            private async Task RunAsync(string action)
            {
                if (_running) return;
                if (action != "save" && string.IsNullOrWhiteSpace(_task.Text))
                {
                    SetStatus("Введите описание детали или команду изменения.", true);
                    return;
                }
                SetBusy(true);
                SetStatus(action == "save" ? "Сохранение…" : "Обработка…", false);
                string repo = FindRepo();
                string python = FindPython(repo);
                string taskFile = Path.Combine(Path.GetTempPath(), "compas_ai_cad_" + Guid.NewGuid().ToString("N") + ".txt");
                try
                {
                    if (action != "save") File.WriteAllText(taskFile, _task.Text.Trim(), new UTF8Encoding(false));
                    ProcessResult result = await Task.Run(() => ExecutePython(repo, python, action, taskFile));
                    string message = ExtractUiMessage(result.Output, result.Error, result.ExitCode, action);
                    bool err = result.ExitCode != 0 || LooksLikeError(message);
                    SetStatus(message, err);
                }
                catch (Exception ex) { SetStatus(SanitizeMessage(ex.Message), true); }
                finally
                {
                    try { if (File.Exists(taskFile)) File.Delete(taskFile); } catch { }
                    SetBusy(false);
                }
            }

            private static bool LooksLikeError(string message)
            {
                if (string.IsNullOrEmpty(message)) return false;
                return message.IndexOf("ошиб", StringComparison.OrdinalIgnoreCase) >= 0
                    || message.IndexOf("error", StringComparison.OrdinalIgnoreCase) >= 0
                    || message.IndexOf("не выполнен", StringComparison.OrdinalIgnoreCase) >= 0;
            }

            private static ProcessResult ExecutePython(string repo, string python, string action, string taskFile)
            {
                string args = action == "save"
                    ? "-m addon.bridge save"
                    : string.Format("-m addon.bridge {0} --task-file \"{1}\"", action, taskFile);
                var psi = new ProcessStartInfo
                {
                    FileName = python,
                    Arguments = args,
                    WorkingDirectory = repo,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };
                psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                psi.EnvironmentVariables["COMPAS_UI"] = "1";
                psi.EnvironmentVariables["COMPAS_REPO"] = repo;
                using (var proc = Process.Start(psi))
                {
                    if (proc == null) return new ProcessResult(3, "", "Не удалось запустить Python.");
                    string output = proc.StandardOutput.ReadToEnd();
                    string error = proc.StandardError.ReadToEnd();
                    if (!proc.WaitForExit(30 * 60 * 1000))
                    {
                        try { proc.Kill(); } catch { }
                        return new ProcessResult(4, output, "Таймаут 30 мин.");
                    }
                    return new ProcessResult(proc.ExitCode, output, error);
                }
            }

            private static string ExtractUiMessage(string output, string error, int exitCode, string action)
            {
                try
                {
                    var serializer = new JavaScriptSerializer();
                    string[] lines = (output ?? "").Replace("\r", "").Split('\n');
                    for (int i = lines.Length - 1; i >= 0; i--)
                    {
                        string line = lines[i].Trim();
                        if (!line.StartsWith("{")) continue;
                        var data = serializer.DeserializeObject(line) as Dictionary<string, object>;
                        if (data == null) continue;
                        if (data.ContainsKey("message"))
                        {
                            string msg = Convert.ToString(data["message"]);
                            if (!string.IsNullOrWhiteSpace(msg)) return SanitizeMessage(msg);
                        }
                        bool ok = data.ContainsKey("ok") && Convert.ToBoolean(data["ok"]);
                        if (ok) return action == "edit" ? "Модель обновлена." : "Готово.";
                        if (data.ContainsKey("error")) return SanitizeMessage(Convert.ToString(data["error"]));
                    }
                }
                catch { }
                string combined = ((error ?? "") + "\n" + (output ?? "")).Trim();
                if (!string.IsNullOrEmpty(combined))
                {
                    string shortMsg = SanitizeMessage(combined);
                    if (!string.IsNullOrEmpty(shortMsg)) return shortMsg;
                }
                if (exitCode == 0) return action == "edit" ? "Модель обновлена." : "Готово.";
                return "Операция не выполнена (код " + exitCode + ").";
            }

            private static string SanitizeMessage(string raw)
            {
                if (string.IsNullOrWhiteSpace(raw)) return "";
                string[] lines = raw.Replace("\r", "").Split('\n');
                var kept = new List<string>();
                foreach (string line in lines)
                {
                    string t = line.Trim();
                    if (t.Length == 0) continue;
                    string low = t.ToLowerInvariant();
                    if (low.Contains("traceback") || low.Contains("file \"") || low.Contains("win32com") || low.Contains("com_error"))
                        continue;
                    kept.Add(t);
                    if (kept.Count >= 4) break;
                }
                string result = string.Join(" ", kept);
                if (result.Length > 400) result = result.Substring(0, 397) + "…";
                return result;
            }

            private static string FindPython(string repo)
            {
                string configured = Environment.GetEnvironmentVariable("COMPAS_PYTHON");
                string[] candidates = { Path.Combine(repo, "venv", "Scripts", "python.exe"), configured ?? "", "python.exe" };
                foreach (string item in candidates)
                {
                    if (string.IsNullOrWhiteSpace(item)) continue;
                    if (Path.IsPathRooted(item)) { if (File.Exists(item)) return item; }
                    else if (item == "python.exe") return item;
                }
                return "python.exe";
            }

            private static string FindRepo()
            {
                string configured = Environment.GetEnvironmentVariable("COMPAS_REPO");
                if (!string.IsNullOrWhiteSpace(configured) && File.Exists(Path.Combine(configured, "agent", "build.py")))
                    return configured;
                DirectoryInfo dir = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
                while (dir != null)
                {
                    if (File.Exists(Path.Combine(dir.FullName, "agent", "build.py"))) return dir.FullName;
                    dir = dir.Parent;
                }
                return Directory.GetCurrentDirectory();
            }
        }

        private readonly struct ProcessResult
        {
            public ProcessResult(int exitCode, string output, string error)
            {
                ExitCode = exitCode;
                Output = output ?? string.Empty;
                Error = error ?? string.Empty;
            }
            public int ExitCode { get; }
            public string Output { get; }
            public string Error { get; }
        }
    }
}
