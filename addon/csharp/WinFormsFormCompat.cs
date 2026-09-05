using System.Drawing;
using System.Windows.Forms;

namespace CompasAiCad
{
    // Compatibility shim for the current panel code. WinForms Form has no
    // PreferredWidth/PreferredHeight properties; the panel code uses these
    // values as its desired initial size.
    internal class Form : System.Windows.Forms.Form
    {
        public int PreferredWidth { get { return 300; } }
        public int PreferredHeight { get { return 520; } }
    }
}
