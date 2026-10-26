$h = "ts01-gyr-maverick.cloudsink.net"
$tcp = New-Object Net.Sockets.TcpClient($h, 443)
$ssl = New-Object Net.Security.SslStream($tcp.GetStream(), $false, ({ $true }))
$ssl.AuthenticateAsClient($h, $null, [Security.Authentication.SslProtocols]::Tls12, $false)
$cert = New-Object Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
$cert | Format-List Subject, Issuer, Thumbprint, NotBefore, NotAfter

# Cadena completa
$chain = New-Object Security.Cryptography.X509Certificates.X509Chain
$chain.Build($cert) | Out-Null
$chain.ChainElements | ForEach-Object { $_.Certificate.Subject }
$ssl.Dispose(); $tcp.Dispose()
