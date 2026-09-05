using System;
using System.Reflection;
using System.Text;

namespace CompasAiCad
{
    /// <summary>
    /// Embeds HWND into KOMPAS PropertyManager tab (API7 CreatePropertyManager).
    /// No top-level Windows form.
    /// </summary>
    internal sealed class PropertyManagerBackend : IDisposable
    {
        private object _manager;
        private object _tab;
        private object _hostControl;

        public bool IsReady { get; private set; }
        public string LastError { get; private set; }

        public bool TryOpen(object kompasOrApp, IntPtr hwnd, int preferredWidth, int preferredHeight)
        {
            LastError = null;
            IsReady = false;
            if (kompasOrApp == null) { LastError = "Нет объекта приложения КОМПАС."; return false; }
            if (hwnd == IntPtr.Zero) { LastError = "HWND панели = 0."; return false; }

            object app = ResolveApplication7(kompasOrApp);
            if (app == null) { LastError = "Не получен IApplication (KOMPAS.Application.7)."; return false; }

            var log = new StringBuilder();
            foreach (bool libraryPanel in new[] { true, false })
            {
                try
                {
                    if (TryOpenOn(app, hwnd, preferredWidth, preferredHeight, libraryPanel, log))
                    {
                        IsReady = true;
                        return true;
                    }
                }
                catch (Exception ex)
                {
                    log.AppendLine("mode=" + libraryPanel + ": " + ex.Message);
                }
            }

            LastError = "PropertyManager не принял вкладку.\n" + log;
            return false;
        }

        private bool TryOpenOn(object app, IntPtr hwnd, int w, int h, bool libraryPanel, StringBuilder log)
        {
            object manager;
            try { manager = Invoke(app, "CreatePropertyManager", libraryPanel); }
            catch (Exception ex)
            {
                log.AppendLine("CreatePropertyManager(" + libraryPanel + "): " + ex.Message);
                return false;
            }
            if (manager == null)
            {
                log.AppendLine("CreatePropertyManager(" + libraryPanel + ") = null");
                return false;
            }

            TrySet(manager, "Caption", "AI CAD");
            TrySet(manager, "SpecToolbar", 3);

            object tabs = Get(manager, "PropertyTabs");
            if (tabs == null) { log.AppendLine("PropertyTabs = null"); return false; }

            object tab = null;
            foreach (object arg in new object[] { "AI CAD", "CompasAiCad" })
            {
                try { tab = Invoke(tabs, "Add", arg); if (tab != null) break; } catch { }
            }
            if (tab == null) { try { tab = Invoke(tabs, "Add"); } catch { } }
            if (tab == null) { log.AppendLine("PropertyTabs.Add failed"); return false; }

            TrySet(tab, "Name", "AI CAD");
            TrySet(tab, "Caption", "AI CAD");
            TrySet(tab, "Visible", true);
            TrySet(tab, "Active", true);
            TrySet(tab, "Expanded", true);
            TrySet(tab, "ActivateOnCreate", true);

            object controls = Get(tab, "PropertyControls");
            if (controls == null) { log.AppendLine("PropertyControls = null"); return false; }

            object control = null;
            try { control = Invoke(controls, "Add", 47); }
            catch (Exception ex)
            {
                log.AppendLine("Controls.Add(47): " + ex.Message);
                try { control = Invoke(controls, "Add", (short)47); }
                catch (Exception ex2) { log.AppendLine("Add(short): " + ex2.Message); }
            }
            if (control == null) { log.AppendLine("ksControlUserWindow = null"); return false; }

            TrySet(control, "Name", "CompasAiCadHost");
            TrySet(control, "Caption", "AI CAD");
            TrySet(control, "Visible", true);
            TrySet(control, "Width", w);
            TrySet(control, "Height", h);
            TrySet(control, "Id", 1001);

            if (!BindHwnd(control, hwnd))
            {
                log.AppendLine("WindowHandle не задан. HWND=" + hwnd.ToInt64());
                try
                {
                    foreach (var m in control.GetType().GetMembers(BindingFlags.Public | BindingFlags.Instance))
                    {
                        if (m.Name.IndexOf("Window", StringComparison.OrdinalIgnoreCase) >= 0
                            || m.Name.IndexOf("Handle", StringComparison.OrdinalIgnoreCase) >= 0
                            || m.Name.IndexOf("Hwnd", StringComparison.OrdinalIgnoreCase) >= 0)
                            log.AppendLine("  member: " + m.Name);
                    }
                }
                catch { }
                return false;
            }

            TryInvoke(manager, "ShowTabs");
            TryInvoke(manager, "UpdateTabs");
            TrySet(manager, "Visible", true);

            _manager = manager;
            _tab = tab;
            _hostControl = control;
            return true;
        }

