using System;
using System.Reflection;
using System.Runtime.InteropServices;

namespace CompasAiCad
{
    /// <summary>
    /// Hosts a WinForms HWND inside KOMPAS IPropertyManager via ksControlUserWindow (type 47).
    /// Reflection-based for COM compatibility across KOMPAS builds.
    /// </summary>
    internal sealed class PropertyManagerBackend : IDisposable
    {
        private object _manager;
        private object _tab;
        private object _hostControl;

        public bool IsReady { get; private set; }

        public bool TryOpen(object kompas, IntPtr hwnd, int preferredWidth = 300, int preferredHeight = 520)
        {
            if (kompas == null || hwnd == IntPtr.Zero) return false;
            try
            {
                object manager = Get(kompas, "PropertyManager")
                                 ?? Invoke(kompas, "GetPropertyManager")
                                 ?? Get(kompas, "IPropertyManager");
                if (manager == null) return false;

                object tab = null;
                try { tab = Invoke(manager, "CreateTab", "AI CAD"); } catch { }
                if (tab == null)
                {
                    try { tab = Invoke(manager, "AddTab", "AI CAD"); } catch { }
                }
                if (tab == null)
                {
                    try { tab = Get(manager, "ActiveTab"); } catch { }
                }
                if (tab == null) return false;

                object control = null;
                foreach (string method in new[] { "CreateControl", "AddControl", "NewControl" })
                {
                    if (control != null) break;
                    foreach (object typeArg in new object[] { (short)47, 47, "ksControlUserWindow" })
                    {
                        try
                        {
                            control = Invoke(tab, method, typeArg, "AI CAD Host");
                            if (control != null) break;
                        }
                        catch { }
                        try
                        {
                            control = Invoke(tab, method, typeArg);
                            if (control != null) break;
                        }
                        catch { }
                    }
                }
                if (control == null) return false;

                TrySet(control, "Name", "CompasAiCadHost");
                TrySet(control, "Caption", "AI CAD");
                TrySet(control, "Visible", true);
                TrySet(control, "Width", preferredWidth);
                TrySet(control, "Height", preferredHeight);

                if (!BindHwnd(control, hwnd)) return false;

                try { Invoke(manager, "ShowTabs"); } catch { }
                try { Invoke(manager, "Show"); } catch { }
                try { Invoke(tab, "Activate"); } catch { }
                try { Invoke(manager, "Update"); } catch { }

                _manager = manager;
                _tab = tab;
                _hostControl = control;
                IsReady = true;
                return true;
            }
            catch
            {
                IsReady = false;
                return false;
            }
        }

        private static bool BindHwnd(object target, IntPtr hwnd)
        {
            foreach (string prop in new[] { "WindowHandle", "Handle", "Hwnd", "HWND", "hWnd" })
                if (TrySetHandle(target, prop, hwnd)) return true;

            foreach (string method in new[] { "SetWindowHandle", "SetHandle", "SetHwnd", "SetWindow" })
            {
                foreach (object arg in new object[] { hwnd.ToInt64(), hwnd.ToInt32(), hwnd })
                {
                    try
                    {
                        Invoke(target, method, arg);
                        return true;
                    }
                    catch { }
                }
            }

            foreach (string innerName in new[] { "Window", "UserWindow", "PropertyUserWindow", "Control" })
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
            foreach (object value in new object[] { hwnd.ToInt64(), hwnd.ToInt32(), hwnd })
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

        private static object Invoke(object target, string name, params object[] args) =>
            target.GetType().InvokeMember(
                name,
                BindingFlags.InvokeMethod | BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance,
                null, target, args);

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

        public void Dispose()
        {
            try { if (_manager != null) Invoke(_manager, "HideTabs"); } catch { }
            IsReady = false;
            _hostControl = null;
            _tab = null;
            _manager = null;
        }
    }
}
