Stop-Process -Name "EDMarketConnector" -Force
Start-Process -FilePath "C:\Program Files (x86)\EDMarketConnector\EDMarketConnector.exe" -WorkingDirectory "~"
