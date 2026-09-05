using System;
using System.Globalization;
using System.Reflection;

namespace CompasAiCad
{
    /// <summary>
    /// Capability-driven adapter around the KOMPAS IPropertyManager automation API.
    /// Exact collection member signatures vary across SDK generations, so this class
    /// probes Automation members and lets the proven WinForms UI remain the fallback.
    /// </summary>
    internal sealed class PropertyManagerBackend : IDisposable
    {
        private object _manager;
        private object _tab;
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
                _manager = Invoke(kompasApplication, "CreatePropertyManager", true);
                if (_manager == null)
                    return false;

                TrySet(_manager, "Caption", "AI CAD");
                TrySet(_manager, "Name", "AI CAD");

                object tabs = Get(_manager, "PropertyTabs");
                if (tabs == null)
                    return false;

                _tab = InvokeAny(tabs,
                    new object[] { "Add", 1, "AI CAD", true, true },
                    new object[] { "AddTab", 1, "AI CAD", true, true },
                    new object[] { "CreateTab", 1, true, true },
                    new object[] { "Add", 1, true, true },
                    new object[] { "Create", 1, "AI CAD", true, true });
                if (_tab == null)
                    return false;

                TrySet(_tab, "Name", "AI CAD");
                TrySet(_tab, "Caption", "AI CAD");

                object controls = Get(_tab, "Controls") ?? Get(_tab, "PropertyControls");
                if (controls == null)
                    return false;

                _commandEdit = InvokeAny(controls,
                    new object[] { "CreateControl", 4, 1001 },
                    new object[] { "CreateControl", 4 },
                    new object[] { "Add", 4, 1001 },
                    new object[] { "Add", 4 });
                if (_commandEdit == null)
                    return false;

                TrySet(_commandEdit, "Id", 1001L);
                TrySet(_commandEdit, "Name", "Команда AI CAD");
                TrySet(_commandEdit, "Caption", "Команда");
                TrySet(_commandEdit, "Value", "Введите команду или описание детали");

                _statusEdit = InvokeAny(controls,
                    new object[] { "CreateControl", 4, 1002 },
                    new object[] { "CreateControl", 4 },
                    new object[] { "Add", 4, 1002 },
                    new object[] { "Add", 4 });
                if (_statusEdit != null)
                {
                    TrySet(_statusEdit, "Id", 1002L);
                    TrySet(_statusEdit, "Name", "Состояние");
                    TrySet(_statusEdit, "Caption", "Состояние");
                    TrySet(_statusEdit, "Value", "Готово");
                    TrySet(_statusEdit, "Enabled", false);
                }

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

        private static object InvokeAny(object target, params object[][] attempts)
        {
            foreach (object[] attempt in attempts)
            {
                if (attempt.Length == 0)
                    continue;
                string name = Convert.ToString(attempt[0], CultureInfo.InvariantCulture);
                object[] args = new object[attempt.Length - 1];
                Array.Copy(attempt, 1, args, 0, args.Length);
                try
                {
                    object result = Invoke(target, name, args);
                    if (result != null)
                        return result;
                }
                catch { }
            }
            return null;
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
            _tab = null;
            _manager = null;
        }
    }
}
