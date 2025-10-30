$Pwd=ConvertTo-SecureString -String "Password123!" -AsPlainText -Force
$Cred=[System.Management.Automation.PSCredential]::new("eduser",$Pwd)

Stop-Process -Name "EDMarketConnector" -Force
Start-Process -FilePath "C:\Program Files (x86)\EDMarketConnector\EDMarketConnector.exe" -Credential $Cred -WorkingDirectory "~"