        internal static object ResolveApplication7(object kompasOrApp)
        {
            if (kompasOrApp == null) return null;
            if (HasMethod(kompasOrApp, "CreatePropertyManager")) return kompasOrApp;
            try
            {
                object app = Get(kompasOrApp, "Application");
                if (app != null && HasMethod(app, "CreatePropertyManager")) return app;
            }
            catch { }
            try
            {
                object app7 = MarshalGetActiveObject("KOMPAS.Application.7");
                if (app7 != null) return app7;
            }
            catch { }
            try
            {
                Type t = Type.GetTypeFromProgID("KOMPAS.Application.7");
                if (t != null)
                {
                    object app7 = Activator.CreateInstance(t);
                    if (app7 != null) return app7;
                }
            }
            catch { }
            return kompasOrApp;
        }

        private static object MarshalGetActiveObject(string progId)
        {
            Type ty = Type.GetType("System.Runtime.InteropServices.Marshal");
            if (ty == null) return null;
            var mi = ty.GetMethod("GetActiveObject", new[] { typeof(string) });
            if (mi == null) return null;
            return mi.Invoke(null, new object[] { progId });
        }

        private static bool HasMethod(object target, string name)
        {
            try
            {
                foreach (var m in target.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance))
                    if (string.Equals(m.Name, name, StringComparison.OrdinalIgnoreCase))
                        return true;
            }
            catch { }
            try
            {
                target.GetType().InvokeMember(
                    name,
                    BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance | BindingFlags.GetProperty,
                    null, target, new object[] { false });
                return true;
            }
            catch { return false; }
        }

        private static bool BindHwnd(object target, IntPtr hwnd)
        {
            foreach (string prop in new[] { "WindowHandle", "Handle", "Hwnd", "HWND", "hWnd" })
                if (TrySetHandle(target, prop, hwnd)) return true;

            foreach (string method in new[] { "SetWindowHandle", "SetHandle", "SetHwnd", "SetWindow" })
            {
                foreach (object arg in new object[] { hwnd.ToInt64(), unchecked((int)hwnd.ToInt64()), hwnd })
                {
                    try { Invoke(target, method, arg); return true; }
                    catch { }
                }
            }

            foreach (string innerName in new[] { "Window", "UserWindow", "PropertyUserWindow", "Control", "UserControl" })
            {
                object inner = Get(target, innerName);
                if (inner == null) continue;
                foreach (string prop in new[] { "WindowHandle", "Handle", "Hwnd", "HWND", "hWnd" })
                    if (TrySetHandle(inner, prop, hwnd)) return true;
            }
            return false;
        }

        private static bool TrySetHandle(object target, string property, IntPtr hwnd)
        {
            foreach (object value in new object[] { hwnd.ToInt64(), unchecked((int)hwnd.ToInt64()), hwnd })
            {
                try
                {
                    target.GetType().InvokeMember(
                        property,
                        BindingFlags.SetProperty | BindingFlags.Public | BindingFlags.Instance,
                        null, target, new[] { value });
                    return true;
                }
                catch { }
            }
            return false;
        }

        private static object Invoke(object target, string name, params object[] args)
        {
            return target.GetType().InvokeMember(
                name,
                BindingFlags.InvokeMethod | BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance,
                null, target, args == null || args.Length == 0 ? null : args);
        }

        private static object Get(object target, string name)
        {
            try
            {
                return target.GetType().InvokeMember(
                    name,
                    BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance,
                    null, target, null);
            }
            catch { return null; }
        }

        private static void TrySet(object target, string name, object value)
        {
            try
            {
                target.GetType().InvokeMember(
                    name,
                    BindingFlags.SetProperty | BindingFlags.Public | BindingFlags.Instance,
                    null, target, new[] { value });
            }
            catch { }
        }

        private static void TryInvoke(object target, string name, params object[] args)
        {
            try { Invoke(target, name, args); } catch { }
        }

        public void ShowAgain()
        {
            try { if (_manager != null) Invoke(_manager, "ShowTabs"); } catch { }
            try { if (_manager != null) TrySet(_manager, "Visible", true); } catch { }
        }

        public void Dispose()
        {
            try { if (_manager != null) Invoke(_manager, "HideTabs"); } catch { }
            IsReady = false;
        }

        public void ReleaseAll()
        {
            try { Dispose(); } catch { }
            _hostControl = null;
            _tab = null;
            _manager = null;
        }
    }
}
