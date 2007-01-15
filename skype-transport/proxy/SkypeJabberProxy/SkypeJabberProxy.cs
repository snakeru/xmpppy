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
        bool Authenticated;

        public SkypeJabberProxy()
        {
            InitializeComponent();
        }

        private void SkypeJabberProxy_Load(object sender, EventArgs e)
        {
            TransportHostTextBox.Text = Settings.Default.TransportHostname;
            TransportPortNumericUpDown.Value = Settings.Default.TransportPort;
            JabberIDTextBox.Text = Settings.Default.JabberID;
            skypeProxy.Connect();
        }

        private void SkypeJabberProxy_FormClosing(object sender, FormClosingEventArgs e)
        {
            Settings.Default.TransportHostname = TransportHostTextBox.Text;
            Settings.Default.TransportPort = (int)TransportPortNumericUpDown.Value;
            Settings.Default.JabberID = JabberIDTextBox.Text;
            Settings.Default.Save();
        }

        void skypeProxy_SkypeAttach(object sender, SkypeAttachEventArgs e)
        {
            switch (e.AttachStatus)
            {
                case SkypeAttachStatus.Success:
                    ConnectButton.Enabled = true;
                    if ((TransportHostTextBox.Text.Length > 0) && (JabberIDTextBox.Text.Length > 0) && 
                        ((tcpClient == null) || (!tcpClient.Connected)))
                    {
                        ConnectButton_Click(sender, e);
                    }
                    break;
                case SkypeAttachStatus.Available:
                    skypeProxy.Connect();
                    break;
                default:
                    ConnectButton.Enabled = false;
                    backgroundWorker_RunWorkerCompleted(sender, null);
                    MessageLabel.Text = e.AttachStatus.ToString();
                    break;
            }
        }

        void skypeProxy_SkypeResponse(object sender, SkypeResponseEventArgs e)
        {
            if ((tcpClient != null) && (tcpClient.Connected) && (streamWriter != null))
            {
                string[] details = e.Response.Split(' ');
                if (Authenticated)
                {
                    if ((details.Length > 3) &&
                    ((details[0] == "MESSAGE") || (details[0] == "CHATMESSAGE")) &&
                    (details[2] == "STATUS") &&
                    (details[3] == "RECEIVED"))
                    {
                        skypeProxy.Command("GET " + details[0] + " " + details[1] + " FROM_HANDLE");
                        skypeProxy.Command("GET " + details[0] + " " + details[1] + " BODY");
                    }
                    streamWriter.WriteLine(e.Response);
                }
                else
                {
                    if ((details.Length > 1) &&
                        (details[0] == "CURRENTUSERHANDLE"))
                    {
                        Authenticated = true;
                        streamWriter.WriteLine("AUTH " + details[1] + " " + JabberIDTextBox.Text);
                    }
                }
            }
        }

        void backgroundWorker_DoWork(object sender, DoWorkEventArgs e)
        {
            while ((tcpClient != null) && (streamReader != null) && (!streamReader.EndOfStream))
            {
                string line = streamReader.ReadLine();
                backgroundWorker.ReportProgress(0, line);
            }
        }

        void backgroundWorker_ProgressChanged(object sender, ProgressChangedEventArgs e)
        {
            skypeProxy.Command((string)e.UserState);
        }

        private void ConnectButton_Click(object sender, EventArgs e)
        {
            if ((tcpClient == null) || (!tcpClient.Connected))
            {
                tcpClient = new TcpClient();
                try
                {
                    MessageLabel.Text = "Connecting...";
                    Application.DoEvents();
                    tcpClient.Connect(TransportHostTextBox.Text, (int)TransportPortNumericUpDown.Value);
                    streamWriter = new StreamWriter(tcpClient.GetStream());
                    streamWriter.AutoFlush = true;
                    streamReader = new StreamReader(tcpClient.GetStream());
                    backgroundWorker.RunWorkerAsync();
                    ConnectButton.Text = "Dis&connect";
                    MessageLabel.Text = "Connected";
                    TransportHostTextBox.Enabled = false;
                    TransportPortNumericUpDown.Enabled = false;
                    JabberIDTextBox.Enabled = false;
                    Authenticated = false;
                    skypeProxy.Command("GET CURRENTUSERHANDLE");
                }
                catch (SocketException ex)
                {
                    MessageLabel.Text = ex.Message;
                    tcpClient = null;
                }
            }
            else
            {
                backgroundWorker_RunWorkerCompleted(sender, null);
            }
        }

        private void backgroundWorker_RunWorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            if (streamReader != null) streamReader.Close();
            streamReader = null;
            if (tcpClient != null) tcpClient.Close();
            tcpClient = null;
            skypeProxy.Command("SET SILENT_MODE OFF");
            ConnectButton.Text = "&Connect";
            MessageLabel.Text = string.Empty;
            TransportHostTextBox.Enabled = true;
            TransportPortNumericUpDown.Enabled = true;
            JabberIDTextBox.Enabled = true;
            Authenticated = false;
        }
    }
}