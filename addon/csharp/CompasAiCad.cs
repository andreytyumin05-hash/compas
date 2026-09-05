using System;
using System.Collections.Generic;
using System.Diagnostics;
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

        [return: MarshalAs(UnmanagedType.BStr)] public string GetLibraryName() => "CompasAiCad";
        [return: MarshalAs(UnmanagedType.BStr)] public string DisplayLibraryName() => "AI CAD";
        public bool IsOnApplication7() => true;

        [return: MarshalAs(UnmanagedType.BStr)]
        public string ExternalMenuItem(short number, ref short itemType, ref short command)
        {
            if (number == 1)
            {
                itemType = 1;
                command = 1;
                return "Панель AI CAD";
            }
            itemType = 3;
            command = -1;
            return string.Empty;
        }

        public void ExternalRunCommand([In] short command, [In] short mode,
            [In, MarshalAs(UnmanagedType.IDispatch)] object kompas_)
        {
            if (command != 1) return;
            try
            {
                ShowNativePanel(kompas_);
            }
            catch (Exception ex)
            {
                MessageBox.Show("AI CAD не смог открыть нативную панель KOMPAS.\n\n" + ex.Message,
                    "Compas AI CAD", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void ShowNativePanel(object kompas)
        {
            lock (Sync)
            {
                if (_form != null && !_form.IsDisposed && _native != null && _native.IsReady)
                    return;

                PanelForm form = CreateFormOnStaThread();
                _native = new PropertyManagerBackend();
                if (!_native.TryOpen(kompas, form.Handle))
                {
                    try { form.BeginInvoke((Action)(() => form.Close())); } catch { }
                    _native.Dispose();
                    _native = null;
                    throw new InvalidOperationException("KOMPAS не принял ksControlUserWindow / IPropertyManager. Проверьте сборку Add-In v23.");
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
                catch (Exception ex)
                {
                    error = ex;
                    ready.Set();
                }
                finally
                {
                    lock (Sync) { if (ReferenceEquals(_form, created)) _form = null; }
                }
            });
            _uiThread.IsBackground = true;
            _uiThread.SetApartmentState(ApartmentState.STA);
            _uiThread.Start();
            ready.Wait(10000);
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
                try { if (_form != null && !_form.IsDisposed) _form.BeginInvoke((Action)(() => _form.Close())); } catch { }
            }
        }

        private sealed class PanelForm : Form
        {
            private readonly TextBox _task;
            private readonly Label _status;
            private readonly Button _create;
            private readonly Button _edit;
            private readonly Button _save;
            private bool _running;

            public PanelForm()
            {
                Text = "AI CAD";
                Width = 420;
                Height = 650;
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                MinimizeBox = false;
                MaximizeBox = false;
                BackColor = System.Drawing.SystemColors.Control;

                var header = new Label
                {
                    Text = "AI CAD",
                    Dock = DockStyle.Top,
                    Height = 42,
                    Padding = new Padding(10, 8, 8, 5),
                    Font = new System.Drawing.Font("Segoe UI", 12F, System.Drawing.FontStyle.Bold)
                };
                var hint = new Label
                {
                    Text = "Описание детали или команда изменения открытой детали",
                    Dock = DockStyle.Top,
                    Height = 34,
                    Padding = new Padding(10, 5, 8, 0)
                };
                _task = new TextBox
                {
                    Multiline = true,
                    AcceptsReturn = true,
                    ScrollBars = ScrollBars.Vertical,
                    Dock = DockStyle.Top,
                    Height = 190,
                    Font = new System.Drawing.Font("Segoe UI", 10F)
                };

                var buttons = new FlowLayoutPanel
                {
                    Dock = DockStyle.Top,
                    Height = 48,
                    Padding = new Padding(8, 6, 8, 5),
                    WrapContents = false
                };
                _create = new Button { Text = "Создать", AutoSize = true };
                _edit = new Button { Text = "Изменить открытую", AutoSize = true };
                _save = new Button { Text = "Сохранить M3D", AutoSize = true };
                _create.Click += async (s, e) => await RunAsync("create");
                _edit.Click += async (s, e) => await RunAsync("edit");
                _save.Click += async (s, e) => await RunAsync("save");
                buttons.Controls.Add(_create);
                buttons.Controls.Add(_edit);
                buttons.Controls.Add(_save);

                _status = new Label
                {
                    Text = "Готово",
                    Dock = DockStyle.Fill,
                    Padding = new Padding(10, 8, 10, 8)
                };

                Controls.Add(_status);
                Controls.Add(buttons);
                Controls.Add(_task);
                Controls.Add(hint);
                Controls.Add(header);
            }

            private async Task RunAsync(string action)
            {
                if (_running) return;
                if (action != "save" && string.IsNullOrWhiteSpace(_task.Text))
                {
                    _status.Text = "Введите команду.";
                    return;
                }

                _running = true;
                _create.Enabled = _edit.Enabled = _save.Enabled = false;
                _status.Text = action == "save" ? "Сохранение…" : "Обработка…";
                string repo = FindRepo();
                string python = FindPython(repo);
                string taskFile = Path.Combine(Path.GetTempPath(), "compas_ai_cad_" + Guid.NewGuid().ToString("N") + ".txt");
                try
                {
                    if (action != "save") File.WriteAllText(taskFile, _task.Text, new UTF8Encoding(false));
                    ProcessResult result = await Task.Run(() => ExecutePython(repo, python, action, taskFile));
                    string message = ExtractUiMessage(result.Output, result.Error, result.ExitCode, action);
                    _status.Text = message;
                }
                catch (Exception ex)
                {
                    _status.Text = ex.Message;
                }
                finally
                {
                    try { if (File.Exists(taskFile)) File.Delete(taskFile); } catch { }
                    _running = false;
                    _create.Enabled = _edit.Enabled = _save.Enabled = true;
                }
            }

            private static ProcessResult ExecutePython(string repo, string python, string action, string taskFile)
            {
                string args = action == "save"
                    ? "-m addon.bridge save"
                    : $"-m addon.bridge {action} --task-file \"{taskFile}\"";
                var psi = new ProcessStartInfo
                {
                    FileName = python,
                    WorkingDirectory = repo,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    Arguments = args
                };
                psi.EnvironmentVariables["COMPAS_REPO"] = repo;
                using (var p = Process.Start(psi))
                {
                    string stdout = p.StandardOutput.ReadToEnd();
                    string stderr = p.StandardError.ReadToEnd();
                    p.WaitForExit();
                    return new ProcessResult(p.ExitCode, stdout, stderr);
                }
            }

            private static string ExtractUiMessage(string stdout, string stderr, int exitCode, string action)
            {
                try
                {
                    var serializer = new JavaScriptSerializer();
                    string[] lines = (stdout ?? string.Empty).Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    for (int i = lines.Length - 1; i >= 0; i--)
                    {
                        string line = lines[i].Trim();
                        if (!line.StartsWith("{")) continue;
                        var data = serializer.DeserializeObject(line) as Dictionary<string, object>;
                        if (data == null) continue;
                        bool ok = data.ContainsKey("ok") && Convert.ToBoolean(data["ok"]);
                        if (ok) return action == "edit" ? "Модель обновлена." : "Готово.";
                        if (data.ContainsKey("error")) return Convert.ToString(data["error"]);
                    }
                }
                catch { }
                if (exitCode == 0) return action == "edit" ? "Модель обновлена." : "Готово.";
                return "Операция не выполнена.";
            }

            private static string FindPython(string repo)
            {
                string configured = Environment.GetEnvironmentVariable("COMPAS_PYTHON");
                string[] candidates = {
                    Path.Combine(repo, "venv", "Scripts", "python.exe"),
                    configured,
                    "python.exe"
                };
                foreach (string item in candidates)
                    if (!string.IsNullOrWhiteSpace(item) && (Path.IsPathRooted(item) ? File.Exists(item) : item == "python.exe"))
                        return item;
                return "python.exe";
            }

            private static string FindRepo()
            {
                string configured = Environment.GetEnvironmentVariable("COMPAS_REPO");
                if (!string.IsNullOrWhiteSpace(configured) && File.Exists(Path.Combine(configured, "agent", "build.py"))) return configured;
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
