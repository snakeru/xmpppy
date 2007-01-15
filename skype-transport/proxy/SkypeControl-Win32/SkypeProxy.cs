using System;
using System.Collections.Generic;
using System.Text;
using System.Runtime.InteropServices;
using System.ComponentModel;
using System.Drawing;

namespace SkypeControl
{
    [ToolboxBitmap(typeof(SkypeProxy), "SkypeProxy.png")]
    public class SkypeProxy : Component
    {
        public SkypeProxy()
        {
            mySkypeClient.SkypeAttach += new SkypeAttachHandler(mySkypeClient_OnSkypeAttach);
            mySkypeClient.SkypeResponse += new SkypeResponseHandler(mySkypeClient_SkypeResponse);
        }

        public event SkypeAttachHandler SkypeAttach;
        public event SkypeResponseHandler SkypeResponse;

        private void mySkypeClient_OnSkypeAttach(object theSender, SkypeAttachEventArgs theEventArgs)
        {
            if (SkypeAttach != null)
                SkypeAttach(this, theEventArgs);
        }

        void mySkypeClient_SkypeResponse(object theSender, SkypeResponseEventArgs theEventArgs)
        {
            if (SkypeResponse != null)
                SkypeResponse(this, theEventArgs);
        }

        private SkypeClient mySkypeClient = new SkypeClient();

        public bool Connect()
        {
            return mySkypeClient.Connect();
        }

        public void Disconnect()
        {
            mySkypeClient.Disconnect();
        }

        public bool Command(string theCommand)
        {
            return mySkypeClient.Command(theCommand);
        }

    }
}
