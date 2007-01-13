#region Declarations

using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Net.Sockets;
using System.Text;
using System.Windows.Forms;

using SkypeControl;

using SkypeJabberProxy.Properties;
using System.IO;

#endregion

namespace SkypeJabberProxy
{
    public partial class SkypeJabberProxy : Form
    {
        TcpClient tcpClient;
        StreamWriter streamWriter;
        StreamReader streamReader;

        public SkypeJabberProxy()
        {
            InitializeComponent();
        }

        private void SkypeJabberProxy_Load(object sender, EventArgs e)
        {
            skypeProxy.Conect();
        }

        void skypeProxy_SkypeAttach(object theSender, SkypeAttachEventArgs theEventArgs)
        {
            switch (theEventArgs.AttachStatus)
            {
                case SkypeAttachStatus.Success:
                    tcpClient = new TcpClient();
                    tcpClient.Connect(Settings.Default.TransportHostname, Settings.Default.TransportPort);
                    streamWriter = new StreamWriter(tcpClient.GetStream());
                    streamWriter.AutoFlush = true;
                    streamReader = new StreamReader(tcpClient.GetStream());
                    backgroundWorker.RunWorkerAsync();
                    break;
            }
        }

        void skypeProxy_SkypeResponse(object theSender, SkypeResponseEventArgs theEventArgs)
        {
            if (tcpClient.Connected)
            {
                string[] details = theEventArgs.Response.Split(' ');
                if ((details.Length > 3) &&
                    ((details[0] == "MESSAGE") || (details[0] == "CHATMESSAGE")) &&
                    (details[2] == "STATUS") &&
                    (details[3] == "RECEIVED"))
                {
                    skypeProxy.Command("GET " + details[0] + " " + details[1] + " FROM_HANDLE");
                    skypeProxy.Command("GET " + details[0] + " " + details[1] + " BODY");
                }
                streamWriter.WriteLine(theEventArgs.Response);
            }
        }

        void backgroundWorker_DoWork(object sender, DoWorkEventArgs e)
        {
            while (!streamReader.EndOfStream)
            {
                string line = streamReader.ReadLine();
                backgroundWorker.ReportProgress(0, line);
            }
            backgroundWorker.ReportProgress(100, "SET SILENT_MODE OFF");
            tcpClient.Close();
        }

        void backgroundWorker_ProgressChanged(object sender, ProgressChangedEventArgs e)
        {
            skypeProxy.Command((string)e.UserState);
        }
    }
}