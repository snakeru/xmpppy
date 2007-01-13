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
            this.SuspendLayout();
            // 
            // backgroundWorker
            // 
            this.backgroundWorker.WorkerReportsProgress = true;
            this.backgroundWorker.DoWork += new System.ComponentModel.DoWorkEventHandler(this.backgroundWorker_DoWork);
            this.backgroundWorker.ProgressChanged += new System.ComponentModel.ProgressChangedEventHandler(this.backgroundWorker_ProgressChanged);
            // 
            // skypeProxy
            // 
            this.skypeProxy.SkypeAttach += new SkypeControl.SkypeAttachHandler(this.skypeProxy_SkypeAttach);
            this.skypeProxy.SkypeResponse += new SkypeControl.SkypeResponseHandler(this.skypeProxy_SkypeResponse);
            // 
            // SkypeJabberProxy
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(540, 162);
            this.Name = "SkypeJabberProxy";
            this.Text = "Skype to Jabber transport proxy";
            this.Load += new System.EventHandler(this.SkypeJabberProxy_Load);
            this.ResumeLayout(false);

        }

        #endregion

        private System.ComponentModel.BackgroundWorker backgroundWorker;
        private SkypeControl.SkypeProxy skypeProxy;
    }
}

