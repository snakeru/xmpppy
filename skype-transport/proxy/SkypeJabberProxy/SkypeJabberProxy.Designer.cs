namespace SkypeJabberProxy
{
    partial class SkypeJabberProxy
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.backgroundWorker = new System.ComponentModel.BackgroundWorker();
            this.skypeProxy = new SkypeControl.SkypeProxy();
            this.TransportLabel = new System.Windows.Forms.Label();
            this.JabberIDTextBox = new System.Windows.Forms.TextBox();
            this.JabberIDLabel = new System.Windows.Forms.Label();
            this.TransportHostTextBox = new System.Windows.Forms.TextBox();
            this.ConnectButton = new System.Windows.Forms.Button();
            this.MessageLabel = new System.Windows.Forms.Label();
            this.TranportPortLabel = new System.Windows.Forms.Label();
            this.TransportPortNumericUpDown = new System.Windows.Forms.NumericUpDown();
            ((System.ComponentModel.ISupportInitialize)(this.TransportPortNumericUpDown)).BeginInit();
            this.SuspendLayout();
            // 
            // backgroundWorker
            // 
            this.backgroundWorker.WorkerReportsProgress = true;
            this.backgroundWorker.DoWork += new System.ComponentModel.DoWorkEventHandler(this.backgroundWorker_DoWork);
            this.backgroundWorker.RunWorkerCompleted += new System.ComponentModel.RunWorkerCompletedEventHandler(this.backgroundWorker_RunWorkerCompleted);
            this.backgroundWorker.ProgressChanged += new System.ComponentModel.ProgressChangedEventHandler(this.backgroundWorker_ProgressChanged);
            // 
            // skypeProxy
            // 
            this.skypeProxy.SkypeAttach += new SkypeControl.SkypeAttachHandler(this.skypeProxy_SkypeAttach);
            this.skypeProxy.SkypeResponse += new SkypeControl.SkypeResponseHandler(this.skypeProxy_SkypeResponse);
            // 
            // TransportLabel
            // 
            this.TransportLabel.AutoSize = true;
            this.TransportLabel.Location = new System.Drawing.Point(12, 15);
            this.TransportLabel.Name = "TransportLabel";
            this.TransportLabel.Size = new System.Drawing.Size(55, 13);
            this.TransportLabel.TabIndex = 0;
            this.TransportLabel.Text = "Transport:";
            // 
            // JabberIDTextBox
            // 
            this.JabberIDTextBox.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left)
                        | System.Windows.Forms.AnchorStyles.Right)));
            this.JabberIDTextBox.Location = new System.Drawing.Point(106, 38);
            this.JabberIDTextBox.Name = "JabberIDTextBox";
            this.JabberIDTextBox.Size = new System.Drawing.Size(357, 20);
            this.JabberIDTextBox.TabIndex = 5;
            // 
            // JabberIDLabel
            // 
            this.JabberIDLabel.AutoSize = true;
            this.JabberIDLabel.Location = new System.Drawing.Point(12, 41);
            this.JabberIDLabel.Name = "JabberIDLabel";
            this.JabberIDLabel.Size = new System.Drawing.Size(81, 13);
            this.JabberIDLabel.TabIndex = 4;
            this.JabberIDLabel.Text = "Jabber ID (JID):";
            // 
            // TransportHostTextBox
            // 
            this.TransportHostTextBox.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left)
                        | System.Windows.Forms.AnchorStyles.Right)));
            this.TransportHostTextBox.Location = new System.Drawing.Point(106, 12);
            this.TransportHostTextBox.Name = "TransportHostTextBox";
            this.TransportHostTextBox.Size = new System.Drawing.Size(273, 20);
            this.TransportHostTextBox.TabIndex = 1;
            // 
            // ConnectButton
            // 
            this.ConnectButton.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right)));
            this.ConnectButton.Enabled = false;
            this.ConnectButton.Location = new System.Drawing.Point(388, 64);
            this.ConnectButton.Name = "ConnectButton";
            this.ConnectButton.Size = new System.Drawing.Size(75, 23);
            this.ConnectButton.TabIndex = 6;
            this.ConnectButton.Text = "&Connect";
            this.ConnectButton.UseVisualStyleBackColor = true;
            this.ConnectButton.Click += new System.EventHandler(this.ConnectButton_Click);
            // 
            // MessageLabel
            // 
            this.MessageLabel.AutoSize = true;
            this.MessageLabel.Location = new System.Drawing.Point(12, 69);
            this.MessageLabel.Name = "MessageLabel";
            this.MessageLabel.Size = new System.Drawing.Size(0, 13);
            this.MessageLabel.TabIndex = 3;
            // 
            // TranportPortLabel
            // 
            this.TranportPortLabel.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right)));
            this.TranportPortLabel.AutoSize = true;
            this.TranportPortLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.TranportPortLabel.Location = new System.Drawing.Point(379, 15);
            this.TranportPortLabel.Name = "TranportPortLabel";
            this.TranportPortLabel.Size = new System.Drawing.Size(10, 13);
            this.TranportPortLabel.TabIndex = 2;
            this.TranportPortLabel.Text = ":";
            // 
            // TransportPortNumericUpDown
            // 
            this.TransportPortNumericUpDown.Location = new System.Drawing.Point(388, 12);
            this.TransportPortNumericUpDown.Maximum = new decimal(new int[] {
            65535,
            0,
            0,
            0});
            this.TransportPortNumericUpDown.Minimum = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.TransportPortNumericUpDown.Name = "TransportPortNumericUpDown";
            this.TransportPortNumericUpDown.Size = new System.Drawing.Size(75, 20);
            this.TransportPortNumericUpDown.TabIndex = 3;
            this.TransportPortNumericUpDown.TextAlign = System.Windows.Forms.HorizontalAlignment.Right;
            this.TransportPortNumericUpDown.Value = new decimal(new int[] {
            10437,
            0,
            0,
            0});
            // 
            // SkypeJabberProxy
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(475, 99);
            this.Controls.Add(this.TransportPortNumericUpDown);
            this.Controls.Add(this.ConnectButton);
            this.Controls.Add(this.MessageLabel);
            this.Controls.Add(this.JabberIDLabel);
            this.Controls.Add(this.JabberIDTextBox);
            this.Controls.Add(this.TransportHostTextBox);
            this.Controls.Add(this.TranportPortLabel);
            this.Controls.Add(this.TransportLabel);
            this.Name = "SkypeJabberProxy";
            this.Text = "Skype to Jabber transport proxy";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.SkypeJabberProxy_FormClosing);
            this.Load += new System.EventHandler(this.SkypeJabberProxy_Load);
            ((System.ComponentModel.ISupportInitialize)(this.TransportPortNumericUpDown)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.ComponentModel.BackgroundWorker backgroundWorker;
        private SkypeControl.SkypeProxy skypeProxy;
        private System.Windows.Forms.Label TransportLabel;
        private System.Windows.Forms.TextBox JabberIDTextBox;
        private System.Windows.Forms.Label JabberIDLabel;
        private System.Windows.Forms.TextBox TransportHostTextBox;
        private System.Windows.Forms.Button ConnectButton;
        private System.Windows.Forms.Label MessageLabel;
        private System.Windows.Forms.Label TranportPortLabel;
        private System.Windows.Forms.NumericUpDown TransportPortNumericUpDown;
    }
}

