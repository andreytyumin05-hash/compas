using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
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

        [return: MarshalAs(UnmanagedType.BStr)]
        public string GetLibraryName() => "CompasAiCad";

        [return: MarshalAs(UnmanagedType.BStr)]
        public string DisplayLibraryName() => "AI CAD";

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

        public void ExternalRunCommand(
            [In] short command,
            [In] short mode,
            [In, MarshalAs(UnmanagedType.IDispatch)] object kompas_)
        {
            if (command != 1)
                return;

            try
            {
                long handle = Process.GetCurrentProcess().MainWindowHandle.ToInt64();
                if (handle == 0)
                    throw new InvalidOperationException("Не удалось получить главное окно КОМПАС-3D.");

                ShowPanel(new IntPtr(handle));
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "AI CAD не смог открыть панель.\n\n" + ex.Message,
                    "Compas AI CAD",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        public void ClosePanel()
        {
            lock (Sync)
            {
                if (_form == null || _form.IsDisposed)
                    return;
                try
                {
                    _form.BeginInvoke((Action)(() => _form.Hide()));
                }
                catch { }
            }
        }

        private static void ShowPanel(IntPtr parent)
        {
            lock (Sync)
            {
                if (_form != null && !_form.IsDisposed)
                {
                    try
                    {
                        _form.BeginInvoke((Action)(() =>
                        {
                            _form.SetParentWindow(parent);
                            _form.Visible = true;
                            _form.BringToFront();
                        }));
                    }
                    catch { }
                    return;
                }

                _uiThread = new Thread(() =>
                {
                    Application.EnableVisualStyles();
                    Application.SetCompatibleTextRenderingDefault(false);
                    _form = new PanelForm(parent);
                    _form.FormClosed += (s, e) =>
                    {
                        lock (Sync) { _form = null; }
                        Application.ExitThread();
                    };
                    Application.Run(_form);
                });
                _uiThread.IsBackground = true;
                _uiThread.SetApartmentState(ApartmentState.STA);
                _uiThread.Start();
            }
        }

        private sealed class PanelForm : Form
        {
            private const int GWL_STYLE = -16;
            private const int WS_CHILD = 0x40000000;
            private const int WS_VISIBLE = 0x10000000;
            private const int WS_CLIPCHILDREN = 0x02000000;
            private const int SWP_NOACTIVATE = 0x0010;
            private const int SWP_SHOWWINDOW = 0x0040;

            [DllImport("user32.dll", SetLastError = true)]
            private static extern IntPtr SetParent(IntPtr hWndChild, IntPtr hWndNewParent);

            [DllImport("user32.dll", SetLastError = true)]
            private static extern int GetWindowLong(IntPtr hWnd, int nIndex);

            [DllImport("user32.dll", SetLastError = true)]
            private static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

            [DllImport("user32.dll", SetLastError = true)]
            private static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

            [DllImport("user32.dll", SetLastError = true)]
            private static extern bool SetWindowPos(
                IntPtr hWnd, IntPtr hWndInsertAfter,
                int X, int Y, int cx, int cy, uint uFlags);

            [StructLayout(LayoutKind.Sequential)]
            private struct RECT { public int Left, Top, Right, Bottom; }

            private readonly TextBox _task;
            private readonly TextBox _log;
            private readonly Label _status;
            private readonly Button _create;
            private readonly Button _edit;
            private readonly Button _save;
            private readonly IntPtr _parent;
            private int _lastWidth = -1;
            private int _lastHeight = -1;
            private bool _running;

            public PanelForm(IntPtr parent)
            {
                _parent = parent;
                Text = "AI CAD";
                Width = 360;
                Height = 680;
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                MinimizeBox = false;
                MaximizeBox = false;
                BackColor = System.Drawing.SystemColors.Control;

                var header = new Panel
                {
                    Dock = DockStyle.Top,
                    Height = 42,
                    Padding = new Padding(10, 6, 8, 6)
                };

                var title = new Label
                {
                    Text = "AI CAD",
                    Dock = DockStyle.Fill,
                    Font = new System.Drawing.Font("Segoe UI", 12F, System.Drawing.FontStyle.Bold),
                    TextAlign = System.Drawing.ContentAlignment.MiddleLeft
                };

                var close = new Button
                {
                    Text = "×",
                    Dock = DockStyle.Right,
                    Width = 32,
                    FlatStyle = FlatStyle.Flat,
                    Font = new System.Drawing.Font("Segoe UI", 13F),
                    TabStop = false
                };
                close.FlatAppearance.BorderSize = 0;
                close.Click += (s, e) => HidePanel();

                header.Controls.Add(title);
                header.Controls.Add(close);

                var hint = new Label
                {
                    Text = "Описание детали или команда изменения",
                    Dock = DockStyle.Top,
                    Height = 30,
                    Padding = new Padding(10, 5, 8, 0)
                };

                _task = new TextBox
                {
                    Multiline = true,
                    ScrollBars = ScrollBars.Vertical,
                    Dock = DockStyle.Top,
                    Height = 150,
                    Font = new System.Drawing.Font("Segoe UI", 10F),
                    Margin = new Padding(10),
                    AcceptsReturn = true
                };

                var buttons = new FlowLayoutPanel
                {
                    Dock = DockStyle.Top,
                    Height = 46,
                    Padding = new Padding(8, 5, 8, 5),
                    WrapContents = false
                };

                _create = new Button { Text = "Создать", AutoSize = true };
                _edit = new Button { Text = "Изменить последнюю", AutoSize = true };
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
                    Dock = DockStyle.Top,
                    Height = 28,
                    Padding = new Padding(10, 5, 8, 0)
                };

                _log = new TextBox
                {
                    Multiline = true,
                    ReadOnly = true,
                    ScrollBars = ScrollBars.Both,
                    Dock = DockStyle.Fill,
                    Font = new System.Drawing.Font("Consolas", 9F)
                };

                Controls.Add(_log);
                Controls.Add(_status);
                Controls.Add(buttons);
                Controls.Add(_task);
                Controls.Add(hint);
                Controls.Add(header);

                Shown += (s, e) => AttachAndLayout();
            }

            public void SetParentWindow(IntPtr parent)
            {
                if (parent == IntPtr.Zero)
                    return;
                SetParent(Handle, parent);
                AttachAndLayout();
            }

            private void AttachAndLayout()
            {
                if (_parent == IntPtr.Zero || !IsHandleCreated)
                    return;

                if (Parent == null)
                    SetParent(Handle, _parent);

                int style = GetWindowLong(Handle, GWL_STYLE);
                int desired = style | WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN;
                if (style != desired)
                    SetWindowLong(Handle, GWL_STYLE, desired);

                if (!GetClientRect(_parent, out RECT r))
                    return;

                int width = Math.Min(360, Math.Max(320, r.Right / 5));
                int height = Math.Max(240, r.Bottom);
                if (width == _lastWidth && height == _lastHeight)
                    return;

                _lastWidth = width;
                _lastHeight = height;
                SetWindowPos(Handle, IntPtr.Zero, r.Right - width, 0, width, height,
                    SWP_NOACTIVATE | SWP_SHOWWINDOW);
            }

            private async Task RunAsync(string action)
            {
                if (_running)
                    return;

                if (action != "save" && string.IsNullOrWhiteSpace(_task.Text))
                {
                    Append("Введите описание детали.");
                    return;
                }

                _running = true;
                SetButtons(false);
                _status.Text = action == "save" ? "Сохранение…" : "Построение…";
                Append($"> {action}");

                string repo = FindRepo();
                string python = FindPython(repo);
                string taskFile = Path.Combine(Path.GetTempPath(), "compas_ai_cad_" + Guid.NewGuid().ToString("N") + ".txt");

                try
                {
                    if (action != "save")
                        File.WriteAllText(taskFile, _task.Text, new UTF8Encoding(false));

                    var result = await Task.Run(() => ExecutePython(repo, python, action, taskFile));
                    Append(result.Output);
                    if (!string.IsNullOrWhiteSpace(result.Error))
                        Append(result.Error);
                    _status.Text = result.ExitCode == 0 ? "Готово" : "Ошибка";
                }
                catch (Exception ex)
                {
                    _status.Text = "Ошибка";
                    Append(ex.ToString());
                }
                finally
                {
                    try { if (File.Exists(taskFile)) File.Delete(taskFile); } catch { }
                    _running = false;
                    SetButtons(true);
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
                    return new ProcessResult(p.ExitCode, stdout.Trim(), stderr.Trim());
                }
            }

            private void SetButtons(bool enabled)
            {
                if (IsDisposed)
                    return;
                _create.Enabled = enabled;
                _edit.Enabled = enabled;
                _save.Enabled = enabled;
            }

            private void HidePanel()
            {
                Visible = false;
                _status.Text = "Готово";
            }

            private static string FindPython(string repo)
            {
                string[] candidates =
                {
                    Path.Combine(repo, "venv", "Scripts", "python.exe"),
                    Environment.GetEnvironmentVariable("COMPAS_PYTHON"),
                    "python.exe"
                };

                foreach (string item in candidates)
                {
                    if (!string.IsNullOrWhiteSpace(item) && File.Exists(item))
                        return item;
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
                    if (File.Exists(Path.Combine(dir.FullName, "agent", "build.py")))
                        return dir.FullName;
                    dir = dir.Parent;
                }

                return Directory.GetCurrentDirectory();
            }

            private void Append(string text)
            {
                if (string.IsNullOrWhiteSpace(text) || IsDisposed)
                    return;
                _log.AppendText(text + Environment.NewLine);
                _log.SelectionStart = _log.TextLength;
                _log.ScrollToCaret();
            }
        }

        private readonly struct ProcessResult
        {
            public ProcessResult(int exitCode, string output, string error)
            {
                ExitCode = exitCode;
                Output = output;
                Error = error;
            }

            public int ExitCode { get; }
            public string Output { get; }
            public string Error { get; }
        }
    }
}
