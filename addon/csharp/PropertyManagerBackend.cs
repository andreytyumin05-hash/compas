using System;
using System.Reflection;

namespace CompasAiCad
{
    /// <summary>
    /// Adds the AI CAD UI to the standard KOMPAS PropertyManager.
    /// KOMPAS v23 documents CreatePropertyManager(false) as the system
    /// PropertyManager; library tabs added to it are integrated into KOMPAS.
    /// The WinForms HWND is used only as the content of the native
    /// ksControlUserWindow control, never as a top-level window.
    /// </summary>
    internal sealed class PropertyManagerBackend : IDisposable
    {
        private object _manager;
        private object _tabs;
        private object _tab;
        private object _controls;
        private object _hostControl;

        public bool IsReady { get; private set; }

        public bool TryOpen(object kompas, IntPtr hwnd, int preferredWidth = 300, int preferredHeight = 520)
        {
            if (kompas == null || hwnd == IntPtr.Zero) return false;
            try
            {
                // IMPORTANT: false requests KOMPAS' standard/integrated panel.
                // The previous implementation tried PropertyManager/CreateTab
                // members that are not the documented v23 API and silently fell
                // back to a separate top-level WinForms window.
                object manager = Invoke(kompas, "CreatePropertyManager", false);
                if (manager == null) return false;

                object tabs = Get(manager, "PropertyTabs") ?? Invoke(manager, "GetPropertyTabs");
                if (tabs == null) return false;

                object tab = FindExistingTab(tabs, "AI CAD");
                if (tab == null)
                {
                    tab = Invoke(tabs, "Add");
                    if (tab == null) return false;
                    TrySet(tab, "Name", "AI CAD");
                    TrySet(tab, "Caption", "AI CAD");
                }

                TrySet(tab, "Visible", true);
                TrySet(tab, "ActivateOnCreate", true);

                object controls = Get(tab, "PropertyControls") ?? Get(tab, "Controls");
                if (controls == null) return false;

                // Reuse an existing host if this command is invoked again.
                object control = FindExistingControl(controls, "CompasAiCadHost");
                if (control == null)
                {
                    control = Invoke(controls, "Add", 47); // ksControlUserWindow
                    if (control == null) return false;
                    TrySet(control, "Name", "CompasAiCadHost");
                    TrySet(control, "Caption", "AI CAD");
                }

                TrySet(control, "Visible", true);
                TrySet(control, "Width", preferredWidth);
                TrySet(control, "Height", preferredHeight);

                if (!BindHwnd(control, hwnd)) return false;

                TrySet(manager, "Visible", true);
                TryInvoke(manager, "ShowTabs");
                TryInvoke(manager, "UpdateTabs");

                _manager = manager;
                _tabs = tabs;
                _tab = tab;
                _controls = controls;
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

        private static object FindExistingTab(object tabs, string name)
        {
            try { return Invoke(tabs, "Item", name); } catch { }
            try { return Invoke(tabs, "GetItem", name); } catch { }
            return null;
        }

        private static object FindExistingControl(object controls, string name)
        {
            try
            {
                int count = Convert.ToInt32(Get(controls, "Count") ?? 0);
                for (int i = 0; i < count; i++)
                {
                    object item = null;
                    try { item = Invoke(controls, "Item", i); } catch { }
                    if (item == null) continue;
                    string itemName = Convert.ToString(Get(item, "Name"));
                    if (string.Equals(itemName, name, StringComparison.OrdinalIgnoreCase)) return item;
                }
            }
            catch { }
            return null;
        }

        private static bool BindHwnd(object target, IntPtr hwnd)
        {
            // IPropertyUserWindow is exposed through the user-window control.
            // COM wrappers differ between installed v23 builds, so try the
            // known Automation spellings without changing the window's parent.
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

        private static void TryInvoke(object target, string name, params object[] args)
        {
            try { Invoke(target, name, args); } catch { }
        }

        public void Dispose()
        {
            try { if (_manager != null) Invoke(_manager, "HideTabs"); } catch { }
            IsReady = false;
            _hostControl = null;
            _controls = null;
            _tab = null;
            _tabs = null;
            _manager = null;
        }
    }
}
