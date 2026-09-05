using System;
using System.Reflection;

namespace CompasAiCad
{
    internal sealed class PropertyManagerBackend : IDisposable
    {
        private object _manager;
        private object _tab;
        private object _hostControl;

        public bool IsReady { get; private set; }
        public object Manager => _manager;

        public bool TryOpen(object kompasApplication, IntPtr childHandle)
        {
            Dispose();
            if (kompasApplication == null || childHandle == IntPtr.Zero) return false;
            try
            {
                _manager = Invoke(kompasApplication, "CreatePropertyManager", false);
                if (_manager == null) return false;
                TrySet(_manager, "Caption", "AI CAD");
                TrySet(_manager, "Label", "AI CAD");
                TrySet(_manager, "ActivateOnCreate", true);

                object tabs = Get(_manager, "PropertyTabs");
                if (tabs == null) return false;
                _tab = Invoke(tabs, "Add", "AI CAD");
                if (_tab == null) return false;
                TrySet(_tab, "Name", "AI CAD");
                TrySet(_tab, "Caption", "AI CAD");

                object controls = Get(_tab, "PropertyControls");
                if (controls == null) return false;
                _hostControl = Invoke(controls, "Add", 47); // ksControlUserWindow
                if (_hostControl == null) return false;
                if (!TryAttachWindow(_hostControl, childHandle)) return false;

                try { Invoke(_manager, "ShowTabs"); } catch { }
                TrySet(_manager, "Visible", true);
                IsReady = true;
                return true;
            }
            catch { Dispose(); return false; }
        }

        private static bool TryAttachWindow(object target, IntPtr hwnd)
        {
            foreach (string prop in new[] { "WindowHandle", "Handle", "Hwnd", "HWND" })
                if (TrySetHandle(target, prop, hwnd)) return true;
            foreach (string method in new[] { "SetWindowHandle", "SetHandle", "SetHwnd" })
            {
                foreach (object arg in new object[] { hwnd.ToInt64(), hwnd })
                {
                    try { Invoke(target, method, arg); return true; } catch { }
                }
            }
            foreach (string innerName in new[] { "Window", "UserWindow", "PropertyUserWindow" })
            {
                object inner = Get(target, innerName);
                if (inner == null) continue;
                foreach (string prop in new[] { "WindowHandle", "Handle", "Hwnd", "HWND" })
                    if (TrySetHandle(inner, prop, hwnd)) return true;
            }
            return false;
        }

        private static bool TrySetHandle(object target, string property, IntPtr hwnd)
        {
            foreach (object value in new object[] { hwnd.ToInt64(), hwnd })
            {
                try
                {
                    target.GetType().InvokeMember(property, BindingFlags.SetProperty | BindingFlags.Public | BindingFlags.Instance, null, target, new[] { value });
                    return true;
                }
                catch { }
            }
            return false;
        }

        private static object Invoke(object target, string name, params object[] args) =>
            target.GetType().InvokeMember(name, BindingFlags.InvokeMethod | BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance, null, target, args);

        private static object Get(object target, string name)
        {
            try { return target.GetType().InvokeMember(name, BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance, null, target, null); }
            catch { return null; }
        }

        private static void TrySet(object target, string name, object value)
        {
            try { target.GetType().InvokeMember(name, BindingFlags.SetProperty | BindingFlags.Public | BindingFlags.Instance, null, target, new[] { value }); }
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
