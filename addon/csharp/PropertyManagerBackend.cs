using System;
using System.Globalization;
using System.Reflection;

namespace CompasAiCad
{
    /// <summary>
    /// Native KOMPAS IPropertyManager adapter. The Automation calls follow the v23
    /// signatures: CreatePropertyManager(bool), PropertyTabs.Add(BSTR), and
    /// PropertyControls.Add(ControlTypeEnum). The host keeps the interface alive
    /// for the lifetime of the add-in and falls back to WinForms on COM mismatch.
    /// </summary>
    internal sealed class PropertyManagerBackend : IDisposable
    {
        private object _manager;
        private object _tab;
        private object _controls;
        private object _commandEdit;
        private object _statusEdit;

        public bool IsReady { get; private set; }
        public object Manager => _manager;

        public bool TryOpen(object kompasApplication)
        {
            Dispose();
            if (kompasApplication == null)
                return false;

            try
            {
                // true = library-created property panel.
                _manager = Invoke(kompasApplication, "CreatePropertyManager", true);
                if (_manager == null)
                    return false;

                TrySet(_manager, "Caption", "AI CAD");
                TrySet(_manager, "Label", "AI CAD");
                TrySet(_manager, "ActivateOnCreate", true);

                object tabs = Get(_manager, "PropertyTabs");
                if (tabs == null)
                    return false;

                // KOMPAS v23: IPropertyTabs::Add(BSTR caption)
                _tab = Invoke(tabs, "Add", "AI CAD");
                if (_tab == null)
                    return false;

                TrySet(_tab, "Name", "AI CAD");
                TrySet(_tab, "Caption", "AI CAD");

                _controls = Get(_tab, "Controls") ?? Get(_tab, "PropertyControls");
                if (_controls == null)
                    return false;

                // KOMPAS v23: IPropertyControls::Add(ControlTypeEnum)
                _commandEdit = Invoke(_controls, "Add", 4); // ksControlEditStr
                if (_commandEdit == null)
                    return false;

                TrySet(_commandEdit, "Name", "Команда AI CAD");
                TrySet(_commandEdit, "Caption", "Команда");
                TrySet(_commandEdit, "Value", "Введите команду или описание детали");

                _statusEdit = Invoke(_controls, "Add", 4); // ksControlEditStr
                if (_statusEdit != null)
                {
                    TrySet(_statusEdit, "Name", "Состояние");
                    TrySet(_statusEdit, "Caption", "Состояние");
                    TrySet(_statusEdit, "Value", "Готово");
                    TrySet(_statusEdit, "ReadOnly", true);
                }

                TrySet(_manager, "Visible", true);
                IsReady = true;
                return true;
            }
            catch
            {
                Dispose();
                return false;
            }
        }

        public string ReadCommand()
        {
            if (!IsReady || _commandEdit == null)
                return string.Empty;
            try
            {
                return Convert.ToString(Get(_commandEdit, "Value"), CultureInfo.InvariantCulture) ?? string.Empty;
            }
            catch { return string.Empty; }
        }

        public void SetStatus(string value)
        {
            if (_statusEdit == null)
                return;
            TrySet(_statusEdit, "Value", value ?? string.Empty);
        }

        private static object Invoke(object target, string name, params object[] args)
        {
            return target.GetType().InvokeMember(
                name,
                BindingFlags.InvokeMethod | BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance,
                binder: null,
                target: target,
                args: args);
        }

        private static object Get(object target, string name)
        {
            try
            {
                return target.GetType().InvokeMember(
                    name,
                    BindingFlags.GetProperty | BindingFlags.Public | BindingFlags.Instance,
                    binder: null,
                    target: target,
                    args: null);
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
                    binder: null,
                    target: target,
                    args: new[] { value });
            }
            catch { }
        }

        public void Dispose()
        {
            IsReady = false;
            _statusEdit = null;
            _commandEdit = null;
            _controls = null;
            _tab = null;
            _manager = null;
        }
    }
}
