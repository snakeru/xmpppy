using System;
using System.Collections.Generic;
using System.Text;

namespace SkypeControl
{
    public class SkypeAttachEventArgs : EventArgs
    {
        public SkypeAttachStatus AttachStatus;

        public SkypeAttachEventArgs(SkypeAttachStatus theAttachStatus)
        {
            AttachStatus = theAttachStatus;
        }
    }

    public delegate void SkypeAttachHandler(object theSender, SkypeAttachEventArgs theEventArgs);

    public class SkypeResponseEventArgs : EventArgs
    {
        public string Response;

        public SkypeResponseEventArgs(string theResponse)
        {
            Response = theResponse;
        }
    }

    public delegate void SkypeResponseHandler(object theSender, SkypeResponseEventArgs theEventArgs);

    public enum SkypeAttachStatus : uint
    {
        Success = 0,
        PendingAuthorizaion = 1,
        Refused = 2,
        NotAvailable = 3,
        Available = 0x8001
    }

    internal class Constants
    {
        public const string SkypeControlAPIDiscover = "SkypeControlAPIDiscover";
        public const string SkypeControlAPIAttach = "SkypeControlAPIAttach";
    }

}
