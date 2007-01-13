using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Text;
using System.Windows.Forms;

namespace SkypeControl
{
    internal partial class SkypeClient : Form
    {
        public SkypeClient()
        {
            InitializeComponent();

            UM_SkypeControlAPIDiscover = Platform.RegisterWindowMessage(Constants.SkypeControlAPIDiscover);
            UM_SkypeControlAPIAttach = Platform.RegisterWindowMessage(Constants.SkypeControlAPIAttach);

            CreateHandle();
        }

        public bool Connect()
        {
            IntPtr result;
            IntPtr aRetVal = Platform.SendMessageTimeout(Platform.HWND_BROADCAST, UM_SkypeControlAPIDiscover, Handle, IntPtr.Zero, Platform.SendMessageTimeoutFlags.SMTO_NORMAL, 100, out result);

            return(aRetVal != IntPtr.Zero);
        }

        public void Disconnect()
        {
            Command("");
            mySkypeHandle = IntPtr.Zero;
        }

        public bool Command(string theCommand)
        {
            Platform.CopyDataStruct aCDS = new Platform.CopyDataStruct();

            aCDS.ID = "1";
            aCDS.Data = theCommand;
            aCDS.Length = aCDS.Data.Length + 1;

            IntPtr result;
            IntPtr aRetVal = Platform.SendMessageTimeout(mySkypeHandle, Platform.WM_COPYDATA, Handle, ref aCDS, Platform.SendMessageTimeoutFlags.SMTO_NORMAL, 100, out result);

            return (aRetVal != IntPtr.Zero);
        }

        private UInt32 UM_SkypeControlAPIDiscover = 0;
        private UInt32 UM_SkypeControlAPIAttach = 0;

        private IntPtr mySkypeHandle = IntPtr.Zero;

        public event SkypeAttachHandler SkypeAttach;
        public event SkypeResponseHandler SkypeResponse;

        protected override void WndProc(ref Message m)
        {
            UInt32 aMsg = (UInt32)m.Msg;

            if (aMsg == UM_SkypeControlAPIAttach)
            {
                SkypeAttachStatus anAttachStatus = (SkypeAttachStatus)m.LParam;

                if (anAttachStatus == SkypeAttachStatus.Success)
                    mySkypeHandle = m.WParam;

                if (SkypeAttach != null)
                    SkypeAttach(this, new SkypeAttachEventArgs(anAttachStatus));

                m.Result = new IntPtr(1);
                return;
            }

            if (aMsg == Platform.WM_COPYDATA)
            {
                if (m.WParam == mySkypeHandle)
                {
                    Platform.CopyDataStruct aCDS = (Platform.CopyDataStruct)m.GetLParam(typeof(Platform.CopyDataStruct));
                    string aResponse = aCDS.Data;

                    if (SkypeResponse != null)
                        SkypeResponse(this, new SkypeResponseEventArgs(aResponse));

                    m.Result = new IntPtr(1);
                    return;
                }
            }

            base.WndProc(ref m);
        }
    }
}