using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
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
        private static Thread _uiThread;
        private static PropertyManagerBackend _native;
        private static bool _hostedNative;

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
            try { ShowPanel(kompas_); }
            catch (Exception ex)
            {
                MessageBox.Show("AI CAD: не удалось открыть встроенную панель.\n\n" + ex.Message,
                    "Compas AI CAD", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void ShowPanel(object kompas)
        {
            lock (Sync)
            {
                if (_form != null && !_form.IsDisposed && _hostedNative)
                {
                    try { _form.BeginInvoke((Action)(() => _form.FocusTaskBox())); } catch { }
                    return;
                }

                if (_form != null && !_form.IsDisposed)
                {
                    try { _form.BeginInvoke((Action)(() => _form.Close())); } catch { }
                    _form = null;
                }

                PanelForm form = CreateFormOnStaThread();
                _hostedNative = false;

                try
                {
                    _native = new PropertyManagerBackend();
                    form.PrepareAsChildHost();
                    if (!_native.TryOpen(kompas, form.Handle, form.PreferredWidth, form.PreferredHeight))
                    {
                        _native.Dispose();
                        _native = null;
                        try { form.BeginInvoke((Action)(() => form.Close())); } catch { }
                        throw new InvalidOperationException(
                            "КОМПАС не принял AI CAD как встроенную вкладку PropertyManager. " +
                            "Отдельное окно намеренно отключено: сначала исправляем нативную интеграцию.");
                    }

                    _hostedNative = true;
                    form.BeginInvoke((Action)(() =>
                    {
                        form.SetHostMode(true);
                        form.Show();
                        form.FocusTaskBox();
                    }));
                }
                catch
                {
                    try { _native?.Dispose(); } catch { }
                    _native = null;
                    _hostedNative = false;
                    throw;
                }
            }
        }

        private static PanelForm CreateFormOnStaThread()
        {
            var ready = new ManualResetEventSlim(false);
            PanelForm created = null;
            Exception error = null;
            _uiThread = new Thread(() =>
            {
                try
                {
                    Application.EnableVisualStyles();
                    Application.SetCompatibleTextRenderingDefault(false);
                    created = new PanelForm();
                    _form = created;
                    ready.Set();
                    Application.Run(created);
                }
                catch (Exception ex) { error = ex; ready.Set(); }
                finally
                {
                    lock (Sync)
                    {
                        if (ReferenceEquals(_form, created)) _form = null;
                        try { _native?.Dispose(); } catch { }
                        _native = null;
                        _hostedNative = false;
                    }
                }
            });
            _uiThread.IsBackground = true;
            _uiThread.SetApartmentState(ApartmentState.STA);
            _uiThread.Start();
            if (!ready.Wait(12000)) throw new TimeoutException("UI AI CAD не поднялся за 12 с.");
            if (error != null) throw error;
            if (created == null || created.IsDisposed) throw new InvalidOperationException("Не удалось создать UI AI CAD.");
            return created;
        }

        public void ClosePanel()
        {
            lock (Sync)
            {
                try { _native?.Dispose(); } catch { }
                _native = null;
                _hostedNative = false;
                try { if (_form != null && !_form.IsDisposed) _form.BeginInvoke((Action)(() => _form.Close())); } catch { }
            }
        }

        private sealed class PanelForm : Form
        {
            public int PreferredWidth { get { return 300; } }
            public int PreferredHeight { get { return 520; } }

            private readonly TextBox _task;
            private readonly Label _status;
            private readonly Label _modeHint;
            private readonly Button _create, _edit, _save, _clear;
            private readonly ProgressBar _progress;
            private bool _running;

            public PanelForm()
            {
                Text = "AI CAD";
                Width = PreferredWidth;
                Height = PreferredHeight;
                FormBorderStyle = FormBorderStyle.SizableToolWindow;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                MinimizeBox = false;
                MaximizeBox = false;
                TopMost = false;
                BackColor = Color.FromArgb(245, 246, 248);
                Font = new Font("Segoe UI", 9F);
                MinimumSize = new Size(260, 380);

                var header = new Panel { Dock = DockStyle.Top, Height = 44, BackColor = Color.FromArgb(32, 90, 167), Padding = new Padding(12, 10, 12, 8) };
                header.Controls.Add(new Label { Text = "AI CAD", Dock = DockStyle.Fill, ForeColor = Color.White, Font = new Font("Segoe UI", 11F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft });

                _modeHint = new Label { Text = "Встроенная панель КОМПАС. Описание передаётся напрямую в CAD-агент.", Dock = DockStyle.Top, Height = 40, Padding = new Padding(12, 8, 12, 4), ForeColor = Color.FromArgb(60, 60, 60) };
                var taskLabel = new Label { Text = "Задача", Dock = DockStyle.Top, Height = 22, Padding = new Padding(12, 4, 12, 0), Font = new Font("Segoe UI", 8.5F, FontStyle.Bold) };

                var taskHost = new Panel { Dock = DockStyle.Top, Height = 172, Padding = new Padding(12, 0, 12, 8) };
                _task = new TextBox { Multiline = true, AcceptsReturn = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill, Font = new Font("Segoe UI", 9.5F), BorderStyle = BorderStyle.FixedSingle };
                taskHost.Controls.Add(_task);

                var buttons = new TableLayoutPanel { Dock = DockStyle.Top, Height = 76, ColumnCount = 2, RowCount = 2, Padding = new Padding(10, 4, 10, 4) };
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

                _progress = new ProgressBar { Dock = DockStyle.Top, Height = 6, Style = ProgressBarStyle.Marquee, MarqueeAnimationSpeed = 0 };
                var statusHeader = new Label { Text = "Статус", Dock = DockStyle.Top, Height = 22, Padding = new Padding(12, 6, 12, 0), Font = new Font("Segoe UI", 8.5F, FontStyle.Bold) };
                _status = new Label { Text = "Готово.", Dock = DockStyle.Fill, Padding = new Padding(12, 4, 12, 12), ForeColor = Color.FromArgb(40, 40, 40) };

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
                new Button { Text = text, Dock = DockStyle.Fill, Margin = new Padding(3), FlatStyle = FlatStyle.System, Font = new Font("Segoe UI", 9F) };

            public void PrepareAsChildHost()
            {
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                Size = new Size(PreferredWidth, PreferredHeight);
            }

            public void SetHostMode(bool nativeHosted)
            {
                FormBorderStyle = FormBorderStyle.None;
                _modeHint.Text = nativeHosted
                    ? "Встроенная панель KOMPAS PropertyManager."
                    : "Встроенная панель.";
            }

            public void FocusTaskBox()
            {
                try { _task.Focus(); } catch { }
            }

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
                    bool err = result.ExitCode != 0 || (message != null && (
                        message.IndexOf("ошиб", StringComparison.OrdinalIgnoreCase) >= 0
                        || message.IndexOf("error", StringComparison.OrdinalIgnoreCase) >= 0
                        || message.IndexOf("не выполнен", StringComparison.OrdinalIgnoreCase) >= 0));
                    SetStatus(message, err);
                }
                catch (Exception ex) { SetStatus(SanitizeMessage(ex.Message), true); }
                finally
                {
                    try { if (File.Exists(taskFile)) File.Delete(taskFile); } catch { }
                    SetBusy(false);
                }
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
                    if (t.StartsWith("Traceback", StringComparison.OrdinalIgnoreCase)) continue;
                    if (t.StartsWith("File \"", StringComparison.OrdinalIgnoreCase)) continue;
                    if (t.Contains("site-packages") || t.Contains("\venv\\")) continue;
                    kept.Add(t);
                    if (kept.Count >= 3) break;
                }
                string result = string.Join("\n", kept);
                if (result.Length > 400) result = result.Substring(0, 397) + "…";
                return result;
            }

            private static string FindRepo()
            {
                string env = Environment.GetEnvironmentVariable("COMPAS_REPO");
                if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env)) return Path.GetFullPath(env);
                return AppDomain.CurrentDomain.BaseDirectory;
            }

            private static string FindPython(string repo)
            {
                string env = Environment.GetEnvironmentVariable("COMPAS_PYTHON");
                if (!string.IsNullOrWhiteSpace(env) && File.Exists(env)) return env;
                string candidate = Path.Combine(repo, "venv", "Scripts", "python.exe");
                if (File.Exists(candidate)) return candidate;
                return "python.exe";
            }

            private readonly struct ProcessResult
            {
                public readonly int ExitCode;
                public readonly string Output;
                public readonly string Error;
                public ProcessResult(int exitCode, string output, string error) { ExitCode = exitCode; Output = output; Error = error; }
            }
        }
    }
}
