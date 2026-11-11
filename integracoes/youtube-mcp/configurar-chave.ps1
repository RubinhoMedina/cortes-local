$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Configurar YouTube Data API'
$form.Size = New-Object System.Drawing.Size(530, 220)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Cole sua chave da YouTube Data API. Ela sera criptografada para este usuario do Windows.'
$label.SetBounds(20, 15, 475, 45)
$form.Controls.Add($label)
$inputKey = New-Object System.Windows.Forms.TextBox
$inputKey.UseSystemPasswordChar = $true
$inputKey.SetBounds(20, 65, 475, 25)
$form.Controls.Add($inputKey)
$status = New-Object System.Windows.Forms.Label
$status.SetBounds(20, 105, 475, 25)
$form.Controls.Add($status)
$save = New-Object System.Windows.Forms.Button
$save.Text = 'Salvar chave'
$save.SetBounds(340, 140, 155, 30)
$save.Add_Click({
    $key = $inputKey.Text.Trim()
    if ($key -notmatch '^AIza[0-9A-Za-z_-]{35}$') {
        $status.Text = 'Confira a chave copiada do Google Cloud.'
        return
    }
    $folder = Join-Path $PSScriptRoot 'private'
    [System.IO.Directory]::CreateDirectory($folder) | Out-Null
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $folder /inheritance:r /grant:r "*${sid}:(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao proteger a pasta da chave.' }
    $secureKey = ConvertTo-SecureString $key -AsPlainText -Force
    $secureKey | Export-Clixml -LiteralPath (Join-Path $folder 'youtube-api-key.xml')
    $inputKey.Clear()
    $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Close()
})
$form.Controls.Add($save)
$form.AcceptButton = $save
[void]$form.ShowDialog()
$form.Dispose()
