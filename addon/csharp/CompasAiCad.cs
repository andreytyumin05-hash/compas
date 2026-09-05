using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
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
        private static IntPtr _kompasHandle;

        [return: MarshalAs(UnmanagedType.BStr)]
        public string GetLibraryName() => "CompasAiCad";

        [return: MarshalAs(UnmanagedType.BStr)]
        public string DisplayLibraryName() => "AI CAD";

        public bool IsOnApplication7() => true;

        [return: MarshalAs(UnmanagedType.BStr)]
        public string ExternalMenuItem(short number, ref short itemType, ref short command)
        {
            if (number == 0)
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
            if (command != 1 || kompas_ == null)
                return;

            try
            {
                dynamic app = kompas_;
                long handle = Convert.ToInt64(app.MainWindowHandle);
                _kompasHandle = new IntPtr(handle);
                ShowPanel(_kompasHandle);
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
                try { _form.BeginInvoke((Action)(() => _form.Close())); }
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

            private readonly IntPtr _parent;
            private readonly TextBox _task;
            private readonly TextBox _log;
            private readonly Label _status;
            private readonly System.Windows.Forms.Timer _layoutTimer;

            public PanelForm(IntPtr parent)
            {
                _parent = parent;
                Text = "AI CAD";
                Width = 390;
                Height = 700;
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                MinimizeBox = false;
                MaximizeBox = false;
                BackColor = System.Drawing.SystemColors.Control;

                var title = new Label
                {
                    Text = "AI CAD",
                    Dock = DockStyle.Top,
                    Height = 38,
                    Font = new System.Drawing.Font("Segoe UI", 13F, System.Drawing.FontStyle.Bold),
                    Padding = new Padding(12, 8, 8, 4)
                };

                var hint = new Label
                {
                    Text = "Описание детали / команда изменения:",
                    Dock = DockStyle.Top,
                    Height = 30,
                    Padding = new Padding(12, 6, 8, 0)
                };

                _task = new TextBox
                {
                    Multiline = true,
                    ScrollBars = ScrollBars.Vertical,
                    Dock = DockStyle.Top,
                    Height = 150,
                    Margin = new Padding(12),
                    Font = new System.Drawing.Font("Segoe UI", 10F)
                };

                var buttons = new FlowLayoutPanel
                {
                    Dock = DockStyle.Top,
                    Height = 42,
                    Padding = new Padding(8, 4, 8, 4),
                    WrapContents = false
                };

                var create = new Button { Text = "Создать", AutoSize = true };
                var edit = new Button { Text = "Изменить последнюю", AutoSize = true };
                var save = new Button { Text = "Сохранить M3D", AutoSize = true };
                create.Click += (s, e) => Run("create");
                edit.Click += (s, e) => Run("edit");
                save.Click += (s, e) => Run("save");
                buttons.Controls.Add(create);
                buttons.Controls.Add(edit);
                buttons.Controls.Add(save);

                _status = new Label
                {
                    Text = "Готово",
                    Dock = DockStyle.Top,
                    Height = 26,
                    Padding = new Padding(12, 4, 8, 0)
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
                Controls.Add(title);

                Shown += (s, e) => AttachAndLayout();
                _layoutTimer = new System.Windows.Forms.Timer { Interval = 500 };
                _layoutTimer.Tick += (s, e) => AttachAndLayout();
                _layoutTimer.Start();
            }

            public void SetParentWindow(IntPtr parent)
            {
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
                SetWindowLong(Handle, GWL_STYLE, style | WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN);

                if (!GetClientRect(_parent, out RECT r))
                    return;

                int width = Math.Min(400, Math.Max(320, r.Right / 4));
                int height = Math.Max(240, r.Bottom);
                SetWindowPos(Handle, IntPtr.Zero, r.Right - width, 0, width, height,
                    SWP_NOACTIVATE | SWP_SHOWWINDOW);
            }

            private void Run(string action)
            {
                if (action != "save" && string.IsNullOrWhiteSpace(_task.Text))
                {
                    Append("Введите описание детали.");
                    return;
                }

                _status.Text = action == "save" ? "Сохранение…" : "Построение…";
                Append($"> {action}");

                string repo = FindRepo();
                string python = Environment.GetEnvironmentVariable("COMPAS_PYTHON");
                if (string.IsNullOrWhiteSpace(python)) python = "python.exe";

                string taskFile = Path.Combine(Path.GetTempPath(), "compas_ai_cad_" + Guid.NewGuid().ToString("N") + ".txt");
                try
                {
                    if (action != "save") File.WriteAllText(taskFile, _task.Text, new UTF8Encoding(false));

                    var psi = new ProcessStartInfo
                    {
                        FileName = python,
                        WorkingDirectory = repo,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        Arguments = action == "save"
                            ? "-m addon.bridge save"
                            : $"-m addon.bridge {action} --task-file \"{taskFile}\""
                    };

                    psi.EnvironmentVariables["COMPAS_REPO"] = repo;
                    using (var p = Process.Start(psi))
                    {
                        string stdout = p.StandardOutput.ReadToEnd();
                        string stderr = p.StandardError.ReadToEnd();
                        p.WaitForExit();
                        Append(stdout.Trim());
                        if (!string.IsNullOrWhiteSpace(stderr)) Append(stderr.Trim());
                        _status.Text = p.ExitCode == 0 ? "Готово" : "Ошибка";
                    }
                }
                catch (Exception ex)
                {
                    _status.Text = "Ошибка";
                    Append(ex.ToString());
                }
                finally
                {
                    try { if (File.Exists(taskFile)) File.Delete(taskFile); } catch { }
                }
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
                if (string.IsNullOrWhiteSpace(text)) return;
                _log.AppendText(text + Environment.NewLine);
                _log.SelectionStart = _log.TextLength;
                _log.ScrollToCaret();
            }
        }
    }
}
